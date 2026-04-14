import csv
import gzip
import time

from more_itertools import chunked
from pymongo import UpdateMany
from tqdm import tqdm

from nedrexdb.db import MongoInstance
from nedrexdb.db.parsers import _get_file_location_factory

get_file_location = _get_file_location_factory("unichem")


def validate_file(file) -> bool:
    try:
        with gzip.open(file, "rt") as f:
            reader = csv.reader(f, delimiter="\t")
            next(reader)  # Skip the header row
    except:
        return False
    return True


def parse():
    fname = get_file_location("pubchem_drugbank_map")
    updates = []

    with gzip.open(fname, "rt") as f:
        reader = csv.reader(f, delimiter="\t")
        next(reader)  # Skip the header row

        for db, pc in tqdm(reader, leave=False):
            update = UpdateMany(
                {"domainIds": f"drugbank.{db}"},
                {
                    "$addToSet": {"domainIds": f"pubchem.{pc}", "dataSources": "unichem"},
                },
                upsert=False,
            )

            updates.append(update)

    coll = MongoInstance.DB["drug"]
    # previously n:500
    for chunk in tqdm(chunked(updates, 10000), leave=False):
        coll.bulk_write(chunk)
        time.sleep(0.1)
