import gzip as _gzip
from collections import defaultdict as _defaultdict
from csv import DictReader as _DictReader
from itertools import chain as _chain
from pathlib import Path as _Path

from more_itertools import chunked as _chunked
from tqdm import tqdm as _tqdm

from nedrexdb.logger import logger

from nedrexdb.db import MongoInstance
from nedrexdb.db.models.nodes.disorder import Disorder
from nedrexdb.db.models.nodes.gene import Gene
from nedrexdb.db.models.edges.gene_associated_with_disorder import GeneAssociatedWithDisorder
from nedrexdb.db.parsers import _get_file_location_factory

from pyspark.sql import SparkSession as _SparkSession
import pyspark.sql.functions as _F

get_file_location = _get_file_location_factory("opentargets")

class OpenTargetsRow:
    def __init__(self, row):
        self._row = row

    def get_disorder_id(self):
        return self._row["diseaseIdValue"]
    
    def get_gene_id(self):
        return self._row["targetId"]
    
    def get_data_source(self):
        return [self._row["datasourceId"]]

    def parse(self, ensembl2entrez) -> list[GeneAssociatedWithDisorder]:
        ensembl_gene = self.get_gene_id()
        source = self.get_data_source()
        disorder = self.get_disorder_id()

        gawds = [GeneAssociatedWithDisorder(sourceDomainId=ensembl2entrez[ensembl_gene], targetDomainId=disorder, dataSources=source)]

        return gawds


class OpenTargetsParser:
    def __init__(self, f: _Path):
        self.f = f

    def parse(self):

        # get mondo ids in NeDRex
        disorders = {dis["primaryDomainId"] for dis in Disorder.find(MongoInstance.DB)}

        # get ensembl to entrez mapping
        ensembl2entrez = {}
        for gene in Gene.find(MongoInstance.DB):
            for domainId in gene["domainIds"]:
                if domainId.startswith("ensembl."):
                    ensembl2entrez[domainId.removeprefix("ensembl.")] = gene["primaryDomainId"]

        # establish spark connection
        spark = (
            _SparkSession.builder
            .master('local[*]')
            .getOrCreate()
        )

        # read evidence dataset
        df = spark.read.parquet(str(self.f))

        # add columns for diseaseIdType and diseaseIdValue
        split_col = _F.split(df['diseaseId'], '_')
        df = df.withColumn('diseaseIdType', split_col.getItem(0))
        df = df.withColumn('diseaseIdValue', split_col.getItem(1))

        # filter for mondo ids
        n_rows = df.count()
        df = df.where(df['diseaseIdType'] == "MONDO")
        logger.debug(f"OpenTargets: Dropped {n_rows - df.count()} rows: no mondo id");

        # add "opentargets." prefix to datasourceId
        df = df.withColumn('datasourceId', _F.concat(_F.lit("opentargets."), df['datasourceId']))

        # add "mondo." prefix to diseaseIdValue
        df = df.withColumn('diseaseIdValue', _F.concat(_F.lit("mondo."), df['diseaseIdValue']))

        # convert to pandas (java caused problems when filtering via pyspark directly)
        df = df.toPandas()

        # keep only rows with mondo id in NeDRex
        n_rows = df.shape[0]
        df = df[df['diseaseIdValue'].isin(disorders)]
        logger.debug(f"OpenTargets: Dropped {n_rows - df.shape[0]} rows: mondo id not in NeDRex");

        # keep only rows sith ensemble id in NeDRex
        n_rows = df.shape[0]
        df = df[df['targetId'].isin(set(ensembl2entrez.keys()))]
        logger.debug(f"OpenTargets: Dropped {n_rows - df.shape[0]} rows: ensembl id not in NeDRex");

        # parse rows
        logger.debug(f"OpenTargets: Adding {df.shape[0]} rows to DB")

        updates = (OpenTargetsRow(row).parse(ensembl2entrez) for index, row in df.iterrows())
        for chunk in _tqdm(_chunked(updates, 1_000), leave=False, desc="Parsing OpenTargets"):
            chunk = list(_chain(*chunk))
            chunk = [gawd.generate_update() for gawd in chunk]

            if not chunk:
                continue

            MongoInstance.DB[GeneAssociatedWithDisorder.collection_name].bulk_write(chunk)


def parse_gene_disease_associations():
    logger.info("Parsing OpenTargets")
    fname = get_file_location("gene_disease_associations")
    OpenTargetsParser(fname).parse()
