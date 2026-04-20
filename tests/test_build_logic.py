import os
import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
import nedrexdb
import build
from build import update

@pytest.fixture
def runner():
    return CliRunner()

class MockConfig:
    def __init__(self, data):
        self.data_dict = data
        self.data = data # This is the crucial part for nedrexdb's check

    def __getitem__(self, k):
        # Handle the split_path logic in nedrexdb/__init__.py
        split_path = k.split(".")
        current = self.data_dict
        for idx, val in enumerate(split_path):
            if isinstance(current, dict):
                current = current.get(val)
            else:
                current = None
            if current is None:
                # Fallback for exact matches if nested fails
                if k in self.data_dict:
                    return self.data_dict[k]
                raise nedrexdb.exceptions.ConfigError(f"'{k}' is not in config")
        return current

    def get(self, k):
        try:
            return self[k]
        except:
            return None

    def from_file(self, f):
        pass

@pytest.fixture(autouse=True)
def mock_nedrex_config(monkeypatch):
    config_data = {
        "db": {"version": "open", "mongo_db": "nedrex", "neo4j_image": "neo4j:latest"},
        "embeddings": {"embedding_dependencies": ["drug"]},
        "sources": {"directory": "downloads"},
        "api": {
            "node_collections": ["protein"],
            "edge_collections": ["protein_interacts_with_protein"],
            "mode": "open"
        },
        "db.version": "open",
        "db.open.container_name": "open_nedrex",
        "db.open.mongo_port": 27017,
        "db.open.mongo_name": "open_mongo",
        "db.open.neo4j_http_port": 7474,
        "db.open.neo4j_bolt_port": 7687,
        "db.open.neo4j_memory_max": "4G"
    }
    mock_cfg = MockConfig(config_data)
    # Monkeypatch the config in the build module directly
    monkeypatch.setattr(build, "config", mock_cfg)
    # Also patch in nedrexdb just in case other modules use it
    monkeypatch.setattr(nedrexdb, "config", mock_cfg)
    monkeypatch.setattr(nedrexdb, "mconfig", mock_cfg)
    return mock_cfg

@patch("build.MongoInstance")
@patch("build.NeDRexDevInstance")
@patch("build.NeDRexLiveInstance")
@patch("build.update_neo4j_image_version")
@patch("build.update_versions")
@patch("build.downloaders.download_all")
@patch("build.run_parsers")
@patch("build.mongo_to_neo.mongo_to_neo")
@patch("build.drop_empty_collections.drop_empty_collections")
@patch("build.collection_stats.profile_collections")
@patch("build.collection_stats.verify_collections_after_profiling")
@patch("build.create_constraints")
@patch("build.EmbeddingController")
@patch("subprocess.run")
def test_update_full_flow(
    mock_subproc, mock_embed_controller, mock_constraints, 
    mock_verify, mock_profile, mock_drop, mock_m2n, 
    mock_parsers, mock_download, mock_upd_vers, 
    mock_upd_img, mock_live_inst, mock_dev_inst, mock_mongo,
    runner, tmp_path
):
    # Setup
    conf_file = tmp_path / "test_config.toml"
    conf_file.write_text("version_type='open'")
    
    mock_upd_vers.return_value = {
        "version": "0.3.1",
        "source_databases": {"chembl": {"version": "1", "date": "today"}}
    }
    
    # Mock Mongo live metadata
    mock_mongo.DB = MagicMock()
    mock_mongo.DB.list_collection_names.return_value = ["metadata"]
    mock_mongo.DB["metadata"].find.return_value = [{"source_databases": {}}]
    
    # Run with TEST_MINIMUM=0 (Full Build)
    with patch.dict(os.environ, {"TEST_MINIMUM": "0", "LOG_LEVEL": "INFO"}):
        result = runner.invoke(update, ["--conf", str(conf_file), "--download"])
        
    if result.exit_code != 0:
        print(result.output)
        if result.exception:
            import traceback
            traceback.print_exception(type(result.exception), result.exception, result.exception.__traceback__)
            
    assert result.exit_code == 0
    mock_upd_img.assert_called_once()
    mock_upd_vers.assert_called_once()
    mock_download.assert_called_once()
    mock_parsers.assert_called_once()
    mock_m2n.assert_called_once()

@patch("build.MongoInstance")
@patch("build.NeDRexDevInstance")
@patch("build.NeDRexLiveInstance")
@patch("build.update_neo4j_image_version")
@patch("build.update_versions")
@patch("build.downloaders.download_all")
@patch("build.run_parsers")
@patch("build.mongo_to_neo.mongo_to_neo")
@patch("build.drop_empty_collections.drop_empty_collections")
@patch("build.collection_stats.profile_collections")
@patch("build.collection_stats.verify_collections_after_profiling")
@patch("build.create_constraints")
@patch("build.EmbeddingController")
@patch("subprocess.run")
def test_update_minimal_flow(
    mock_subproc, mock_embed_controller, mock_constraints, 
    mock_verify, mock_profile, mock_drop, mock_m2n, 
    mock_parsers, mock_download, mock_upd_vers, 
    mock_upd_img, mock_live_inst, mock_dev_inst, mock_mongo,
    runner, tmp_path, monkeypatch, mock_nedrex_config
):
    conf_file = tmp_path / "test_config.toml"
    conf_file.write_text("version_type='open'")
    
    mock_upd_vers.return_value = {
        "version": "0.3.1",
        "source_databases": {"chembl": {"version": "1", "date": "today"}}
    }
    
    # Mock Mongo
    mock_mongo.DB = MagicMock()
    mock_mongo.DB.list_collection_names.return_value = ["metadata"]
    mock_mongo.DB["metadata"].find.return_value = [{"source_databases": {}}]
    
    # Properly mock MongoInstance in the module where it's used
    monkeypatch.setattr("nedrexdb.post_integration.drop_empty_collections.MongoInstance", mock_mongo)
    monkeypatch.setattr("nedrexdb.db.collection_stats._config", mock_nedrex_config)
    monkeypatch.setattr("nedrexdb.db.mongo_to_neo.logger", MagicMock()) # just to be safe

    with patch.dict(os.environ, {"TEST_MINIMUM": "1"}):
        result = runner.invoke(update, ["--conf", str(conf_file), "--download"])
        
    if result.exit_code != 0:
        print(result.output)
        if result.exception:
            import traceback
            traceback.print_exception(type(result.exception), result.exception, result.exception.__traceback__)
        
    assert result.exit_code == 0
    mock_upd_img.assert_called_once()
    mock_m2n.assert_called_once()
    
    # Verify that run_parsers was called with a non-empty ignored_sources
    args, kwargs = mock_parsers.call_args
    assert len(kwargs['ignored_sources']) > 0
    assert "go" in kwargs['ignored_sources']

@patch("build.MongoInstance")
@patch("build.NeDRexDevInstance")
@patch("build.NeDRexLiveInstance")
@patch("build.update_neo4j_image_version")
@patch("build.update_versions")
@patch("build.downloaders.download_all")
@patch("build.run_parsers")
@patch("build.mongo_to_neo.mongo_to_neo")
@patch("build.drop_empty_collections.drop_empty_collections")
@patch("build.collection_stats.profile_collections")
@patch("build.collection_stats.verify_collections_after_profiling")
@patch("build.create_constraints")
@patch("build.EmbeddingController")
@patch("subprocess.run")
def test_update_rebuild_flow(
    mock_subproc, mock_embed_controller, mock_constraints, 
    mock_verify, mock_profile, mock_drop, mock_m2n, 
    mock_parsers, mock_download, mock_upd_vers, 
    mock_upd_img, mock_live_inst, mock_dev_inst, mock_mongo,
    runner, tmp_path
):
    conf_file = tmp_path / "test_config.toml"
    conf_file.write_text("version_type='open'")
    
    mock_upd_vers.return_value = {
        "version": "0.3.1",
        "source_databases": {"chembl": {"version": "1", "date": "today"}}
    }
    
    # Mock Mongo live metadata
    mock_mongo.DB = MagicMock()
    mock_mongo.DB.list_collection_names.return_value = ["metadata"]
    mock_mongo.DB["metadata"].find.return_value = [{"source_databases": {"chembl": {"version": "1"}}}]
    
    with patch.dict(os.environ, {"TEST_MINIMUM": "0"}):
        result = runner.invoke(update, ["--conf", str(conf_file), "--rebuild"])
        
    assert result.exit_code == 0
    # In rebuild, no_download should be empty even if versions match
    # We can check if setup_data.sh was called (it is called if static_download is not empty)
    # bioontology, drugbank, disgenet, repotrial, hippie, sider, cosmic, intogen, ncg
    # Since they are not in no_download (because rebuild=True), static_download will have them.
    mock_subproc.assert_called_with(["./setup_data.sh", "/data/nedrex_files", "1"])
    mock_download.assert_called_once()

@patch("build.MongoInstance")
@patch("build.NeDRexDevInstance")
@patch("build.NeDRexLiveInstance")
@patch("build.update_neo4j_image_version")
@patch("build.update_versions")
@patch("build.downloaders.download_all")
@patch("build.run_parsers")
@patch("build.mongo_to_neo.mongo_to_neo")
@patch("build.drop_empty_collections.drop_empty_collections")
@patch("build.collection_stats.profile_collections")
@patch("build.collection_stats.verify_collections_after_profiling")
@patch("build.create_constraints")
@patch("build.EmbeddingController")
@patch("subprocess.run")
def test_update_create_embeddings_flow(
    mock_subproc, mock_embed_controller, mock_constraints, 
    mock_verify, mock_profile, mock_drop, mock_m2n, 
    mock_parsers, mock_download, mock_upd_vers, 
    mock_upd_img, mock_live_inst, mock_dev_inst, mock_mongo,
    runner, tmp_path
):
    conf_file = tmp_path / "test_config.toml"
    conf_file.write_text("version_type='open'")
    
    # mock_embed_controller.return_value = ({}, set()) # No longer returns this directly
    mock_mongo.DB = MagicMock()
    mock_mongo.DB.list_collection_names.return_value = ["metadata", "drug"]
    mock_mongo.DB["drug"].distinct.return_value = ["DrugBank"]
    
    with patch.dict(os.environ, {"TEST_MINIMUM": "0"}):
        result = runner.invoke(update, ["--conf", str(conf_file), "--create_embeddings"])
        
    assert result.exit_code == 0
    # Check if controller was initialized correctly
    mock_embed_controller.assert_called_once_with(
        dev_instance=mock_dev_inst.return_value,
        create_embeddings=True,
        rebuild=False
    )
    # Check if key stages were called on the controller
    controller_instance = mock_embed_controller.return_value
    controller_instance.gather_live_state.assert_called_once()
    controller_instance.prepare_reusable_embeddings.assert_called_once()
    controller_instance.validate_and_finalize.assert_called_once()

@patch("build.NeDRexLiveInstance")
@patch("build.nedrexdb.parse_config")
def test_restart_live(mock_parse, mock_live_inst, runner, tmp_path):
    conf_file = tmp_path / "test_config.toml"
    conf_file.write_text("version_type='open'")
    
    from build import restart_live
    result = runner.invoke(restart_live, ["--conf", str(conf_file)])
    
    assert result.exit_code == 0
    mock_live_inst.return_value.remove.assert_called_once()
    mock_live_inst.return_value.set_up.assert_called_once_with(use_existing_volume=True, neo4j_mode="db")
