from langchain_neo4j import Neo4jGraph
from neo4j.exceptions import Neo4jError
from nedrexdb import config as _config
from nedrexdb.post_integration.neo4j_db_adjustments import create_vector_index
from nedrexdb.post_integration.embedding_config import NODE_EMBEDDING_CONFIG, EDGE_EMBEDDING_CONFIG
from nedrexdb.logger import logger
import time

node_keys = {key.lower(): key for key in NODE_EMBEDDING_CONFIG.keys()}
edge_keys = {key.lower(): key for key in EDGE_EMBEDDING_CONFIG.keys()}

def connect_to_session(session_type):
    # Connection details
    neo4j_container = _config[f"db.{session_type}.neo4j_name"]
    bolt_port = 7687

    NEO4J_URI = f'bolt://{neo4j_container}:{bolt_port}'

    retry = 10
    while retry > 0:
        try:
            kg = Neo4jGraph(url=NEO4J_URI, username="", password="", database='neo4j')
            # test if neo4j ready
            kg.query("RETURN 1")
            logger.info(f"Connected to Neo4j at {NEO4J_URI}")
            return kg
        except (DatabaseUnavailable, ServiceUnavailable, TransientError) as e:
            retry -= 1
            logger.warning(f"Neo4j not ready ({e}), retrying... ({retry} left)")
            time.sleep(15)
        except Exception as e:
            retry -= 1
            logger.warning(f"Could not connect to Neo4j at {NEO4J_URI}: {e}, retrying... ({retry} left)")
            time.sleep(10)

    raise RuntimeError(f"Could not connect to Neo4j at {NEO4J_URI} after {retry} retries")


def fetch_embeddings(toimport_embeddings):
    session = connect_to_session(session_type="live")
    result = {}
    for name in toimport_embeddings:
        logger.info(f"Import embeddings for {name}")
        try:
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

        except Neo4jError as e:  # catch Neo4j warnings
            msg = str(e)
            if "UnknownPropertyKeyWarning" in msg or "not in the database" in msg:
                logger.info(f"[{name}] No embeddings found (property missing) — skipped silently.")
            else:
                logger.warning(f"Neo4j error for '{name}': {e}")
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
            create_vector_index(session, "RELATIONSHIP", edge_keys[name])
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
            logger.debug(f"Could not upsert Embedding {name}.")
