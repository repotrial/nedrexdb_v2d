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

@patch("build.clean_api_data.clean_after_update")
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
    mock_clean_after_update,
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
    mock_clean_after_update.assert_called_once()

@patch("build.clean_api_data.clean_after_update")
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
    mock_clean_after_update,
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
    mock_clean_after_update.assert_called_once()
    
    # Verify that run_parsers was called with a non-empty ignored_sources
    args, kwargs = mock_parsers.call_args
    assert len(kwargs['ignored_sources']) > 0
    assert "go" in kwargs['ignored_sources']

@patch("build.clean_api_data.clean_after_update")
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
    mock_clean_after_update,
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
    mock_clean_after_update.assert_called_once()

@patch("build.clean_api_data.clean_after_update")
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
    mock_clean_after_update,
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
        rebuild=False,
        keep_dev=False,
    )
    # Check if key stages were called on the controller
    controller_instance = mock_embed_controller.return_value
    controller_instance.gather_live_state.assert_called_once()
    controller_instance.prepare_reusable_embeddings.assert_called_once()
    controller_instance.validate_and_finalize.assert_called_once()
    mock_clean_after_update.assert_called_once()

@patch("build.clean_api_data.clean_after_update")
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
def test_update_aborts_clean_when_embeddings_fail(
    mock_subproc, mock_embed_controller, mock_constraints,
    mock_verify, mock_profile, mock_drop, mock_m2n,
    mock_parsers, mock_download, mock_upd_vers,
    mock_upd_img, mock_live_inst, mock_dev_inst, mock_mongo,
    mock_clean_after_update,
    runner, tmp_path
):
    conf_file = tmp_path / "test_config.toml"
    conf_file.write_text("version_type='open'")

    mock_mongo.DB = MagicMock()
    mock_mongo.DB.list_collection_names.return_value = ["metadata"]
    mock_embed_controller.return_value.validate_and_finalize.return_value = False

    with patch.dict(os.environ, {"TEST_MINIMUM": "0"}):
        result = runner.invoke(update, ["--conf", str(conf_file), "--create_embeddings"])

    assert result.exit_code == 0
    mock_live_inst.assert_not_called()
    mock_clean_after_update.assert_not_called()


def test_clean_api_files(tmp_path):
    from nedrexdb.post_integration import clean_api_data

    data_dir = tmp_path / "data"
    static_dir = tmp_path / "static"

    # Populate data subdirs
    for subdir in clean_api_data.DATA_SUBDIRS_TO_CLEAN:
        d = data_dir / subdir
        d.mkdir(parents=True)
        (d / "sample_file.graphml").write_text("dummy")
        nested = d / "uid_subdir"
        nested.mkdir()
        (nested / "inner.txt").write_text("inner")

    # Populate static subdirs and static files
    for subdir in clean_api_data.STATIC_SUBDIRS_TO_CLEAN:
        d = static_dir / subdir
        d.mkdir(parents=True)
        (d / "PPDr-for-ranking.graphml").write_text("dummy")

    for fname in clean_api_data.STATIC_FILES_TO_CLEAN:
        (static_dir / fname).write_text("gt_data")

    # Non-derived static file should be preserved
    preserved_static = static_dir / "lengths.map"
    preserved_static.write_text("keep_me")

    clean_api_data.clean_api_files(data_dir=data_dir, static_dir=static_dir)

    for subdir in clean_api_data.DATA_SUBDIRS_TO_CLEAN:
        d = data_dir / subdir
        assert d.exists()
        assert list(d.iterdir()) == []

    for subdir in clean_api_data.STATIC_SUBDIRS_TO_CLEAN:
        d = static_dir / subdir
        assert d.exists()
        assert list(d.iterdir()) == []

    for fname in clean_api_data.STATIC_FILES_TO_CLEAN:
        assert not (static_dir / fname).exists()

    assert preserved_static.exists()


def test_clean_api_files_skips_when_dirs_unconfigured(monkeypatch):
    from nedrexdb.post_integration import clean_api_data

    monkeypatch.setattr(clean_api_data._config, "get", lambda k: None)
    clean_api_data.clean_api_files()  # must not raise


def test_clean_api_db(monkeypatch):
    from nedrexdb.post_integration import clean_api_data

    mock_client = MagicMock()
    mock_db = MagicMock()
    collections = {
        "graphs_": MagicMock(),
        "bicon_": MagicMock(),
        "api_keys_": MagicMock(),
    }
    mock_db.list_collection_names.return_value = list(collections.keys())
    mock_db.__getitem__.side_effect = collections.__getitem__
    mock_client.__getitem__.return_value = mock_db

    monkeypatch.setattr(clean_api_data, "MongoClient", lambda **kwargs: mock_client)
    monkeypatch.setattr(
        clean_api_data._config,
        "get",
        lambda k: "open_nedrex_live" if k == "db.live.mongo_name" else None,
    )

    clean_api_data.clean_api_db()

    collections["graphs_"].drop.assert_called_once()
    collections["bicon_"].drop.assert_called_once()
    collections["api_keys_"].drop.assert_not_called()


_REDIS_CFG = {
    "api.redis_host": "open-nedrex-redis",
    "api.redis_port_internal": 6379,
    "api.redis_nedrex_db": 1,
}


def test_reset_api_static_status_deletes_key(monkeypatch):
    import sys
    from nedrexdb.post_integration import clean_api_data

    mock_redis_module = MagicMock()
    monkeypatch.setitem(sys.modules, "redis", mock_redis_module)
    monkeypatch.setattr(clean_api_data._config, "get", _REDIS_CFG.get)

    clean_api_data.reset_api_static_status()

    kwargs = mock_redis_module.Redis.call_args.kwargs
    assert (kwargs["host"], kwargs["port"], kwargs["db"]) == ("open-nedrex-redis", 6379, 1)
    mock_redis_module.Redis.return_value.delete.assert_called_once_with("static-file-status")


def test_reset_api_static_status_survives_redis_failure(monkeypatch):
    import sys
    from nedrexdb.post_integration import clean_api_data

    mock_redis_module = MagicMock()
    mock_redis_module.Redis.return_value.delete.side_effect = ConnectionError("down")
    monkeypatch.setitem(sys.modules, "redis", mock_redis_module)
    monkeypatch.setattr(clean_api_data._config, "get", _REDIS_CFG.get)

    clean_api_data.reset_api_static_status()  # must not raise

    # Unconfigured Redis is skipped without connecting
    mock_redis_module.Redis.reset_mock()
    monkeypatch.setattr(clean_api_data._config, "get", lambda k: None)
    clean_api_data.reset_api_static_status()
    mock_redis_module.Redis.assert_not_called()


def test_clean_after_update_runs_all_steps(monkeypatch):
    from nedrexdb.post_integration import clean_api_data

    calls = []
    monkeypatch.setattr(clean_api_data, "clean_api_files", lambda **kw: calls.append("files"))
    monkeypatch.setattr(clean_api_data, "reset_api_static_status", lambda: calls.append("redis"))
    monkeypatch.setattr(clean_api_data, "clean_api_db", lambda: calls.append("db"))

    clean_api_data.clean_after_update()

    assert calls == ["files", "redis", "db"]


@pytest.mark.parametrize("finalize_result, expect_clean", [(None, True), (False, False)])
@patch("build.clean_api_data.clean_after_update")
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
def test_update_keep_dev_cleans_only_when_promoted(
    mock_subproc, mock_embed_controller, mock_constraints,
    mock_verify, mock_profile, mock_drop, mock_m2n,
    mock_parsers, mock_download, mock_upd_vers,
    mock_upd_img, mock_live_inst, mock_dev_inst, mock_mongo,
    mock_clean_after_update,
    finalize_result, expect_clean,
    runner, tmp_path
):
    conf_file = tmp_path / "test_config.toml"
    conf_file.write_text("version_type='open'")

    mock_mongo.DB = MagicMock()
    mock_mongo.DB.list_collection_names.return_value = ["metadata"]
    mock_embed_controller.return_value.validate_and_finalize.return_value = finalize_result

    with patch.dict(os.environ, {"TEST_MINIMUM": "0"}):
        result = runner.invoke(update, ["--conf", str(conf_file), "--create_embeddings", "--keep-dev"])

    assert result.exit_code == 0
    assert mock_clean_after_update.called is expect_clean

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


@pytest.mark.parametrize("fail", [False, True])
@patch("build.time.sleep")
@patch("build.set_kg_target")
@patch("build.create_vector_indices")
@patch("build.create_constraints")
@patch("build.NeDRexLiveInstance")
@patch("build.nedrexdb.parse_config")
def test_embed_only_targets_live_and_always_restores_it(
    mock_parse, mock_live_inst, mock_constraints, mock_vectors, mock_target, mock_sleep,
    fail, runner, tmp_path
):
    conf_file = tmp_path / "test_config.toml"
    conf_file.write_text("version_type='open'")
    if fail:
        mock_constraints.side_effect = RuntimeError("Could not connect to Neo4j")

    from build import embed_only
    result = runner.invoke(embed_only, ["--conf", str(conf_file)])

    assert (result.exit_code != 0) is fail
    # Embedding work runs against the live instance, not dev
    assert mock_target.call_args_list[0].args == ("live",)
    assert mock_target.call_args_list[-1].args == ("dev",)
    # Live is always brought back read-only (which also restarts its MongoDB)
    set_up_calls = mock_live_inst.return_value.set_up.call_args_list
    assert set_up_calls[0].kwargs == {"use_existing_volume": True, "neo4j_mode": "db-write"}
    assert set_up_calls[-1].kwargs == {"use_existing_volume": True, "neo4j_mode": "db"}


def test_kg_target_selects_neo4j_host(monkeypatch):
    from nedrexdb.post_integration import neo4j_db_adjustments as adj

    names = {"db.dev.neo4j_name": "open_nedrex_dev_neo4j", "db.live.neo4j_name": "open_nedrex_live_neo4j"}
    monkeypatch.setattr(adj, "_config", names)
    try:
        assert adj._neo4j_host() == "open_nedrex_dev_neo4j"
        adj.set_kg_target("live")
        assert adj._neo4j_host() == "open_nedrex_live_neo4j"
        with pytest.raises(ValueError):
            adj.set_kg_target("prod")
    finally:
        adj.set_kg_target("dev")
