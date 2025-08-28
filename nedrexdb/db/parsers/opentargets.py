import gzip as _gzip
from collections import defaultdict as _defaultdict
from csv import DictReader as _DictReader
from itertools import chain as _chain
from pathlib import Path as _Path

from more_itertools import chunked as _chunked
from tqdm import tqdm as _tqdm

from nedrexdb.downloaders.opentargets import download_opentargets
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType


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
        return self._row["mapped_mondo"]
    
    def get_gene_id(self):
        return self._row["targetId"]
    
    def get_data_source(self):
        return [self._row["datasourceId"]]
    
    def get_score(self):
        return self._row["summaryScore"]

    def parse(self, ensembl2entrez) -> list[GeneAssociatedWithDisorder]:
        ensembl_gene = self.get_gene_id()
        source = self.get_data_source()
        disorder = self.get_disorder_id()
        scoreOpenTargets = self.get_score()

        gawds = [GeneAssociatedWithDisorder(sourceDomainId=ensembl2entrez[ensembl_gene], targetDomainId=disorder, dataSources=source, scoreOpenTargets=scoreOpenTargets)]

        return gawds


class OpenTargetsParser:
    def __init__(self, f: _Path, f_mapping: _Path, f_associations_summary: _Path):
        self.f = f
        self.f_mapping = f_mapping
        self.f_associations_summary = f_associations_summary

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
            .config("spark.driver.memory", "12g")
            .getOrCreate()
        )

        # read evidence dataset
        df = spark.read.parquet(str(self.f))
        
        # read disease file for creating an idspace mapping
        df_mapping = spark.read.parquet(str(self.f_mapping))
        
        # count rows with MONDO ID as primary id
        mondo_count = df_mapping.filter(F.col("id").like("MONDO%")).count()
        logger.debug(f"OpenTargets: {mondo_count} rows with MONDO ID as primary id in the disease file.")

        # split the id column to get the idspaces and their distribution 
        df_mapping_with_idspace = df_mapping.withColumn(
            "idspace", F.split(F.col("id"), "_")[0]
        )
        idspace_count = df_mapping_with_idspace.groupBy("idspace").count().orderBy("count", ascending=False)
        logger.debug(f"OpenTargets: Counting idspaces and their distribution in the disease file.")
        idspace_count.show()
        
        total_rows_disease_file = df_mapping.count()
        # Filter rows where dbXRefs contains a MONDO ID or primary id is MONDO
        df_mapping = df_mapping.withColumn(
            "mondo_id",
            F.expr("filter(dbXRefs, x -> x LIKE 'MONDO:%')")
        ).filter(
            (F.size("mondo_id") > 0) | (F.col("id").startswith("MONDO"))
        )
        logger.debug(f"OpenTargets: Filtered rows with MONDO ID as dbXref or primary id is MONDO: {df_mapping.count()} out of {total_rows_disease_file} could be mapped to MONDO. {total_rows_disease_file - df_mapping.count()} rows without MONDO ID that will be removed.")
        
        # Extract the first MONDO ID/primary id MONDO for each row
        df_mapping = df_mapping.withColumn(
            "first_mondo_id",
            F.when(F.size("mondo_id") > 0, F.col("mondo_id")[0])
            .otherwise(
                F.when(
                    F.col("id").startswith("MONDO"),
                    F.regexp_replace(F.col("id"), "_", ":")
                ).otherwise(F.lit(None))
            )
        )        
        
        # Count rows with multiple MONDO IDs
        # multiple_mondo_ids = df_mapping.filter(F.size(F.col("mondo_id")) > 1)
        # count_multiple_mondo_ids = multiple_mondo_ids.count()

        # if count_multiple_mondo_ids > 0:
        #     print(f"There are {count_multiple_mondo_ids} rows with more than one MONDO ID:")
        #     multiple_mondo_ids.select("id", "mondo_id").show(truncate=False)

        # Create a mapping dictionary
        mappings_diseases = {}
        for row in df_mapping.select("id", "dbXRefs", "first_mondo_id").collect():
            mondo_id = row["first_mondo_id"]
            dbxrefs = row["dbXRefs"]

            # Map each dbXRef entry to the MONDO ID
            for dbxref in dbxrefs:
                mappings_diseases[dbxref] = mondo_id

            # Ensure the MONDO ID maps to itself
            mappings_diseases[mondo_id] = mondo_id
            # also map primary id to MONDO ID
            id_entry = row["id"].replace("_", ":")
            mappings_diseases[id_entry] = mondo_id
        logger.debug(f"OpenTargets: Created mapping dictionary with {len(mappings_diseases)} entries.")
       
        # read associations summary to extract the scores
        df_associations_summary = spark.read.parquet(str(self.f_associations_summary))
        df_associations_summary_len = df_associations_summary.count()
        
        # split the diseaseId column to get the idspaces and the distribution
        df_associations_summary = df_associations_summary.withColumn(
            "idspace", F.split(F.col("diseaseId"), "_")[0]
        )
        idspace_count_summary = df_associations_summary.groupBy("idspace").count().orderBy("count", ascending=False)
        logger.debug(f"OpenTargets: Counting idspaces and their distribution in the associations summary file.")
        idspace_count_summary.show()
        
        summary_score_mapping = {}
        count_not_mapped_scores = 0
        count_mapped_scores = 0
        
        # create a dictionary with the mondo id and target id as key and the score as value
        for row in df_associations_summary.collect():
            disease_id = row["diseaseId"].replace("_", ":")
            target_id = row["targetId"]
            score = row["score"]

            # Map the disease ID to a MONDO ID using the mappings_diseases dictionary
            mondo_id = mappings_diseases.get(disease_id)

            # If the MONDO ID is found, add the score to the dictionary
            if mondo_id:
                key = f"{mondo_id}_{target_id}"
                summary_score_mapping[key] = score
                count_mapped_scores += 1
            else:
                count_not_mapped_scores += 1

        logger.debug(f"OpenTargets: Created summary score mapping dictionary with {len(summary_score_mapping)} entries.")
        logger.debug(f"OpenTargets: Mapped {count_mapped_scores} scores and could not map {count_not_mapped_scores} scores out of {df_associations_summary_len} rows.")
        
        # add columns for diseaseIdType and diseaseIdValue, and a cleaned diseaseId column
        split_col = _F.split(df['diseaseId'], '_')
        df = df.withColumn('diseaseIdType', split_col.getItem(0))
        df = df.withColumn('diseaseIdValue', split_col.getItem(1))
        df = df.withColumn('diseaseId_clean', F.regexp_replace(F.col('diseaseId'), '_', ':'))

        # show the distribution of the idspaces
        idspace_count_associations = df.groupBy("diseaseIdType").count().orderBy("count", ascending=False)
        idspace_count_associations.show()
        
        # broadcast the mappings_diseases dictionary for better performance
        mapping_broadcast = spark.sparkContext.broadcast(mappings_diseases)
        def map_to_mondo(id_clean):
            return mapping_broadcast.value.get(id_clean)

        map_to_mondo_udf = F.udf(map_to_mondo)

        # create a new column with the mapped MONDO ID to filter out the rows without a MONDO ID
        df = df.withColumn("mapped_mondo", map_to_mondo_udf(F.col("diseaseId_clean")))
        total_entries_association = df.count()
        df = df.filter(F.col("mapped_mondo").isNotNull())
        entries_after_filter = df.count()
        logger.debug(f"OpenTargets: Dropped {total_entries_association - entries_after_filter} rows out of {total_entries_association}: mondo id not in NeDRex. {entries_after_filter} rows left.")

        # add "opentargets_" prefix to datasourceId
        df = df.withColumn('datasourceId', _F.concat(_F.lit("opentargets_"), df['datasourceId']))
        
        # broadcast the summary_score_mapping dictionary for better performance
        results_broadcast = spark.sparkContext.broadcast(summary_score_mapping)
        def get_summary_score(mondo_id, target_id):
            key = f"{mondo_id}_{target_id}"
            return results_broadcast.value.get(key)
        get_summary_score_udf = F.udf(get_summary_score, DoubleType())

        # add a new column with the summary score for each row using the summary_score_mapping dictionary
        df = df.withColumn(
            "summaryScore",
            get_summary_score_udf(F.col("mapped_mondo"), F.col("targetId"))
        )
        count_before_score_mapping = df.count()
        df = df.filter(F.col("summaryScore").isNotNull())
        count_after_score_mapping = df.count()
        logger.debug(f"OpenTargets: Dropped {count_before_score_mapping - count_after_score_mapping} rows out of {count_before_score_mapping}: no score found. {count_after_score_mapping} rows left out of.")

        # replace "MONDO:" with "mondo." prefix for mapped mondo ids
        df = df.withColumn(
            'mapped_mondo', 
            F.regexp_replace(F.col('mapped_mondo'), 'MONDO:', 'mondo.')
        )

        # convert to pandas (java caused problems when filtering via pyspark directly)
        df = df.toPandas()

        # keep only rows with mondo id in NeDRex
        n_rows = df.shape[0]
        df = df[df['mapped_mondo'].isin(disorders)]
        logger.debug(f"OpenTargets: Dropped {n_rows - df.shape[0]} rows: mondo id not in NeDRex")

        # keep only rows with ensemble id in NeDRex
        n_rows = df.shape[0]
        df = df[df['targetId'].isin(set(ensembl2entrez.keys()))]
        logger.debug(f"OpenTargets: Dropped {n_rows - df.shape[0]} rows: ensembl id not in NeDRex")

        # parse rows
        logger.debug(f"OpenTargets: Adding {df.shape[0]} rows to DB out of {n_rows} rows.")

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
    fname_mapping = get_file_location("mapping_diseases")
    fname_associations_summary = get_file_location("gene_disease_associations_summary")
    OpenTargetsParser(fname, fname_mapping, fname_associations_summary).parse()
