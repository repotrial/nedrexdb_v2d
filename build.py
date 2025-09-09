#!/usr/bin/env python

import click
import os
import subprocess

import nedrexdb
from nedrexdb import config, downloaders
from nedrexdb.control.docker import NeDRexDevInstance, NeDRexLiveInstance
from nedrexdb.db import MongoInstance, mongo_to_neo, collection_stats
from nedrexdb.db.import_embeddings import fetch_embeddings, upsert_embeddings
from nedrexdb.db.parsers import (
    biogrid,
    disgenet,
    ctd,
    drugbank,
    drug_central,
    hpo,
    hpa,
    iid,
    intact,
    uniprot,
    uniprot_signatures,
    ncbi,
    mondo,
    omim,
    reactome,
    go,
    clinvar,
    chembl,
    unichem,
    bioontology,
    sider,
    uberon,
    repotrial,
)
from nedrexdb.downloaders import get_versions, update_versions
from nedrexdb.post_integration import (trim_uberon, drop_empty_collections, create_vector_indices)


@click.group()
def cli():
    pass


@click.option("--conf", required=True, type=click.Path(exists=True))
@click.option("--download", is_flag=True, default=False)
@click.option("--version_update", is_flag=False, default="")
@click.option("--create_embeddings", is_flag=True, default=False)
@cli.command()
def update(conf, download, version_update, create_embeddings):
    print(f"Config file: {conf}")
    print(f"Download updates: {download}")
    print(f"Update DB versions: {version_update}")
    print(f"Create embeddings: {create_embeddings}")

    nedrexdb.parse_config(conf)

    version = config["db.version"]

    if version not in ["open", "licensed"]:
        raise Exception(f"invalid version {version!r}")

    version_update_skip = set()
    prev_metadata = {}

    # check for metadata of the current live version before fetching new data
    if download:
        try:
            MongoInstance.connect("live")
            if create_embeddings:
                # find sources used previously to create embeddings
                distinct_per_collection = {}
                for collection_name in MongoInstance.DB.list_collection_names():
                    if collection_name not in ["metadata", '_collections']:
                        collection = MongoInstance.DB[collection_name]
                        # Get distinct values for the field `dataSources`
                        try:
                            distinct_values = collection.distinct("dataSources")
                        except Exception as e:
                            print(f"⚠️ Could not fetch distinct dataSources for collection '{collection_name}': {e}")
                            continue
                        if distinct_values:
                            distinct_per_collection[collection_name.replace("_", "")] = distinct_values
                            print(f"Found distinct dataSources for collection {collection_name}")
            # needed for metadata comparisons
            prev_metadata = list(MongoInstance.DB["metadata"].find())
            prev_metadata = {} if prev_metadata is None else prev_metadata[0]["source_databases"]
            # log printing
            print("PREVIOUS METADATA")
            for source in prev_metadata:
                print(f"{source}:\t{prev_metadata[source]['version']}"
                      f" [{prev_metadata[source]['date']}]")
        except:
            print("NO PREVIOUS METADATA FOUND")

    # init neo4j (while not needed for download & parsing of data - mongoDB does that)
    dev_instance = NeDRexDevInstance()
    #dev_instance.remove()

    if os.environ.get("TEST_MINIMUM", 0) == '1':
        # only pass dev_instance if embeddings are created
        instance = None
        if create_embeddings:
            instance = dev_instance
        embeddings, tobuild_embeddings = parse_dev(version=version,
                                                   download=download,
                                                   version_update=version_update,
                                                   prev_metadata=prev_metadata,
                                                   distinct_per_collection=distinct_per_collection,
                                                   dev_instance=instance)
    else:
        if download:
            # update metadata
            # fallback version is rarely needed. Do not change that file, only use the config!
            default_version = None
            if os.path.exists("/data/nedrex_files/nedrex_data/fallback_version"):
                with open("/data/nedrex_files/nedrex_data/fallback_version") as fallback_file:
                    default_version = fallback_file.readline().rstrip()
            nedrex_versions = update_versions(version_update_skip, default_version=default_version)
            with open("/data/nedrex_files/nedrex_data/fallback_version", "w") as fallback_file:
                fallback_file.write(f"{nedrex_versions['version']}")

            print("Download: ON")
            current_metadata = nedrex_versions["source_databases"]
            # already up-to-date data
            no_download = [key for key in prev_metadata if key in current_metadata and
                           prev_metadata[key]['version'] == current_metadata[key]['version']]
            static_download = [key for key in ["bioontology", "drugbank", "disgenet", "repotrial"] if
                               key not in no_download]
            if static_download:
                subprocess.run(["./setup_data.sh", "/data/nedrex_files"])
            downloaders.download_all(no_download_meta=no_download)

        if version_update:
            get_versions(version_update)

        if create_embeddings:
            embeddings, tobuild_embeddings = manage_embeddings(dev_instance=dev_instance,
                                                               distinct_per_collection=distinct_per_collection)

        # prepare neo4j for import from mongoDB
        dev_instance.set_up(use_existing_volume=False, neo4j_mode="import")

        # MongoDB data download & import
        MongoInstance.connect("dev")
        MongoInstance.set_indexes()

        MongoInstance.DB["metadata"].replace_one({}, nedrex_versions, upsert=True)

        # Parse sources contributing only nodes (and edges amongst those nodes)
        go.parse_go()
        mondo.parse_mondo_json()  # disorder nodes
        ncbi.parse_gene_info()
        uberon.parse()
        uniprot.parse_proteins()

        # Sources that add node type but require existing nodes, too
        clinvar.parse()

        if version == "licensed":
            drugbank._parse_drugbank()  # requires proteins to be parsed first
        elif version == "open":
            drugbank.parse_drugbank()
            chembl.parse_chembl()
        uniprot_signatures.parse()  # requires proteins to be parsed first
        hpo.parse()  # requires disorders to be parsed first
        reactome.parse()  # requires protein to be parsed first
        bioontology.parse()  # requires phenotype to be parsed

        # Sources that add data to existing nodes
        drug_central.parse_drug_central()
        unichem.parse()
        repotrial.parse()

        # Sources adding edges.
        biogrid.parse_ppis()
        ctd.parse()
        disgenet.parse_gene_disease_associations()
        go.parse_goa()
        hpa.parse_hpa()
        iid.parse_ppis()
        intact.parse()

        if version == "licensed":
            omim.parse_gene_disease_associations()
            version_update_skip.add("omim")

        sider.parse()
        uniprot.parse_idmap()

        from nedrexdb.analyses import molecule_similarity
        molecule_similarity.run()

        # Post-processing
        trim_uberon.trim_uberon()

    # clean up for export
    drop_empty_collections.drop_empty_collections()

    # export to Neo4j
    mongo_to_neo.mongo_to_neo(dev_instance, MongoInstance.DB)

    # Profile the collections
    collection_stats.profile_collections(MongoInstance.DB)

    collection_stats.verify_collections_after_profiling(MongoInstance.DB)

    if not create_embeddings:
        # remove dev instance and set up live instance
        dev_instance.remove(neo4j_mode="import")

    if create_embeddings:
        embedding_deps = {}
        # find sources used now to build mongo
        for collection_name in MongoInstance.DB.list_collection_names():
            if collection_name not in ["metadata", '_collections']:
                collection = MongoInstance.DB[collection_name]
                # Get distinct values for the field `dataSources`
                try:
                    distinct_values = collection.distinct("dataSources")
                except Exception as e:
                    print(f"⚠️ Could not fetch new distinct dataSources for collection '{collection_name}': {e}")
                    continue
                collection_name = collection_name.replace("_", "")
                if (collection_name not in distinct_per_collection.keys() or
                        distinct_per_collection[collection_name] != distinct_values):
                    embeddings.pop(collection_name, None)
                    tobuild_embeddings.add(collection_name)
                    print("Collection name:")
                    print(collection_name)
                if distinct_values:
                    embedding_deps[collection_name] = distinct_values

        for collection_name in embeddings.keys():
            import_embedding = True
            for dependency in embedding_deps[collection_name]:
                # check if dependency is up-to-date to decide whether an embedding can be imported or has to be built
                if dependency not in no_download:
                    import_embedding = False

                # check which embeddings can be build based on current metadata
                if dependency not in current_metadata.keys():
                    import_embedding = None
                    break

            if not import_embedding:
                embeddings.pop(collection_name)
                tobuild_embeddings.add(collection_name)

        print(embeddings.keys())
        print("tobuild:")
        print(tobuild_embeddings)

        dev_instance.remove(neo4j_mode="import")
        manage_embeddings(dev_instance=dev_instance,
                          read=False,
                          embeddings=embeddings,
                          tobuild_embeddings=tobuild_embeddings)

    live_instance = NeDRexLiveInstance()
    live_instance.remove()
    live_instance.set_up(use_existing_volume=True, neo4j_mode="db")


# put all embedding management in here to properly separate it from the essential code
def manage_embeddings(dev_instance,
                      distinct_per_collection={},
                      read=True,
                      embeddings=None,
                      tobuild_embeddings=None):
    # goal: "read" embeddings from previous build to not have to create them again (if metadata is unchanged)
    if read:
        toimport_embeddings = set()
        tobuild_embeddings = set()
        # fetch embeddings from previous database
        for collection_name in config["embeddings"]["embedding_dependencies"]:
            if collection_name in distinct_per_collection.keys():
                toimport_embeddings.add(collection_name)
            else:
                tobuild_embeddings.add(collection_name)

        print("To import embeddings:")
        print(toimport_embeddings)

        if toimport_embeddings:
            dev_instance.set_up(use_existing_volume=True, neo4j_mode="db")
            embeddings = fetch_embeddings(toimport_embeddings)
            dev_instance.remove()
        else:
            embeddings = {}

        try:
            check_list = [(entry[0], entry[1][1]) for entry in embeddings["drug"]][:5]
            print("Printing drug check list in next line...")
            print(check_list)
        except:
            print("Cannot print drug check list")

        # if embedding was not built in the last version even though metadata did not change
        for key in list(embeddings.keys()):
            if not embeddings[key]:
                tobuild_embeddings.add(key)
                embeddings.pop(key)

        print("To build embeddings:")
        print(tobuild_embeddings)

        return embeddings, tobuild_embeddings

    else:
        dev_instance = NeDRexDevInstance()
        dev_instance.set_up(use_existing_volume=True, neo4j_mode="db-write")

        # upsert previous embeddings, if they are still up-to-date
        upsert_embeddings(embeddings)

        # create embeddings
        try:
            for key in config["embeddings"]["embedding_dependencies"]:
                if key not in tobuild_embeddings:
                    config["embeddings"]["embedding_dependencies"].pop(key)
            create_vector_indices.create_vector_indices(config["embeddings"]["embedding_dependencies"])
        except Exception as e:
            print(e)
            print("Failed to create vector indices")
        dev_instance.remove()


def parse_dev(version, download, version_update, prev_metadata, distinct_per_collection, dev_instance):
    # control source downloads
    ignored_sources = {"chembl",
                       "biogrid",
                       "go",
                       "uberon",
                       "clinvar",
                       "hpo",
                       "hpa",
                       "uniprot",
                       "reactome",
                       "bioontology",
                       "drug_central",
                       "unichem",
                       "repotrial",
                       "iid",
                       "intact",
                       "omim",
                       "sider",  # from here on, temp.
                       #"ctd",
                       "disgenet",
                       #"mondo",
                       "ncbi"}
    if download:
        # fallback version is rarely needed. Do not change that file, only use the config!
        default_version = None
        if os.path.exists("/data/nedrex_files/nedrex_data/fallback_version"):
            with open("/data/nedrex_files/nedrex_data/fallback_version") as fallback_file:
                default_version = fallback_file.readline().rstrip()
        nedrex_versions = update_versions(ignored_sources=ignored_sources, default_version=default_version)
        with open("/data/nedrex_files/nedrex_data/fallback_version", "w") as fallback_file:
            fallback_file.write(f"{nedrex_versions['version']}")

        print("Download: ON")
        current_metadata = nedrex_versions["source_databases"]
        # already up-to-date data
        no_download = [key for key in prev_metadata if key in current_metadata and
                       prev_metadata[key]['version'] == current_metadata[key]['version']]
        static_download = [key for key in ["bioontology", "drugbank", "disgenet", "repotrial"] if key not in no_download
                           and key not in ignored_sources]
        if static_download:
            subprocess.run(["./setup_data.sh", "/data/nedrex_files"])
        else:
            print("Static sources are already up-to-date")
        downloaders.download_all(ignored_sources=ignored_sources,
                                 no_download_meta=no_download)

    if version_update:
        get_versions(version_update)

    if dev_instance is not None:
        embeddings, tobuild_embeddings = manage_embeddings(dev_instance=dev_instance,
                                                           distinct_per_collection=distinct_per_collection)

    # prepare neo4j for import from mongoDB
    dev_instance.set_up(use_existing_volume=False, neo4j_mode="import")

    # MongoDB data download & import
    MongoInstance.connect("dev")
    MongoInstance.set_indexes()

    MongoInstance.DB["metadata"].replace_one({}, nedrex_versions, upsert=True)

    if "mondo" not in ignored_sources:
        mondo.parse_mondo_json()
    if "ncbi" not in ignored_sources:
        ncbi.parse_gene_info()
    if "drugbank" not in ignored_sources:
        if version == "licensed":
            drugbank._parse_drugbank()
        elif version == "open":
            drugbank.parse_drugbank()
    if "drug_central" not in ignored_sources:
        drug_central.parse_drug_central()
    if "ctd" not in ignored_sources:
        ctd.parse()
    if "disgenet" not in ignored_sources:
        disgenet.parse_gene_disease_associations()

    if dev_instance:
        return embeddings, tobuild_embeddings


@click.option("--conf", required=True, type=click.Path(exists=True))
@cli.command()
def restart_live(conf):
    print(f"Config file: {conf}")
    nedrexdb.parse_config(conf)

    live_instance = NeDRexLiveInstance()
    live_instance.remove()
    live_instance.set_up(use_existing_volume=True, neo4j_mode="db")


if __name__ == "__main__":
    cli()
