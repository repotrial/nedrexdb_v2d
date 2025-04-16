from nedrexdb import config as _config

_LLM_BASE=_config["embeddings.server_base"]
_LLM_model=_config[f"embeddings.model"]
_LLM_path=_config[f"embeddings.path"]

_LLM_API_KEY=_config[f"embeddings.api_key"]
if _LLM_API_KEY is None:
    _LLM_API_KEY="no-key"
elif _LLM_API_KEY == "":
    _LLM_API_KEY="no-key"
