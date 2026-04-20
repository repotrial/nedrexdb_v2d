import pytest
from nedrexdb.post_integration.neo4j_db_adjustments import get_node_info_string, get_edge_info_string

def test_get_node_info_string():
    config = {
        "Gene": {
            "symbol": {"prefix": "symbol ", "suffix": ""},
            "description": {"prefix": " described as ", "suffix": "."}
        }
    }
    result = get_node_info_string("Gene", config)
    # Expected: "coalesce(x.type, '') + ' with ID ' + x.primaryDomainId + ':' + 'symbol ' + coalesce(x.symbol, '') + '' + ' described as ' + coalesce(x.description, '') + '.'"
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
