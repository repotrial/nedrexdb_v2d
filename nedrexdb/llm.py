from nedrexdb import config as _config

_LLM_BASE=_config["embeddings.server_base"]
_LLM_model=_config[f"embeddings.model"]
_LLM_path=_config[f"embeddings.path"]

_LLM_API_KEY=_config[f"embeddings"].get("api_key", "")
