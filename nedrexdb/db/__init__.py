from dataclasses import dataclass as _dataclass

from pymongo import MongoClient as _MongoClient

from nedrexdb import config as _config
from nedrexdb.logger import logger
from nedrexdb.db.models.nodes import (
    disorder as _disorder,
    drug as _drug,
    gene as _gene,
    genomic_variant as _genomic_variant,
    pathway as _pathway,
    phenotype as _phenotype,
    protein as _protein,
    go as _go,
    side_effect as _side_effect,
    tissue as _tissue,
)
from nedrexdb.db.models.edges import (
    disorder_has_phenotype as _disorder_has_phenotype,
    disorder_is_subtype_of_disorder as _disorder_is_subtype_of_disorder,
    drug_has_contraindication as _drug_has_contraindication,
    drug_has_indication as _drug_has_indication,
    drug_has_target as _drug_has_target,
    drug_has_side_effect as _drug_has_side_effect,
    gene_associated_with_disorder as _gene_associated_with_disorder,
    gene_expressed_in_tissue as _gene_expressed_in_tissue,
    protein_encoded_by_gene as _protein_encoded_by_gene,
    protein_expressed_in_tissue as _protein_expressed_in_tissue,
    protein_in_pathway as _protein_in_pathway,
    protein_interacts_with_protein as _protein_interacts_with_protein,
    go_is_subtype_of_go as _go_is_subtype_of_go,
    protein_has_go_annotation as _protein_has_go_annotation,
    side_effect_same_as_phenotype as _side_effect_same_as_phenotype,
    variant_affects_gene as _variant_affects_gene,
    variant_associated_with_disorder as _variant_associated_with_disorder,
)


@_dataclass
class MongoInstance:
    CLIENT = None
    DB = None

    @classmethod
    def connect(cls, version):
        if version not in ("live", "dev"):
            raise ValueError(f"version given ({version!r}) should be 'live' or 'dev")

        port = _config[f"db.{version}.mongo_port"]
        host = _config[f"db.{version}.mongo_name"]
        dbname = _config["db.mongo_db"]
        logger.debug(f"Connecting to MongoDB... {host}:{port}")
        cls.CLIENT = _MongoClient(host=host, port=27017)
        cls.DB = cls.CLIENT[dbname]

    @classmethod
    def set_indexes(cls):
        if cls.DB is None:
            raise ValueError("run nedrexdb.db.connect() first to connect to MongoDB")
        # Nodes
        _disorder.Disorder.set_indexes(cls.DB)
        _drug.Drug.set_indexes(cls.DB)
        _gene.Gene.set_indexes(cls.DB)
        _genomic_variant.GenomicVariant.set_indexes(cls.DB)
        _pathway.Pathway.set_indexes(cls.DB)
        _phenotype.Phenotype.set_indexes(cls.DB)
        _protein.Protein.set_indexes(cls.DB)
        _tissue.Tissue.set_indexes(cls.DB)
        _side_effect.SideEffect.set_indexes(cls.DB)
        _go.GO.set_indexes(cls.DB)
        # Edges
        _disorder_has_phenotype.DisorderHasPhenotype.set_indexes(cls.DB)
        _disorder_is_subtype_of_disorder.DisorderIsSubtypeOfDisorder.set_indexes(cls.DB)
        _drug_has_contraindication.DrugHasContraindication.set_indexes(cls.DB)
        _drug_has_indication.DrugHasIndication.set_indexes(cls.DB)
        _drug_has_target.DrugHasTarget.set_indexes(cls.DB)
        _drug_has_side_effect.DrugHasSideEffect.set_indexes(cls.DB)
        _gene_associated_with_disorder.GeneAssociatedWithDisorder.set_indexes(cls.DB)
        _gene_expressed_in_tissue.GeneExpressedInTissue.set_indexes(cls.DB)
        _protein_encoded_by_gene.ProteinEncodedByGene.set_indexes(cls.DB)
        _protein_expressed_in_tissue.ProteinExpressedInTissue.set_indexes(cls.DB)
        _protein_in_pathway.ProteinInPathway.set_indexes(cls.DB)
        _protein_interacts_with_protein.ProteinInteractsWithProtein.set_indexes(cls.DB)
        _go_is_subtype_of_go.GOIsSubtypeOfGOBase.set_indexes(cls.DB)
        _protein_has_go_annotation.ProteinHasGOAnnotation.set_indexes(cls.DB)
        _side_effect_same_as_phenotype.SideEffectSameAsPhenotype.set_indexes(cls.DB)
        _variant_affects_gene.VariantAffectsGene.set_indexes(cls.DB)
        _variant_associated_with_disorder.VariantAssociatedWithDisorder.set_indexes(cls.DB)
