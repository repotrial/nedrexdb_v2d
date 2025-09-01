from langchain_neo4j import Neo4jGraph
from nedrexdb import config as _config
import time

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

# only building embeddings for dev nodes and edges, except they are None.
# dev_nodes = ["Disorder", "Gene"]
# dev_edges = []
dev_nodes = None
dev_edges = None


def get_kg_connection() -> Neo4jGraph:
    NEO4J_URI = f'bolt://{_config["db.dev.neo4j_name"]}:7687'

    retry = 10
    while retry > 0:
        try:
            kg = Neo4jGraph(
                url=NEO4J_URI, username="", password="", database='neo4j'
            )
            return kg
        except Exception:
            retry -= 1
            if retry == 0:
                print("Could not connect to Neo4j database at " + NEO4J_URI)
                return None
            time.sleep(10)


def create_unique_node_constraint(con, node_type, attribute):
    query = f"CREATE CONSTRAINT {node_type.lower()}_{attribute.lower()}_unique FOR (n:{node_type}) REQUIRE n.{attribute} IS UNIQUE"
    con.query(query)


def create_constraints():
    kg = get_kg_connection()
    node_list = NODE_EMBEDDING_CONFIG.keys() if not dev_nodes else dev_nodes
    for node in node_list:
        create_unique_node_constraint(kg, node, "primaryDomainId")


def create_vector_indices():
    print("Starting indexing")

    kg = get_kg_connection()

    index_names = []

    node_list = NODE_EMBEDDING_CONFIG.keys() if not dev_nodes else dev_nodes

    # Only building embeddings for specified nodes
    retry_list = []
    num_retries = 5
    while num_retries > 0:
        for node in node_list:
            if not fill_vector_index(kg, "NODE", node):
                retry_list.append(node)
            else:
                index_names.append(f"{node.lower()}Embeddings")
        node_list = [node for node in retry_list]
        retry_list = []
        num_retries -= 1

    if len(node_list) > 0:
        print(f"Could not create embeddings successfully for the following nodes: {node_list}")

    edge_list = EDGE_EMBEDDING_CONFIG.keys() if not dev_edges else dev_edges
    retry_list = []
    num_retries = 5
    while num_retries > 0:
        for edge in edge_list:
            if not fill_vector_index(kg, "RELATIONSHIP", edge):
                retry_list.append(edge)
            else:
                index_names.append(f"{edge.lower()}Embeddings")
        edge_list = [edge for edge in retry_list]
        retry_list = []
        num_retries -= 1

    if len(edge_list) > 0:
        print(f"Could not create embeddings successfully for the following edges: {edge_list}")

    if wait_for_database_ready(kg, index_names):
        print("Ready to switch to read-only mode")
    else:
        print("Something went wrong with the index build")


def get_node_info_string(node_name, node_embedding_config):
    """
    Generates a Cypher string snippet for node embeddings in a more readable way.

    Args:
        node_name (str): The name of the node label (used to look up the config).
        node_embedding_config (dict): The configuration dictionary.

    Returns:
        str: A Cypher string for concatenating node properties.
    """
    config = node_embedding_config.get(node_name, {})
    parts = ["coalesce(x.type, '') + ' with ID ' + x.primaryDomainId + ':'"]

    for attribute, format_config in config.items():
        prefix = format_config.get('prefix', ' ')
        suffix = format_config.get('suffix', ' ')
        attribute_type = format_config.get('type', 'string')

        if attribute_type == "list":
            part = f"'{prefix}' + coalesce(apoc.text.join(x.{attribute}, ', '), '') + '{suffix};'"
        else:
            part = f"'{prefix}' + coalesce(x.{attribute}, '') + '{suffix};'"
        parts.append(part)

    return " + ".join(parts)


def get_edge_info_string(edge_name, edge_embedding_config):
    """
    Generates a Cypher string snippet for edge embeddings and fixes a likely bug.

    Args:
        edge_name (str): The name of the edge type (used to look up the config).
        edge_embedding_config (dict): The configuration dictionary.

    Returns:
        str: A Cypher string for concatenating edge and node properties.
    """
    config = edge_embedding_config.get(edge_name, {})
    link_term = config.get("link_term", "is connected to")

    base_info = f"coalesce(entry.s.type, '') + ' ' + coalesce(entry.s.displayName, '') + ' with ID ' + entry.s.primaryDomainId + ' {link_term} ' + coalesce(entry.t.type, '') + ' ' + coalesce(entry.t.displayName, '') + ' with ID ' + entry.t.primaryDomainId"
    parts = [base_info]

    if "attributes" in config:
        parts.append("' and has properties:'")
        for attribute, format_config in config["attributes"].items():
            prefix = format_config.get('prefix', ' ')
            suffix = format_config.get('suffix', ' ')
            attribute_type = format_config.get('type', 'string')

            if attribute_type == "list":
                part = f"'{prefix}' + coalesce(apoc.text.join(entry.r.{attribute}, ', '), '') + '{suffix};'"
            else:
                part = f"'{prefix}' + coalesce(entry.r.{attribute}, '') + '{suffix};'"
            parts.append(part)

    return " + ".join(parts)

def fill_vector_index(con, entityType, name) -> bool:

    retries = 5
    try:
        start = time.time()
        from nedrexdb.llm import (_LLM_API_KEY, _LLM_BASE, _LLM_path, _LLM_model, _LLM_embedding_length)
        create_vector_index(con, entityType, name,_LLM_embedding_length)
        params = {"api_key": _LLM_API_KEY, "llm_base": _LLM_BASE, "llm_path": _LLM_path, "llm_model": _LLM_model}
        info_string = get_info_string(entityType, name, NODE_EMBEDDING_CONFIG, EDGE_EMBEDDING_CONFIG)
        if entityType == "NODE":
            query = create_node_vector_query(info_string, name)
        else:
            source_name = EDGE_EMBEDDING_CONFIG[name]["source"]
            target_name = EDGE_EMBEDDING_CONFIG[name]["target"]
            query = create_edge_vector_query(info_string, source_name, name, target_name)
            print(query)
        while retries > 0:
            retries -= 1
            try:
                con.query(query, params=params)
                break
            except Exception as e:
                print(e)
                print(f"Encountered an issue! Retry {6 - retries} retrying in 60s...")
                if retries == 0:
                    raise e
                time.sleep(60)
        duration = time.time() - start
        print(f"Building {name} embedding indexes finished after {duration} seconds")
        return True
    except Exception as e:
        print(e)
        print("Could not create vector index for " + name)
        return False

def get_info_string(element_type, name, node_config, edge_config):
    """
    Dispatcher function to get the correct info string for a node or edge.
    This prevents calling the wrong generator with the wrong config by
    routing the request based on the element_type.

    Args:
        element_type (str): The type of element, either "NODE" or "EDGE".
        name (str): The name of the node label or edge type.
        node_config (dict): The complete node embedding configuration dictionary.
        edge_config (dict): The complete edge embedding configuration dictionary.

    Returns:
        str: The generated Cypher string snippet.
    """
    if element_type.upper() == "NODE":
        return get_node_info_string(name, node_config)
    elif element_type.upper() == "RELATIONSHIP":
        return get_edge_info_string(name, edge_config)
    else:
        raise ValueError(f"Unknown element_type: {element_type}. Must be 'NODE' or 'EDGE'.")

def create_node_vector_query(node_info_string, name):
    escaped_node_info_string = node_info_string.replace("'", "\\'")
    query = f"""
    CALL apoc.periodic.iterate(
    'MATCH (n:{name}) WHERE n.embedding IS NULL
     WITH id(n) AS id
     WITH collect(id) AS ids
     UNWIND range(0, size(ids) - 1, 100) AS i
     RETURN ids[i..i+100] AS id_batch',
        'UNWIND id_batch AS id
        MATCH (n:{name}) WHERE id(n) = id
        WITH collect(n) AS batchNodes
         CALL apoc.ml.openai.embedding(
             [x IN batchNodes | {escaped_node_info_string}],
             $api_key,
             {{
                 endpoint: $llm_base,
                 path: $llm_path,
                 model: $llm_model,
                 enableBackOffRetries: true,
                 backOffRetries: 20,
                 exponentialBackoff: true
             }}
         ) YIELD index, embedding
         WITH batchNodes[index] as node, embedding
         CALL db.create.setNodeVectorProperty(node, "embedding", embedding) 
         RETURN count(*)',
        {{
            batchSize: 10,
            parallel: false,
            params: {{
                api_key: $api_key,
                llm_base: $llm_base,
                llm_path: $llm_path,
                llm_model: $llm_model
            }}
        }}
    )
    """
    return query



def create_edge_vector_query(edge_info_string, source_name, name, target_name):
    escaped_node_info_string = edge_info_string.replace("'", "\\'")
    query = f"""
      CALL apoc.periodic.iterate(
          'MATCH (s:{source_name})-[r:{name}]-(t:{target_name}) WHERE r.embedding IS NULL
           WITH id(r) AS id
           WITH collect(id) AS ids
           UNWIND range(0, size(ids) - 1, 100) AS i
           RETURN ids[i..i+100] AS id_batch',
           'UNWIND id_batch AS id
           MATCH (s:{source_name})-[r:{name}]-(t:{target_name}) WHERE id(r) = id
           WITH collect({{s:s, r:r, t:t}}) AS batchEntries
          CALL apoc.ml.openai.embedding(
              [entry in batchEntries | {escaped_node_info_string}], 
              $api_key, 
              {{
                  endpoint: $llm_base,
                  path: $llm_path,
                  model: $llm_model,
                  enableBackOffRetries: true,
                  backOffRetries: 20,
                  exponentialBackoff: true
              }}
          ) YIELD index, embedding
          WITH batchEntries[index] as entry, embedding 
          CALL db.create.setRelationshipVectorProperty(entry.r, "embedding", embedding)
          RETURN count(*)',
          {{
            batchSize: 10,
            parallel: false,
            params: {{
                api_key: $api_key,
                llm_base: $llm_base,
                llm_path: $llm_path,
                llm_model: $llm_model
            }}
          }}
      )
    """
    return query


def create_vector_index(con, entityType, name, length=1024):
    props = {"index_name": f"{name.lower()}Embeddings"}
    if entityType == "NODE":
        con.query("""CREATE VECTOR INDEX $index_name IF NOT EXISTS
        FOR (d: """ + name + """) ON (d.embedding) 
        OPTIONS { indexConfig: {
          `vector.dimensions`: """+str(length)+""",
          `vector.similarity_function`: 'cosine'
        }}""", params=props)
    else:
        con.query("""CREATE VECTOR INDEX $index_name IF NOT EXISTS
               FOR ()-[r:""" + name + """]-() ON (r.embedding) 
               OPTIONS { indexConfig: {
                 `vector.dimensions`: """+str(length)+""",
                 `vector.similarity_function`: 'cosine'
               }}""", params=props)


def wait_for_database_ready(con, index_names=['bad_default']):
    for index_name in index_names:
        try:
            result = list(con.query("""
                SHOW INDEXES
                YIELD name, state, type, labelsOrTypes, properties
                WHERE name = $name
                RETURN *
            """, {"name": index_name}))

            if result:
                index = result[0]
                print(f"\nIndex details:")
                print(f"- Name: {index['name']}")
                print(f"- State: {index['state']}")
                print(f"- Type: {index['type']}")
                print(f"- Labels: {index['labelsOrTypes']}")
                print(f"- Properties: {index['properties']}")
                return index['state'] == 'ONLINE'
            else:
                print(f"\nNo index found with name {index_name}")
                return False

        except Exception as e:
            print(f"\nError checking index: {str(e)}")
            return False
