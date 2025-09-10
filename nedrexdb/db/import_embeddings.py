from langchain_neo4j import Neo4jGraph
from nedrexdb import config as _config
from nedrexdb.post_integration.neo4j_db_adjustments import create_vector_index
from nedrexdb.post_integration.embedding_config import NODE_EMBEDDING_CONFIG, EDGE_EMBEDDING_CONFIG
import time
from nedrexdb.logger import logger

node_keys = {key.lower(): key for key in NODE_EMBEDDING_CONFIG.keys()}
edge_keys = {key.lower(): key for key in EDGE_EMBEDDING_CONFIG.keys()}

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
                logger.error("Could not connect to Neo4j database at " + NEO4J_URI)
                return
            time.sleep(5)
    return kg


def fetch_embeddings(toimport_embeddings):
    session = connect_to_session(session_type="live")
    result = {}
    for name in toimport_embeddings:
        if name in node_keys.keys():
            query = f"""
            MATCH (n:{node_keys[name]}) 
            WHERE n.embedding IS NOT NULL
            RETURN n.primaryDomainId AS id, n.embedding AS embedding
            """
            query_result = session.query(query)
            result[name] = [(record["id"], record["embedding"]) for record in query_result]
        elif name in edge_keys.keys():
            query = f"""
                MATCH (src)-[r:{edge_keys[name]}]->(dst)
                WHERE r.embedding IS NOT NULL
                RETURN 
                    src.primaryDomainId AS src_id,
                    dst.primaryDomainId AS dst_id,
                    r.embedding AS embedding
                """
            query_result = session.query(query)
            result[name] = [
                ((record["src_id"], record["dst_id"]), record["embedding"])
                for record in query_result
            ]
        else:
            logger.debug(f"Embedding {name} is not defined.")

    return result


def upsert_embeddings(embeddings):
    session = connect_to_session(session_type="dev")
    for name in embeddings:
        if name in node_keys.keys():
            create_vector_index(session, "NODE", node_keys[name])
            query = f"""
            UNWIND $nodes AS node
            MERGE (n:{node_keys[name]} {{ primaryDomainId: node.id }})
            SET n.embedding = node.embedding
            """
            session.query(
                query,
                {"nodes": [{"id": id_, "embedding": emb} for id_, emb in embeddings[name]]}
            )
        elif name in edge_keys.keys():
            create_vector_index(session, "EDGE", edge_keys[name])
            query = f"""
                UNWIND $edges AS edge
                MATCH (src {{ primaryDomainId: edge.src_id }})
                MATCH (dst {{ primaryDomainId: edge.dst_id }})
                MERGE (src)-[r:{edge_keys[name]}]->(dst)
                SET r.embedding = edge.embedding
                """
            session.query(
                query,
                {
                    "edges": [
                        {
                            "src_id": edge_id[0],  # unpack directly from tuple
                            "dst_id": edge_id[1],
                            "embedding": emb
                        }
                        for edge_id, emb in embeddings[name]
                    ]
                }
            )
        else:
            logger.error(f"Could not upsert Embedding {name}.")
