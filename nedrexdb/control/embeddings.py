import os
from nedrexdb import config
from nedrexdb.logger import logger
from nedrexdb.db.import_embeddings import fetch_embeddings, upsert_embeddings
from nedrexdb.post_integration.neo4j_db_adjustments import create_constraints, create_vector_indices
from nedrexdb.control.docker import NeDRexLiveInstance
import time

class EmbeddingController:
    """
    Manages the lifecycle of vector embeddings during the build process.
    Unifies the logic for invalidation, siphoning, and regeneration.
    """
    
    def __init__(self, dev_instance, create_embeddings=False, rebuild=False, keep_dev=False):
        self.dev_instance = dev_instance
        self.create_embeddings = create_embeddings
        self.rebuild = rebuild
        
        # State tracked during the build
        self.distinct_per_collection_live = {}
        self.distinct_per_collection_dev = {}
        self.reusable_embeddings = {}
        self.tobuild_embeddings = set()
        
        # Mapping from Neo4j Label/Type to Mongo Collection Name (and vice versa)
        # Note: In build.py, it was ad-hoc .replace("_", "")
        # We can formalize it here if needed, but for now, we'll maintain parity.
        self.keep_dev = keep_dev
        self.embedding_deps_config = config.get("embeddings.embedding_dependencies") or []

    def _get_mongo_col_name(self, embedding_key):
        """Maps embedding key to mongo collection (e.g., 'protein_interacts_with_protein' -> 'protein_interacts_with_protein')"""
        # The current codebase uses the key directly or with minor variations.
        # We'll use the key as provided in the config.
        return embedding_key

    def _check_embedding_config_changed(self, mongo_live_db):
        """
        Reads the embedding config (model + length) stored in the live MongoDB metadata
        and compares it with the current config. If either changed, forces a full rebuild
        so stale embeddings from a different model or dimension are never reused.
        """
        from nedrexdb.llm import _LLM_model, _LLM_embedding_length
        try:
            meta = mongo_live_db["metadata"].find_one({}) or {}
            stored = meta.get("embedding_config", {})
        except Exception as e:
            logger.warning(f"Could not read live embedding metadata: {e}. Assuming config unchanged.")
            return

        if not stored:
            logger.info("No embedding config found in live metadata (first run or legacy build). Proceeding with normal reuse logic.")
            return

        stored_model = stored.get("model")
        stored_length = stored.get("length")

        if stored_model != _LLM_model or stored_length != _LLM_embedding_length:
            logger.warning(
                f"Embedding config changed since last build: "
                f"model {stored_model!r} -> {_LLM_model!r}, "
                f"length {stored_length} -> {_LLM_embedding_length}. "
                f"Forcing full re-embedding — existing embeddings are incompatible."
            )
            self.rebuild = True
        else:
            logger.debug(f"Embedding config unchanged (model={_LLM_model!r}, length={_LLM_embedding_length}). Reuse eligible.")

    def gather_live_state(self, mongo_live_db):
        """
        Scans the Live MongoDB to see what sources were used for each collection.
        This is Stage 1 of the decision process.
        """
        if not self.create_embeddings or self.rebuild:
            return

        # Check if the embedding model or vector length changed since the last build.
        # If so, existing embeddings are from a different vector space and must not be reused.
        self._check_embedding_config_changed(mongo_live_db)
        if self.rebuild:
            return

        for collection_name in mongo_live_db.list_collection_names():
            if collection_name in ["metadata", "_collections"]:
                continue
            
            collection = mongo_live_db[collection_name]
            try:
                distinct_values = collection.distinct("dataSources")
                if distinct_values:
                    # Maintain the .replace("_", "") convention for keys used in embeddings
                    clean_key = collection_name.replace("_", "")
                    self.distinct_per_collection_live[clean_key] = distinct_values
                    logger.debug(f"Found live dataSources for {collection_name}: {distinct_values}")
            except Exception as e:
                logger.info(f"Could not fetch live dataSources for {collection_name}: {e}")

    def prepare_reusable_embeddings(self):
        """
        Decides which embeddings can be fetched from the Live Neo4j instance
        before the build starts.
        """
        if not self.create_embeddings:
            return

        if self.rebuild:
            logger.info("Rebuild flag is set, marking all embeddings for regeneration.")
            self.tobuild_embeddings = set(self.embedding_deps_config)
            return

        to_fetch = set()
        for key in self.embedding_deps_config:
            if key in self.distinct_per_collection_live:
                to_fetch.add(key)
            else:
                self.tobuild_embeddings.add(key)

        if to_fetch:
            logger.info(f"Siphoning reusable embeddings from Live DB: {to_fetch}")
            # The fetch_embeddings function expects a set of names
            # and connects to 'live' session type internally.
            # Requirement: Live Neo4j must be accessible.
            self.dev_instance.set_up(use_existing_volume=True, neo4j_mode="db")
            self.reusable_embeddings = fetch_embeddings(to_fetch)
            self.dev_instance.remove()
        
        # Basic sanity check: if fetch returned empty for a key, we must rebuild it
        for key in list(self.reusable_embeddings.keys()):
            if not self.reusable_embeddings[key]:
                logger.debug(f"Fetched embedding for {key} was empty, marking for rebuild.")
                self.tobuild_embeddings.add(key)
                self.reusable_embeddings.pop(key)

    def _promote_and_keep_dev(self):
        """
        Used when --keep-dev is set: gracefully stop the dev write container, promote
        to live, then attempt to restart dev in read-only mode for inspection.
        Both containers share the same Neo4j volume (Neo4j 5 allows multiple readers).
        If the dev read-only start fails due to a store lock conflict, the live instance
        is still running and the data is safe.
        """
        # Gracefully stop dev Neo4j so it flushes WAL and releases store lock.
        logger.info("Stopping dev Neo4j and MongoDB before live promotion...")
        self.dev_instance._remove_neo4j(remove_db_volume=False)

        # Stop dev MongoDB so the live instance can take over the same data volume.
        # (MongoDB requires exclusive access — two instances cannot share a data directory.)
        self.dev_instance._remove_mongo(remove_db_volume=False)

        # Promote to live (read-only Neo4j + MongoDB) on the same volumes.
        live_instance = NeDRexLiveInstance()
        live_instance.remove()
        live_instance.set_up(use_existing_volume=True, neo4j_mode="db")
        logger.info(
            f"Live Neo4j started. "
            f"Bolt: bolt://localhost:{live_instance.neo4j_bolt_port}, "
            f"HTTP: http://localhost:{live_instance.neo4j_http_port}"
        )

        # Attempt to restart dev in read-only mode on the same volume for inspection.
        try:
            self.dev_instance._set_up_neo4j(use_existing_volume=True, neo4j_mode="db")
            logger.info(
                f"[DEBUG] Dev Neo4j also running in read-only mode for inspection. "
                f"Container: {self.dev_instance.neo4j_container_name}, "
                f"Bolt: bolt://localhost:{self.dev_instance.neo4j_bolt_port}, "
                f"HTTP: http://localhost:{self.dev_instance.neo4j_http_port}"
            )
        except Exception as e:
            logger.warning(
                f"[DEBUG] Dev container could not be started for inspection "
                f"(Neo4j store lock held by live instance?): {e}. "
                f"Data is accessible via the live instance."
            )

    def validate_and_finalize(self, mongo_dev_db, no_download, current_metadata):
        """
        Final check after ingestion. Compares new Dev state with old Live state.
        Executes the actual upsert and generation.
        """
        if not self.create_embeddings:
            # Traditional non-embedding path
            self.dev_instance._remove_neo4j(remove_db_volume=False, neo4j_mode="import")
            self.dev_instance._set_up_neo4j(use_existing_volume=True, neo4j_mode="db-write")
            time.sleep(60)
            create_constraints()
            if self.keep_dev:
                self._promote_and_keep_dev()
            else:
                self.dev_instance.remove()
            return

        # 1. Gather new Dev state
        embedding_deps_dev = {}
        for collection_name in mongo_dev_db.list_collection_names():
            if collection_name in ["metadata", "_collections"]:
                continue
            collection = mongo_dev_db[collection_name]
            try:
                distinct_values = collection.distinct("dataSources")
                clean_key = collection_name.replace("_", "")
                
                # Check if data sources changed between Live and Dev
                if (clean_key not in self.distinct_per_collection_live or 
                    self.distinct_per_collection_live[clean_key] != distinct_values):
                    
                    if clean_key in self.reusable_embeddings:
                        logger.debug(f"Data sources for {clean_key} changed in Dev, invalidating fetched embedding.")
                        self.reusable_embeddings.pop(clean_key)
                        self.tobuild_embeddings.add(clean_key)
                
                if distinct_values:
                    embedding_deps_dev[clean_key] = distinct_values
            except Exception as e:
                logger.info(f"Could not fetch dev dataSources for {collection_name}: {e}")

        # 2. Check for content updates (the no_download list)
        for key in list(self.reusable_embeddings.keys()):
            if key in self.embedding_deps_config:
                is_valid = True
                deps = embedding_deps_dev.get(key, [])
                
                for dep in deps:
                    # If a dependency was NOT in no_download, it was updated -> invalidate
                    if dep not in no_download:
                        is_valid = False
                        break
                    # If dependency is missing from metadata (edge case)
                    if dep not in current_metadata:
                        is_valid = None # Cannot determine, safer to rebuild
                        break
                
                if is_valid is False:
                    logger.info(f"Source data for {key} was updated, marking for rebuild.")
                    self.reusable_embeddings.pop(key)
                    self.tobuild_embeddings.add(key)
                elif is_valid is None:
                    self.reusable_embeddings.pop(key)

        logger.info(f"Final Embedding Plan:")
        logger.info(f"  -> Upserting reusable: {list(self.reusable_embeddings.keys())}")
        logger.info(f"  -> Building new:       {list(self.tobuild_embeddings)}")

        # 3. Execution Phase
        self.dev_instance._remove_neo4j(remove_db_volume=False, neo4j_mode="import")
        self.dev_instance._set_up_neo4j(use_existing_volume=True, neo4j_mode="db-write")
        time.sleep(60)
        create_constraints()

        # Write siphoned embeddings back
        upsert_embeddings(self.reusable_embeddings)

        # Trigger APOC generation for the rest
        try:
            # We filter the config list down to only what we actually need to build
            build_list = [k for k in self.embedding_deps_config if k in self.tobuild_embeddings]
            if build_list:
                logger.info(f"Creating vector indices and generating embeddings for: {build_list}")
                create_vector_indices(build_list)
            else:
                logger.info("No new embeddings need to be generated.")
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")

        # Persist the embedding config used for this build so the next build can detect changes.
        try:
            from nedrexdb.llm import _LLM_model, _LLM_embedding_length
            mongo_dev_db["metadata"].update_one(
                {},
                {"$set": {"embedding_config": {"model": _LLM_model, "length": _LLM_embedding_length}}},
                upsert=True,
            )
            logger.info(f"Persisted embedding config to metadata (model={_LLM_model!r}, length={_LLM_embedding_length}).")
        except Exception as e:
            logger.warning(f"Could not persist embedding config to metadata: {e}")

        if self.keep_dev:
            self._promote_and_keep_dev()
        else:
            self.dev_instance.remove()
