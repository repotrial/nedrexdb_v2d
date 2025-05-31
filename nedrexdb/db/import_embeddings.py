from langchain_neo4j import Neo4jGraph
from nedrexdb import config as _config
import time

# Define label and property key of embeddings
LABEL = "Drug"
EMBEDDING_PROPERTY = "embedding"
ID_PROPERTY = "domainIds"  # or your unique node property


def connect_to_session(session_type):
    # Connection details
    neo4j_container = _config[f"db.{session_type}.neo4j_name"]
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
    return kg



def fetch_embeddings():
    session = connect_to_session(session_type="live")
    query = f"""
    MATCH (n:{LABEL}) 
    WHERE n.{EMBEDDING_PROPERTY} IS NOT NULL
    RETURN n.{ID_PROPERTY} AS id, n.{EMBEDDING_PROPERTY} AS embedding
    """
    result = session.query(query)
    return [(record["id"], record["embedding"]) for record in result]

def upsert_embeddings(session, data):
    query = f"""
    UNWIND $nodes AS node
    MERGE (n:{LABEL} {{ {ID_PROPERTY}: node.id }})
    SET n.{EMBEDDING_PROPERTY} = node.embedding
    """
    session.run(query, nodes=[{"id": id_, "embedding": emb} for id_, emb in data])

def main():
    source_driver = GraphDatabase.driver(uri)
    target_driver = GraphDatabase.driver(uri)

    with source_driver.session() as source_session, target_driver.session() as target_session:
        embeddings = fetch_embeddings(source_session)
        print(f"Fetched {len(embeddings)} embeddings from source Neo4j.")
        upsert_embeddings(target_session, embeddings)
        print(f"Upserted embeddings into target Neo4j.")

    source_driver.close()
    target_driver.close()
