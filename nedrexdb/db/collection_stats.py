from collections import defaultdict

from tqdm import tqdm

from nedrexdb import config as _config


def profile_collections(db):
    nodes = _config["api.node_collections"]
    edges = _config["api.edge_collections"]

    collections = nodes + edges
    print("Starting collection profiling...")
    for coll in collections:
        if coll not in db.list_collection_names():
            print(f"WARNING: Collection '{coll}' does not exist in database, skipping...")
            continue

        print(f"Profiling collection: {coll}")
        doc_count = 0
        attr_counts = defaultdict(int)

        try:
            total_docs = db[coll].count_documents({})
            if total_docs == 0:
                print(f"WARNING: Collection '{coll}' is empty")
                continue

            for doc in tqdm(db[coll].find(), total=total_docs, desc=f"Processing {coll}", leave=False):
                doc_count += 1
                for attr in doc.keys():
                    attr_counts[attr] += 1

            unique_attrs = list(attr_counts.keys())

            db["_collections"].replace_one(
                {"collection": coll},
                {
                    "collection": coll,
                    "document_count": doc_count,
                    "unique_attributes": unique_attrs,
                    "attribute_counts": dict(attr_counts),
                },
                upsert=True
            )
            print(f"Successfully profiled {coll}: {doc_count} documents")
        except Exception as e:
            print(f"Error profiling {coll}: {str(e)}")
            raise


def verify_collections_after_profiling(db):
    """Verify that all collections have been properly profiled."""
    actual_collections = set(coll for coll in db.list_collection_names()
                             if not coll.startswith("system.") and coll != "_collections")
    metadata_collections = set(doc["collection"] for doc in db["_collections"].find())

    missing = actual_collections - metadata_collections
    if missing:
        raise Exception(f"Collections missing from metadata after profiling: {missing}")
