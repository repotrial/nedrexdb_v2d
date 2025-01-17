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
    create_drug_embeddings(kg)
    create_gene_embeddings(kg)
    create_disease_gene_embeddings(kg)
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
        'coalesce(d.type, '') +  ' with ID ' + d.primaryDomainId +
        ': DisplayName: ' + coalesce(d.displayName, '') + '; Synonyms: ' +
        coalesce( apoc.text.join(d.synonyms,', '), '') + '; Description: ' +
        coalesce(d.description, '')
    ], 
    "whatever", 
    {
        endpoint: '""" + _LLM_BASE + """',
        path: '""" + _LLM_path + """',
        model: '""" + _LLM_model + """',
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


def create_gene_embeddings(con):
    from nedrexdb.llm import (_LLM_BASE, _LLM_path, _LLM_model)
    con.query("""CREATE VECTOR INDEX gene_embeddings IF NOT EXISTS
  FOR (d:Gene) ON (d.geneEmbedding) 
  OPTIONS { indexConfig: {
    `vector.dimensions`: 1024,
    `vector.similarity_function`: 'cosine'
  }}""")

    res = con.query("""SHOW VECTOR INDEXES""")
    print(res)
    start = time.time()
    con.query("""
      MATCH (gene:Gene)
WITH collect(gene) as allGenes
UNWIND range(0, size(allGenes)-1, 1000) as i
WITH i, allGenes[i..i+1000] as batchGenes
WHERE size(batchGenes) > 0
CALL apoc.ml.openai.embedding(
    [d in batchGenes | 
        coalesce(d.type, '') +' with ID ' + d.primaryDomainId +
        ': DisplayName: ' + coalesce(d.displayName, '') + 
        '; Approved Symbol: ' + coalesce(d.approvedSymbol, '')+
        '; Description: ' + coalesce(d.description, '')+
        '; Gene Type: ' + coalesce(d.geneType, '')+
        '; Synonyms: ' + coalesce( apoc.text.join(d.synonyms, ', '), '')+
        '; Other symbols: ' + coalesce( apoc.text.join(d.symbols, ', '), '')+
        '; Data Sources: ' + coalesce( apoc.text.join( d.dataSources,', '), '')
    ], 
    "whatever", 
    {
        endpoint: '""" + _LLM_BASE + """',
        path: '""" + _LLM_path + """',
        model: '""" + _LLM_model + """',
        enableBackOffRetries: true,
        exponentialBackoff: true
    }
) YIELD index, embedding
WITH batchGenes[index] as gene, embedding CALL db.create.setNodeVectorProperty(gene, "geneEmbedding", embedding);"""
              )
    duration = time.time() - start
    print(f"Building drug embedding indexes finished after {duration} seconds")
    res = con.query("""SHOW VECTOR INDEXES""")
    print(res)


def create_disease_gene_embeddings(con):
    from nedrexdb.llm import (_LLM_BASE, _LLM_path, _LLM_model)
    con.query("""CREATE VECTOR INDEX disease_gene_embeddings IF NOT EXISTS
  FOR (r:GeneAssociatedWithDisorder) ON (r.geneDiseaseEmbedding) 
  OPTIONS { indexConfig: {
    `vector.dimensions`: 1024,
    `vector.similarity_function`: 'cosine'
  }}""")

    res = con.query("""SHOW VECTOR INDEXES""")
    print(res)
    start = time.time()
    con.query("""
      MATCH (g:Gene)-[r:GeneAssociatedWithDisorder]-(d:Disorder) 
WITH collect({g:g,r:r,d:d}) as allEntries
UNWIND range(0, size(allEntries)-1, 1000) as i
WITH i, allEntries[i..i+1000] as batchEntries
WHERE size(batchEntries) > 0
CALL apoc.ml.openai.embedding(
    [entry in batchEntries | 
        coalesce(entry.g.type, '') +' '+ coalesce(entry.g.displayName, '') +' with ID '+ entry.g.primaryDomainId + ' is associated with '+ coalesce(entry.d.type, '') +' '+coalesce(entry.d.displayName, '')+'  with ID '+ entry.d.primaryDomainId +
        '; Data Sources: ' + coalesce( apoc.text.join( entry.r.dataSources,', '), '')
    ], 
    "whatever", 
    {
        endpoint: '""" + _LLM_BASE + """',
        path: '""" + _LLM_path + """',
        model: '""" + _LLM_model + """',
        enableBackOffRetries: true,
        exponentialBackoff: true
    }
) YIELD index, embedding
WITH batchEntries[index] as entry, embedding CALL db.create.setRelationshipVectorProperty(entry.r, "geneDiseaseEmbedding", embedding);"""
              )
    duration = time.time() - start
    print(f"Building disease-gene embedding indexes finished after {duration} seconds")
    res = con.query("""SHOW VECTOR INDEXES""")
    print(res)


def create_drug_embeddings(con):
    from nedrexdb.llm import (_LLM_BASE, _LLM_path, _LLM_model)
    con.query("""CREATE VECTOR INDEX drug_embeddings IF NOT EXISTS
  FOR (d:Drug) ON (d.drugEmbedding) 
  OPTIONS { indexConfig: {
    `vector.dimensions`: 1024,
    `vector.similarity_function`: 'cosine'
  }}""")

    res = con.query("""SHOW VECTOR INDEXES""")
    print(res)
    start = time.time()
    con.query("""
      MATCH (drug:Drug)
WITH collect(drug) as allDrugs
UNWIND range(0, size(allDrugs)-1, 1000) as i
WITH i, allDrugs[i..i+1000] as batchDrugs
WHERE size(batchDrugs) > 0
CALL apoc.ml.openai.embedding(
    [d in batchDrugs | 
        coalesce(d.type, '') + ' with ID ' + d.primaryDomainId +
        ': DisplayName: ' + coalesce(d.displayName, '') + '; Data Sources: ' +
        coalesce( apoc.text.join(d.dataSources,', '), '')
    ], 
    "whatever", 
    {
        endpoint: '""" + _LLM_BASE + """',
        path: '""" + _LLM_path + """',
        model: '""" + _LLM_model + """',
        enableBackOffRetries: true,
        exponentialBackoff: true
    }
) YIELD index, embedding
WITH batchDrugs[index] as drug, embedding CALL db.create.setNodeVectorProperty(drug, "drugEmbedding", embedding);"""
              )
    duration = time.time() - start
    print(f"Building drug embedding indexes finished after {duration} seconds")
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
