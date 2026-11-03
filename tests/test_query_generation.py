from nedrexdb.post_integration.neo4j_db_adjustments import (
    get_node_info_string,
    get_edge_info_string,
    create_node_vector_query,
    create_edge_vector_query
)

def test_get_node_info_string():
    config = {
        "Gene": {
            "symbol": {"prefix": "symbol ", "suffix": ""},
            "description": {"prefix": " described as ", "suffix": "."}
        }
    }
    result = get_node_info_string("Gene", config)
    assert "symbol " in result
    assert "described as " in result
    assert "x.primaryDomainId" in result

def test_get_edge_info_string():
    config = {
        "INTERACTS_WITH": {
            "link_term": "interacts with",
            "attributes": {
                "score": {"prefix": " with score ", "suffix": ""},
                "methods": {"prefix": " by methods ", "suffix": "", "type": "list"}
            },
            "source": "Protein",
            "target": "Protein"
        }
    }
    result = get_edge_info_string("INTERACTS_WITH", config)
    assert "interacts with" in result
    assert "entry.s.primaryDomainId" in result
    assert "entry.t.primaryDomainId" in result
    assert "apoc.text.join(entry.r.methods, ', ')" in result

def test_create_node_vector_query():
    info_str = "x.displayName"
    query = create_node_vector_query(info_str, "Gene")
    assert "MATCH (x:Gene) WHERE x.embedding IS NULL" in query
    assert "LIMIT 50000" in query
    assert "MATCH (x:Gene) WHERE id(x) = id" in query
    assert "db.create.setNodeVectorProperty(node, \"embedding\", embedding)" in query

def test_create_edge_vector_query():
    info_str = "entry.s.displayName"
    query = create_edge_vector_query(info_str, "Gene", "GeneAssociatedWithDisorder", "Disorder")
    # Outer query should match directed, label-free relationships of the type
    assert "MATCH ()-[r:GeneAssociatedWithDisorder]->() WHERE r.embedding IS NULL" in query
    assert "LIMIT 50000" in query
    # Inner CALL block match should also be directed
    assert "MATCH (s)-[r:GeneAssociatedWithDisorder]->(t) WHERE id(r) = id" in query
    assert "db.create.setRelationshipVectorProperty(rel, \"embedding\", embedding)" in query


def test_wait_for_database_ready_checks_all_indices():
    from unittest.mock import MagicMock
    from nedrexdb.post_integration.neo4j_db_adjustments import wait_for_database_ready

    con = MagicMock()
    con.query.side_effect = [
        [{"name": "idx1", "state": "ONLINE", "type": "VECTOR", "labelsOrTypes": ["Drug"], "properties": ["embedding"]}],
        [{"name": "idx2", "state": "POPULATING", "type": "VECTOR", "labelsOrTypes": ["Gene"], "properties": ["embedding"]}],
    ]
    assert wait_for_database_ready(con, ["idx1", "idx2"]) is False
    assert con.query.call_count == 2


def test_create_constraints_adds_drug_label_even_when_constraints_disabled(monkeypatch):
    from unittest.mock import MagicMock
    from nedrexdb.post_integration import neo4j_db_adjustments

    mock_kg = MagicMock()
    monkeypatch.setattr(neo4j_db_adjustments, "get_kg_connection", lambda: mock_kg)
    monkeypatch.setattr(neo4j_db_adjustments, "close_kg_connection", lambda: None)
    monkeypatch.setattr(neo4j_db_adjustments._config, "get", lambda k: False if k == "db.set_unique_constraints" else None)

    neo4j_db_adjustments.create_constraints()

    queries = [call.args[0] for call in mock_kg.query.call_args_list]
    assert any("MATCH (n:BiotechDrug) WHERE NOT n:Drug SET n:Drug" in q for q in queries)
    assert any("MATCH (n:SmallMoleculeDrug) WHERE NOT n:Drug SET n:Drug" in q for q in queries)
    assert not any("CREATE CONSTRAINT" in q for q in queries)

