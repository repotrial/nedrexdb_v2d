import base64
import os as _os
from pathlib import Path as _Path

import requests  # type: ignore

from nedrexdb import config as _config
from nedrexdb.common import change_directory as _cd, Downloader
from nedrexdb.logger import logger


def download_cosmic():
    cosmic_conf = _config.get("sources.cosmic.census")

    first_response = requests.get(cosmic_conf["url"], auth=(cosmic_conf["email"], cosmic_conf["password"]))
    first_response.raise_for_status()

    download_url = first_response.json()["url"]

    cosmic_dir = _Path(_config.get("db.root_directory")) / _config.get("sources.directory") / "cosmic"
    cosmic_dir.mkdir(exist_ok=True, parents=True)

    filename = cosmic_conf["filename"]

    d = Downloader(
        url=download_url,
        target=cosmic_dir / filename,
    )
    d.download()