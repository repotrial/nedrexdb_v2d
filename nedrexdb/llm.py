from nedrexdb import config as _config

_LLM_embeddings = _config["embeddings"]
def _require(d, key, section="embeddings"):
    if key not in d:
        raise KeyError(f"Required key '{key}' missing from [{section}] config section")
    return d[key]

_LLM_BASE=_require(_LLM_embeddings, "server_base")
_LLM_model=_require(_LLM_embeddings, "model")
_LLM_path=_LLM_embeddings.get("path", "embeddings")
_LLM_embedding_length=_LLM_embeddings.get("embedding_length",1024)
_LLM_parallel=_LLM_embeddings.get("parallel", False)
_LLM_openwebui=_LLM_embeddings.get("openwebui", False)

_LLM_API_KEY=_LLM_embeddings.get("api_key", "no-key")
