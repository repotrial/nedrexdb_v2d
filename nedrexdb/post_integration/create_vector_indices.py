from langchain_community.graphs import Neo4jGraph
from nedrexdb import config as _config
import time

NODE_EMBEDDING_CONFIG = {
    "Disorder":{
        "displayName": {"prefix":"DisplayName: ", "suffix":"", "type": "string"},
        "synonyms": {"prefix":"Synonyms: ", "suffix":"", "type": "list"},
        "description": {"prefix":"Description: ", "suffix":"", "type": "string"},
        "domainIds": {"prefix": "Other used IDs: ", "suffix": "", "type": "list"},
        "dataSources": {"prefix": "Data Sources: ", "suffix": "", "type": "list"},
    },
    "Gene":{
        "displayName": {"prefix":"DisplayName: ", "suffix":"", "type": "string"},
        "approvedSymbol":{"prefix":"Approved Symbol: ", "suffix":"", "type": "string"},
        "description": {"prefix":"Description: ", "suffix":"", "type": "string"},
        "geneType": {"prefix":"GeneType: ", "suffix":"", "type": "string"},
        "synonyms": {"prefix": "Synonyms: ", "suffix": "", "type": "list"},
        "symbols": {"prefix": "Alternative Symbols: ", "suffix": "", "type": "list"},
        "dataSources":{"prefix": "Data Sources: ", "suffix": "", "type": "list"},
        "domainIds": {"prefix": "Other used IDs: ", "suffix": "", "type": "list"},
    },
    "Drug":{
        "displayName": {"prefix":"DisplayName: ", "suffix":"", "type": "string"},
        "domainIds":{"prefix":"Other used IDs: ", "suffix":"", "type": "list"},
        "dataSources": {"prefix": "Data Sources: ", "suffix": "", "type": "list"},
        "casNumber": {"prefix":"This exact CAS number: ", "suffix":"", "type": "string"},
    },
    "Protein":{
        "displayName": {"prefix":"DisplayName: ", "suffix":"", "type": "string"},
        "geneName": {"prefix":"Gene name: ", "suffix":"", "type": "string"},
        "synonyms": {"prefix": "Synonyms: ", "suffix": "", "type": "list"},
        "domainIds":{"prefix":"Other used IDs: ", "suffix":"", "type": "list"},
        "dataSources": {"prefix": "Data Sources: ", "suffix": "", "type": "list"},
        "reviewed":{"prefix":"Review status: ", "suffix":"", "type": "boolean"},
        "comments": {"prefix":"the following comments: ", "suffix":"", "type": "string"},
    }
}



EDGE_EMBEDDING_CONFIG = {
    "GeneAssociatedWithDisorder":{
        "source": "Gene",
        "link_term": "is associated with",
        "target":"Disorder",
        "attributes":{
            "dataSources":{"prefix": "Data Source: ", "suffix": "", "type": "list"}
        }
    },
    "DrugHasIndication":{
        "source": "Drug",
        "link_term": "has an indication for",
        "target": "Disorder",
        "attributes":{
            "dataSources":{"prefix": "Data Source: ", "suffix": "", "type": "list"}
        }
    },
    "DrugHasTarget": {
        "source": "Drug",
        "link_term": "has the known target",
        "target": "Protein",
        "attributes": {
            "dataSources": {"prefix": "Data Source: ", "suffix": "", "type": "list"}
        }
    }
}

def create_vector_indices():
    neo4j_container = _config["db.dev.neo4j_name"]
    bolt_port = 7687

    NEO4J_URI = f'bolt://{neo4j_container}:{bolt_port}'

    retry = 5
    while retry > 0:
        try:
            kg = Neo4jGraph(
                url=NEO4J_URI, username="", password="", database='neo4j'
            )
            break
        except Exception:
            retry -= 1
            if retry == 0:
                print("Could not connect to Neo4j database at " + NEO4J_URI)
                return
            time.sleep(5)
    for node in NODE_EMBEDDING_CONFIG.keys():
        fill_vector_index(kg, "NODE", node)
    for edge in EDGE_EMBEDDING_CONFIG.keys():
        fill_vector_index(kg, "RELATIONSHIP", edge)
    if wait_for_database_ready(kg):
        print("Ready to switch to read-only mode")
    else:
        print("Something went wrong with the index build")


def get_node_info_string(node_name):
    info_string = """coalesce(x.type, '') +  ' with ID ' + x.primaryDomainId +':'"""
    for attribute, format in NODE_EMBEDDING_CONFIG[node_name].items():
        prefix = f" {format.get('prefix', ' ')} "
        suffix = f" {format.get('suffix', ' ')} "
        attribute_type =format.get('type', 'string')

        info_string += f"+ '{prefix}'"
        if attribute_type == "list":
            info_string += f"+ coalesce( apoc.text.join(x.{attribute},', '), '')"
        else:
            info_string += f"+ coalesce(x.{attribute}, '')"
        info_string += f"+ '{suffix};'"
    return info_string


def get_edge_info_string(edge_name):
    link_term = EDGE_EMBEDDING_CONFIG[edge_name]["link_term"]
    info_string = f"coalesce(entry.s.type, '') +' '+ coalesce(entry.s.displayName, '') +' with ID ' + entry.s.primaryDomainId + ' {link_term} ' + coalesce(entry.t.type, '') +' '+coalesce(entry.t.displayName, '')+'  with ID '+ entry.t.primaryDomainId +' and has properties:'"
    for attribute, format in EDGE_EMBEDDING_CONFIG[edge_name]["attributes"].items():
        prefix = format.get('prefix', ' ')
        suffix = format.get('suffix', ' ')
        attribute_type = format.get('type', 'string')

        info_string += f"+'{prefix}'"
        if attribute_type == "list":
            info_string += f"+ coalesce( apoc.text.join(entry.r.{attribute},', '), '')"
        else:
            info_string += f"+ coalesce(d.{attribute}, '')"
        info_string += f"+ '{suffix};'"
    return info_string

def fill_vector_index(con, entityType, name):

    try:
        start = time.time()
        create_vector_index(con, entityType, name)
        from nedrexdb.llm import (_LLM_BASE, _LLM_path, _LLM_model)
        params = {"llm_base": _LLM_BASE, "llm_path": _LLM_path, "llm_model": _LLM_model}
        if entityType == "NODE":
            info_string = get_node_info_string(name)
            query = create_node_vector_query(info_string, name)
            con.query(query, params=params)
        else:
            info_string = get_edge_info_string(name)
            source_name = EDGE_EMBEDDING_CONFIG[name]["source"]
            target_name = EDGE_EMBEDDING_CONFIG[name]["target"]
            query = create_edge_vector_query(info_string, source_name, name, target_name)
            con.query(query, params=params)
        duration = time.time() - start
        print(f"Building {name} embedding indexes finished after {duration} seconds")
    except Exception as e:
        print(e)
        print("Could not create vector index for " + name)

def create_node_vector_query(node_info_string, name):
    query = """
      MATCH (n: """+name+""")
WITH collect(n) as allNodes
UNWIND range(0, size(allNodes)-1, 1000) as i
WITH i, allNodes[i..i+1000] as batchNodes
WHERE size(batchNodes) > 0
CALL apoc.ml.openai.embedding(
    [x in batchNodes | """+node_info_string+"""], 
    "no_key", 
    {
        endpoint: $llm_base,
        path: $llm_path,
        model: $llm_model,
        enableBackOffRetries: true,
        backOffRetries: 10,
        exponentialBackoff: true
    }
) YIELD index, embedding
WITH batchNodes[index] as n, embedding CALL db.create.setNodeVectorProperty(n, "embedding", embedding);"""
    return query


def create_edge_vector_query(edge_info_string, source_name, name, target_name):
    query = """MATCH (s: """+source_name+""")-[r: """+name+"""]-(t: """+target_name+""")
    WITH collect({s:s,r:r,t:t}) as allEntries
    UNWIND range(0, size(allEntries)-1, 1000) as i
    WITH i, allEntries[i..i+1000] as batchEntries
    WHERE size(batchEntries) > 0
    CALL apoc.ml.openai.embedding(
        [entry in batchEntries | """ + edge_info_string + """
        ], 
        "no_key", 
        {
            endpoint: $llm_base,
            path: $llm_path,
            model: $llm_model,
            enableBackOffRetries: true,
            backOffRetries: 10,
            exponentialBackoff: true
        }
    ) YIELD index, embedding
    WITH batchEntries[index] as entry, embedding CALL db.create.setRelationshipVectorProperty(entry.r, "embedding", embedding);"""
    return query


def create_vector_index(con, entityType, name):
    props = {"name":name, "index_name":f"{name.lower()}Embeddings"}
    if entityType == "NODE":
        con.query("""CREATE VECTOR INDEX $index_name IF NOT EXISTS
        FOR (d: """+name+""") ON (d.embedding) 
        OPTIONS { indexConfig: {
          `vector.dimensions`: 1024,
          `vector.similarity_function`: 'cosine'
        }}""", params=props)
    else:
        con.query("""CREATE VECTOR INDEX $index_name IF NOT EXISTS
               FOR ()-[r:"""+name+"""]-() ON (r.embedding) 
               OPTIONS { indexConfig: {
                 `vector.dimensions`: 1024,
                 `vector.similarity_function`: 'cosine'
               }}""", params=props)


def wait_for_database_ready(con, index_name='disorder_embeddings'):
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
