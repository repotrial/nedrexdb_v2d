NODE_EMBEDDING_CONFIG = {
    "Disorder": {
        "displayName": {"prefix": "DisplayName: ", "suffix": "", "type": "string"},
        "synonyms": {"prefix": "Synonyms: ", "suffix": "", "type": "list"},
        "description": {"prefix": "Description: ", "suffix": "", "type": "string"},
        "domainIds": {"prefix": "Other used IDs: ", "suffix": "", "type": "list"},
        # "dataSources": {"prefix": "Data Sources: ", "suffix": "", "type": "list"},
    },
    "Gene": {
        "displayName": {"prefix": "DisplayName: ", "suffix": "", "type": "string"},
        "approvedSymbol": {"prefix": "Approved Symbol: ", "suffix": "", "type": "string"},
        "description": {"prefix": "Description: ", "suffix": "", "type": "string"},
        "geneType": {"prefix": "GeneType: ", "suffix": "", "type": "string"},
        "synonyms": {"prefix": "Synonyms: ", "suffix": "", "type": "list"},
        "symbols": {"prefix": "Alternative Symbols: ", "suffix": "", "type": "list"},
        # "dataSources": {"prefix": "Data Sources: ", "suffix": "", "type": "list"},
        "domainIds": {"prefix": "Other used IDs: ", "suffix": "", "type": "list"},
    },
    "Drug": {
        "displayName": {"prefix": "DisplayName: ", "suffix": "", "type": "string"},
        "domainIds": {"prefix": "Other used IDs: ", "suffix": "", "type": "list"},
        # "dataSources": {"prefix": "Data Sources: ", "suffix": "", "type": "list"},
        "casNumber": {"prefix": "This exact CAS number: ", "suffix": "", "type": "string"},
    },
    "Protein": {
        "displayName": {"prefix": "DisplayName: ", "suffix": "", "type": "string"},
        "geneName": {"prefix": "Gene name: ", "suffix": "", "type": "string"},
        "synonyms": {"prefix": "Synonyms: ", "suffix": "", "type": "list"},
        "domainIds": {"prefix": "Other used IDs: ", "suffix": "", "type": "list"},
        # "dataSources": {"prefix": "Data Sources: ", "suffix": "", "type": "list"},
        "reviewed": {"prefix": "Review status: ", "suffix": "", "type": "boolean"},
        "comments": {"prefix": "the following comments: ", "suffix": "", "type": "string"},
    },
    "GO": {
        "displayName": {"prefix": "DisplayName: ", "suffix": "", "type": "string"},
        "synonyms": {"prefix": "Synonyms: ", "suffix": "", "type": "list"},
        "description": {"prefix": "Description: ", "suffix": "", "type": "string"},
        "domainIds": {"prefix": "Other used IDs: ", "suffix": "", "type": "list"},
        "dataSources": {"prefix": "Data Sources: ", "suffix": "", "type": "list"},
    },
    # "GenomicVariant": {
    #     "domainIds": {"prefix": "Other used IDs: ", "suffix": "", "type": "list"},
    #     "dataSources": {"prefix": "Data Sources: ", "suffix": "", "type": "list"},
    #     "referenceSequence": {"prefix": "Reference Sequence: ", "suffix": "", "type": "string"},
    #     "alternativeSequence": {"prefix": "Alternative Sequence: ", "suffix": "", "type": "string"},
    #     "chromosome": {"prefix": "Chromosome: ", "suffix": "", "type": "string"},
    #     "position": {"prefix": "Position: ", "suffix": "", "type": "string"},
    #     "variantType": {"prefix": "Variant Type: ", "suffix": "", "type": "string"},
    # },
    "Pathway": {
        "displayName": {"prefix": "DisplayName: ", "suffix": "", "type": "string"},
        "domainIds": {"prefix": "Other used IDs: ", "suffix": "", "type": "list"},
        # "dataSources": {"prefix": "Data Sources: ", "suffix": "", "type": "list"},
        # "species": {"prefix": "Species: ", "suffix": "", "type": "string"},
        # "taxid": {"prefix": "taxid: ", "suffix": "", "type": "string"},
    },
    "Phenotype": {
        "displayName": {"prefix": "DisplayName: ", "suffix": "", "type": "string"},
        "synonyms": {"prefix": "Synonyms: ", "suffix": "", "type": "list"},
        "description": {"prefix": "Description: ", "suffix": "", "type": "string"},
        "domainIds": {"prefix": "Other used IDs: ", "suffix": "", "type": "list"},
        # "dataSources": {"prefix": "Data Sources: ", "suffix": "", "type": "list"},
    },
    "SideEffect": {
        "displayName": {"prefix": "DisplayName: ", "suffix": "", "type": "string"},
        "domainIds": {"prefix": "Other used IDs: ", "suffix": "", "type": "list"},
        # "dataSources": {"prefix": "Data Sources: ", "suffix": "", "type": "list"},
    },
    "Signature": {
        "displayName": {"prefix": "DisplayName: ", "suffix": "", "type": "string"},
        "domainIds": {"prefix": "Other used IDs: ", "suffix": "", "type": "list"},
        # "dataSources": {"prefix": "Data Sources: ", "suffix": "", "type": "list"},
        # "database": {"prefix": "Database: ", "suffix": "", "type": "string"},
    },
    "Tissue": {
        "displayName": {"prefix": "DisplayName: ", "suffix": "", "type": "string"},
        "domainIds": {"prefix": "Other used IDs: ", "suffix": "", "type": "list"},
        # "dataSources": {"prefix": "Data Sources: ", "suffix": "", "type": "list"},
    }
}


EDGE_EMBEDDING_CONFIG = {
    "GeneAssociatedWithDisorder": {
        "source": "Gene",
        "link_term": "is associated with",
        "target": "Disorder",
        "attributes": {
            "dataSources": {"prefix": "Data Source: ", "suffix": "", "type": "list"}
        }
    },
    "DrugHasIndication": {
        "source": "Drug",
        "link_term": "has an indication for",
        "target": "Disorder",
        "attributes": {
            "dataSources": {"prefix": "Data Source: ", "suffix": "", "type": "list"}
        }
    },
    "DrugHasTarget": {
        "source": "Drug",
        "link_term": "has the known target",
        "target": "Protein",
        "attributes": {
            "dataSources": {"prefix": "Data Source: ", "suffix": "", "type": "list"}
        }
    },
    "DisorderHasPhenotype": {
        "source": "Disorder",
        "link_term": "exhibits the known phenotype",
        "target": "Phenotype",
        # "attributes": {
        #     "dataSources": {"prefix": "Data Source: ", "suffix": "", "type": "list"}
        # }
    },
    "DisorderIsSubtypeOfDisorder": {
        "source": "Disorder",
        "link_term": "is subtype of",
        "target": "Disorder",
        # "attributes": {
        #     "dataSources": {"prefix": "Data Source: ", "suffix": "", "type": "list"}
        # }
    },
    "DrugHasContraindication": {
        "source": "Drug",
        "link_term": "is contraindicated in",
        "target": "Disorder",
        # "attributes": {
        #     "dataSources": {"prefix": "Data Source: ", "suffix": "", "type": "list"}
        # }
    },
    "DrugHasSideEffect": {
        "source": "Drug",
        "link_term": "has the known side effect",
        "target": "SideEffect",
        # "attributes": {
        #     "dataSources": {"prefix": "Data Source: ", "suffix": "", "type": "list"},
        #     "maximum_frequency": {"prefix": "Maximum Frequency: ", "suffix": "", "type": "string"},
        #     "minimum_frequency": {"prefix": "Minimum Frequency: ", "suffix": "", "type": "string"}
        # }
    },
    # "GOIsSubtypeOfGO": {
    #     "source": "GO",
    #     "link_term": "is subtype of",
    #     "target": "GO",
    #     "attributes": {
    #         "dataSources": {"prefix": "Data Source: ", "suffix": "", "type": "list"}
    #     }
    # },
    "GeneExpressedInTissue": {
        "source": "Gene",
        "link_term": "is expressed in",
        "target": "Tissue",
        # "attributes": {
        #     "dataSources": {"prefix": "Data Source: ", "suffix": "", "type": "list"},
            # "TPM": {"prefix": "TPM: ", "suffix": "", "type": "string"},
            # "nTPM": {"prefix": "nTPM: ", "suffix": "", "type": "string"},
            # "pTPM": {"prefix": "pTPM: ", "suffix": "", "type": "string"},
        # }
    },
    "ProteinEncodedByGene": {
        "source": "Protein",
        "link_term": "is encoded by",
        "target": "Gene",
        "attributes": {
            "dataSources": {"prefix": "Data Source: ", "suffix": "", "type": "list"}
        }
    },
    # "ProteinExpressedInTissue": {
    #     "source": "Protein",
    #     "link_term": "is expressed by",
    #     "target": "Tissue",
        # "attributes": {
        #     "dataSources": {"prefix": "Data Source: ", "suffix": "", "type": "list"},
            # "level": {"prefix": "Expression level: ", "suffix": "", "type": "string"},
        # }
    # },
    "ProteinHasGoAnnotation": {
        "source": "Protein",
        "link_term": "has GO annotation",
        "target": "GO",
        # "attributes": {
        #     "dataSources": {"prefix": "Data Source: ", "suffix": "", "type": "list"},
        #     "qualifiers": {"prefix": "Qualifiers: ", "suffix": "", "type": "list"},
        # }
    },
    # "ProteinHasSignature": {
    #     "source": "Protein",
    #     "link_term": "has signature",
    #     "target": "Signature",
    #     "attributes": {
    #         "dataSources": {"prefix": "Data Source: ", "suffix": "", "type": "list"}
    #     }
    # },
    # "ProteinInPathway": {
    #     "source": "Protein",
    #     "link_term": "is in the pathway",
    #     "target": "Pathway",
        # "attributes": {
        #     "dataSources": {"prefix": "Data Source: ", "suffix": "", "type": "list"}
        # }
    # },
    # "ProteinInteractsWithProtein": {
    #     "source": "Protein",
    #     "link_term": "interacts with",
    #     "target": "Protein",
        # "attributes": {
        #     "dataSources": {"prefix": "Data Source: ", "suffix": "", "type": "list"},
        #     "evidenceTypes": {"prefix": "Evidence Type: ", "suffix": "", "type": "list"},
        #     "methods": {"prefix": "Method/Approach: ", "suffix": "", "type": "list"},
        #     "subcellularLocations": {"prefix": "Subcellular Locations: ", "suffix": "", "type": "list"},
        #     "tissues": {"prefix": "Tissues: ", "suffix": "", "type": "list"},
        # }
    # },
    "SideEffectSameAsPhenotype": {
        "source": "SideEffect",
        "link_term": "is the same as",
        "target": "Phenotype",
        # "attributes": {
        #     "dataSources": {"prefix": "Data Source: ", "suffix": "", "type": "list"}
        # }
    },
    # "VariantAffectsGene": {
    #     "source": "GenomicVariant",
    #     "link_term": "effects",
    #     "target": "Gene",
        # "attributes": {
        #     "dataSources": {"prefix": "Data Source: ", "suffix": "", "type": "list"}
        # }
    # },
    "VariantAssociatedWithDisorder": {
        "source": "GenomicVariant",
        "link_term": "is associated with",
        "target": "Disorder",
        # "attributes": {
        #     # "dataSources": {"prefix": "Data Source: ", "suffix": "", "type": "list"},
        #     "effects": {"prefix": "Effects: ", "suffix": "", "type": "list"},
        #     # "accession": {"prefix": "Accession: ", "suffix": "", "type": "string"},
        #     "reviewStatus": {"prefix": "Review Status: ", "suffix": "", "type": "string"}
        # }
    },
}