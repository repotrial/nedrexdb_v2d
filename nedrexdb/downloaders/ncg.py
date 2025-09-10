import os as _os
from pathlib import Path as _Path

import requests  # type: ignore

from nedrexdb import config as _config
from nedrexdb.common import change_directory as _cd
from nedrexdb.logger import logger


def download_ncg():
    ncg_conf = _config.get("sources.ncg.annotation")
    url = ncg_conf["url"]
    data = {'downloadcancergenes': 'Download'}

    target_fname = ncg_conf["filename"]
    ncg_dir = _Path(_config.get("db.root_directory")) / _config.get("sources.directory") / "ncg"

    ncg_dir.mkdir(exist_ok=True, parents=True)

    with _cd(ncg_dir):
        # NOTE: we have to remove the old file first, otherwise we get a bug where it gets deleted
        #       (because iterdir() will delete it).
        if _os.path.isfile(target_fname):
            _os.remove(target_fname)

        logger.info("Downloading NCG")
        try:
            # Send the request and save response directly to a file
            response = requests.post(url, data=data)
            response.raise_for_status()  # Raise an exception for any HTTP error

            with open(target_fname, 'wb') as f:
                f.write(response.content)
            logger.debug("NCG downloaded successfully.")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Unable to download NCG: {e}")