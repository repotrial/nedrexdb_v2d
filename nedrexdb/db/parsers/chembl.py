import gzip as _gzip
import sqlite3
import subprocess as _sp

from nedrexdb.db import MongoInstance
from nedrexdb.db.parsers import _get_file_location_factory
from nedrexdb.db.models.nodes.drug import Drug
from nedrexdb.downloaders import get_latest_chembl_version

get_file_location = _get_file_location_factory("chembl")


def get_chembl_drugbank_map():
    path = get_file_location("unichem")
    cd_map = {}
    with _gzip.open(path, "rt") as f:
        next(f)  # Skip header row
        for line in f:
            chembl_id, drugbank_id = line.strip().split()
            cd_map[drugbank_id] = chembl_id

    return cd_map


def decompress_if_necessary():
    version = get_latest_chembl_version()
    url_path = get_file_location("sqlite")

    target = url_path.parents[0] / url_path.name.rsplit(".", 2)[0].format(version)
    if target.exists():
        return target

    target.mkdir(parents=True)
    path = url_path.parents[0] / url_path.name.format(version)
    _sp.call(
        ["tar", "-zxvf", f"{path}", "-C", f"{target.resolve()}", "--strip-components", "1"], cwd=f"{path.parents[0]}"
    )

    return target


def parse_chembl():
    cd_map = get_chembl_drugbank_map()

    path = decompress_if_necessary()
    db = [i for i in path.rglob("*") if i.name.endswith(".db")][0]
    con = sqlite3.connect(f"{db}")
    cur = con.cursor()

    for drugbank_id, chembl_id in cd_map.items():
        result = list(cur.execute("SELECT MAX_PHASE FROM MOLECULE_DICTIONARY WHERE CHEMBL_ID = '%s'" % chembl_id))
        if not result:
            continue
        max_phase = max(i[0] for i in result)

        if max_phase == 4:
            query = {"primaryDomainId": f"drugbank.{drugbank_id}"}
            update = {"$addToSet": {"drugGroups": "approved", "dataSources": "chembl"}}
            MongoInstance.DB[Drug.collection_name].update_one(query, update)
