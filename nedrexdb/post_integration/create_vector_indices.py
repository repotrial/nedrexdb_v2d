from langchain_community.graphs import Neo4jGraph
from nedrexdb import config as _config
import time



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

    res = kg.query("MATCH (n) RETURN n LIMIT 25")
    print(res)

    print("Starting with indexing!")
    create_disease_embeddings(kg)
    if wait_for_database_ready(kg):
        print("Ready to switch to read-only mode")
    else:
        print("Something went wrong with the index build")


def create_disease_embeddings(con):

    from nedrexdb.llm import (_LLM_BASE, _LLM_path, _LLM_model)
    con.query("""CREATE VECTOR INDEX disorder_embeddings IF NOT EXISTS
  FOR (d:Disorder) ON (d.disorderEmbedding) 
  OPTIONS { indexConfig: {
    `vector.dimensions`: 1024,
    `vector.similarity_function`: 'cosine'
  }}""")

    res = con.query("""SHOW VECTOR INDEXES""")
    print(res)
    start = time.time()
    con.query("""
      MATCH (disorder:Disorder)
WITH collect(disorder) as allDisorders
UNWIND range(0, size(allDisorders)-1, 1000) as i
WITH i, allDisorders[i..i+1000] as batchDisorders
WHERE size(batchDisorders) > 0
CALL apoc.ml.openai.embedding(
    [d in batchDisorders | 
        'DisplayName: ' + coalesce(d.displayName, '') + '; Synonyms: ' +
        coalesce( apoc.text.join(d.synonyms,', '), '') + '; Description: ' +
        coalesce(d.description, '')
    ], 
    "whatever", 
    {
        endpoint: '"""+_LLM_BASE+"""',
        path: '"""+_LLM_path+"""',
        model: '"""+_LLM_model+"""',
        enableBackOffRetries: true,
        exponentialBackoff: true
    }
) YIELD index, embedding
WITH batchDisorders[index] as disorder, embedding CALL db.create.setNodeVectorProperty(disorder, "disorderEmbedding", embedding);"""
              )
    duration = time.time() - start
    print(f"Building disorder embedding indexes finished after {duration} seconds")
    res = con.query("""SHOW VECTOR INDEXES""")
    print(res)


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

