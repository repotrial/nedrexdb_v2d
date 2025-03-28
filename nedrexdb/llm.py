from nedrexdb import config as _config

_LLM_BASE=_config["embeddings.server_base"]
_LLM_model=_config[f"embeddings.model"]
_LLM_path=_config[f"embeddings.path"]

_LLM_user=_config[f"embeddings.user"]
_LLM_pass=_config[f"embeddings.pass"]
