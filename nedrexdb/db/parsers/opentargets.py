import gzip as _gzip
from collections import defaultdict as _defaultdict
from csv import DictReader as _DictReader
from itertools import chain as _chain
from pathlib import Path as _Path

from more_itertools import chunked as _chunked
from tqdm import tqdm as _tqdm

from nedrexdb.db import MongoInstance
from nedrexdb.db.models.nodes.disorder import Disorder
from nedrexdb.db.models.nodes.gene import Gene
from nedrexdb.db.models.edges.gene_associated_with_disorder import GeneAssociatedWithDisorder
from nedrexdb.db.parsers import _get_file_location_factory

from pyspark.sql import _SparkSession
import pyspark.sql.functions as _F

get_file_location = _get_file_location_factory("opentargets")


def _umls_to_nedrex_map() -> dict[str, list[str]]:
    d = _defaultdict(list)

    for dis in Disorder.find(MongoInstance.DB):
        umls_ids = [acc for acc in dis["domainIds"] if acc.startswith("umls.")]
        for umls_id in umls_ids:
            d[umls_id].append(dis["primaryDomainId"])

    return d


class OpenTargetsRow:
    def __init__(self, row):
        self._row = row

    def get_gene_id(self):
        return f"entrez.{self._row['geneId'].strip()}"

    def get_disorder_id(self):
        return f"umls.{self._row['diseaseId'].strip()}"

    def get_score(self) -> float:
        return float(self._row["score"])

    def parse(self, umls_nedrex_map: dict[str, list[str]]) -> list[GeneAssociatedWithDisorder]:
        sourceDomainId = self.get_gene_id()
        score = self.get_score()
        asserted_by = ["disgenet"]
        disorders = umls_nedrex_map.get(self.get_disorder_id(), [])

        gawds = [
            GeneAssociatedWithDisorder(
                sourceDomainId=sourceDomainId, targetDomainId=disorder, score=score, dataSources=asserted_by
            )
            for disorder in disorders
        ]

        return gawds


class OpenTargetsParser:
    def __init__(self, f: _Path):
        self.f = f

    def parse(self):

        # establish spark connection
spark = (
    _SparkSession.builder
    .master('local[*]')
    .getOrCreate()
)

# read evidence dataset
df = spark.read.parquet(self.f)

# add columns for diseaseIdType and diseaseIdValue
split_col = _F.split(df['diseaseId'], '_')
df = df.withColumn('diseaseIdType', split_col.getItem(0))
df = df.withColumn('diseaseIdValue', split_col.getItem(1))

# filter for mondo ids
n_rows = df.count()
df = df.where(df['diseaseIdType'] == "MONDO")
print(f"OpenTargets: Dropped {n_rows - df.count()} rows: no mondo id");

# add "opentargets." prefix to datasourceId
df = df.withColumn('datasourceId', _F.concat(_F.lit("opentargets."), df['datasourceId']))

# add "mondo." prefix to diseaseIdValue
df = df.withColumn('diseaseIdValue', _F.concat(_F.lit("mondo."), df['diseaseIdValue']))

# keep only rows with mondo id in NeDRex
n_rows = df.count()
df = df.where(df['diseaseIdValue'].isin(set(["mondo.0004992"])))
print(f"OpenTargets: Dropped {n_rows - df.count()} rows: mondo id not in NeDRex");

# keep only rows sith ensemble id in NeDRex
n_rows = df.count()
df = df.where(df['targetId'].isin(set(["ENSG00000146648"])))
print(f"OpenTargets: Dropped {n_rows - df.count()} rows: ensembl id not in NeDRex");

# parse rows
print(f"OpenTargets: Adding {df.count()} rows to DB")

# generate tuples for insertion
tuple_list = df.rdd.map(lambda x: (x.diseaseIdValue, x.targetId, x.datasourceId)).collect()

        updates = (DisGeNetRow(row).parse(umls_nedrex_map) for row in reader)
        for chunk in _tqdm(_chunked(updates, 1_000), leave=False, desc="Parsing OpenTargets"):
            chunk = list(_chain(*chunk))
            chunk = [gawd.generate_update() for gawd in chunk]

            if not chunk:
                continue

            MongoInstance.DB[GeneAssociatedWithDisorder.collection_name].bulk_write(chunk)


def parse_gene_disease_associations():
    fname = get_file_location("gene_disease_associations")
    OpenTargetsParser(fname).parse()
