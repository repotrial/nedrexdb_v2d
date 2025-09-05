from collections import defaultdict as _defaultdict
from pathlib import Path as _Path
import xml.etree.cElementTree as _et

from nedrexdb.db import MongoInstance
from nedrexdb.logger import logger
from nedrexdb.db.models.nodes.disorder import Disorder
from nedrexdb.db.models.nodes.gene import Gene
from nedrexdb.db.models.edges.gene_associated_with_disorder import (
    GeneAssociatedWithDisorder,
)
from nedrexdb.db.parsers import _get_file_location_factory

get_file_location = _get_file_location_factory("orphanet")

class OrphanetParser:
    def __init__(self, orphanet_path, nomenclature_pack):
        # file for disorder-genes associations
        self.associations_path = _Path(orphanet_path)
        # file for Orphacode-icd10 mapping
        self.nomenclature_path = _Path(nomenclature_pack)
    
    def get_orpha_mondo_mapping(self):
        orpha_mondo = _defaultdict(list)
        for item in Disorder.find(MongoInstance.DB):
            orpha_ids = [id.replace("orpha.", "") for id in item["domainIds"] if id.startswith("orpha.")]
            for orpha_id in orpha_ids:
                orpha_mondo[orpha_id].append(item["primaryDomainId"])
        return orpha_mondo
                


    def get_OrphaCode(self):
        depth = 0
        OrphaCode_list = []

        for event, elem in _et.iterparse(self.associations_path, events=["start", "end"]):
            if not elem.tag == "OrphaCode":
                continue
            if event == "start":
                depth += 1
            if event == "end":
                depth -= 1
            if depth == 0 and event == "end":
                OrphaCode_list.append(elem.text)

        return OrphaCode_list


    def get_genes(self):
        list_genes = []
        depth = 0

        for event, elem in _et.iterparse(self.associations_path, events=["start", "end"]):
            if not elem.tag == "DisorderGeneAssociationList":
                continue
            if event == "start":
                depth += 1
            if event == "end":
                depth -= 1
            if depth == 0 and event == "end":
                genes = []
                if elem.attrib["count"] != 0:
                    for i in elem.iter('Symbol'):
                        genes.append(i.text)
                list_genes.append(genes)

        return list_genes


    @logger.catch

    def parse(self):

        logger.info("Parsing OrphaNet")
        logger.info("\tParsing disorder-gene associations from OrphaNet")

        orpha_mondo = self.get_orpha_mondo_mapping()
        logger.info(f"Anzahl der Orphanet-IDs: {len(orpha_mondo)}")
        avg_mondo_ids = sum(len(mondo_ids) for mondo_ids in orpha_mondo.values()) / len(orpha_mondo)
        logger.info(f"Durchschnittliche Anzahl von MONDO-IDs pro Orphanet-ID: {avg_mondo_ids:.2f}")

        # have the same length
        ordered_OrphaCode = self.get_OrphaCode() # array with numbers as strings (orpha ids)
        ordered_associatedGenes = self.get_genes() # array with arrays of genes -> order matching to orpha ids they are associated with?
        logger.info(f"Number of Orphanet codes: {len(ordered_OrphaCode)}")
        logger.info(f"Number of associated genes: {len(ordered_associatedGenes)}")
        
        dict_disorder_genes = {}
        chunk = []
        num_unmapped_orpha = 0

        # go throuh all ordered Orpha codes (same order: associated genes)
        for i in range(len(ordered_OrphaCode)):
            current_OrphaCode = ordered_OrphaCode[i]
            mondo_ids = orpha_mondo[current_OrphaCode] # an array of mondo ids
            if len(mondo_ids) == 0:
                num_unmapped_orpha += 1
            for mondo in mondo_ids:
                if mondo not in dict_disorder_genes:
                    dict_disorder_genes[mondo] = set()
                dict_disorder_genes[mondo].update(ordered_associatedGenes[i]) # key: disorder id, value: set of genes that are associated with this disorder
        dict_disorder_genes = {key: list(value) for key, value in dict_disorder_genes.items()}
        logger.info(f"Number of unmapped Orphanet codes: {num_unmapped_orpha}")
        logger.info(len(dict_disorder_genes))
        avg_gene_ids = sum(len(gene_ids) for gene_ids in dict_disorder_genes.values()) / len(dict_disorder_genes)
        logger.info(f"Average number of genes per disorder: {avg_gene_ids:.2f}")
        
        # get gene id mapping
        symbol2entrez = {gene["approvedSymbol"]: gene["primaryDomainId"] for gene in Gene.find(MongoInstance.DB)}
        n_unmapped = 0
        n_added = 0

        for d, gs in dict_disorder_genes.items():
            for g in gs:
                if g in symbol2entrez:
                    n_added += 1
                    chunk.append(GeneAssociatedWithDisorder(
                            sourceDomainId = symbol2entrez[g],
                            targetDomainId = d,
                            dataSources = ["orphanet"]
                        ).generate_update())
                else:
                    n_unmapped += 1
        MongoInstance.DB[GeneAssociatedWithDisorder.collection_name].bulk_write(chunk)

        if n_unmapped:
            logger.info(f"Orphanet added {n_added} disease gene associations ({n_unmapped} skipped) ")


def parse_gene_disease_associations():
    logger.info("Parsing orphanet")
    fname = get_file_location("data")
    mapping_fname = get_file_location("mapping")
    OrphanetParser(fname, mapping_fname).parse()