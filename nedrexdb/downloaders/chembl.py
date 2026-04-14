import re as _re
from pathlib import Path as _Path
from urllib.request import urlretrieve as _urlretrieve

import requests
import time

from nedrexdb import config as _config
from nedrexdb.common import change_directory as _cd
from nedrexdb.exceptions import (
    ProcessError as _ProcessError,
)
from nedrexdb.logger import logger

version_cache = None

def get_latest_chembl_version() -> str:

    global version_cache
    if not version_cache:
        # correct source urls to match latest version names
        url = _config["sources.chembl.version_url"]
        response = requests.get(url)
        if response.status_code != 200:
            raise _ProcessError("got non-zero status code while scraping ChEMBL to get latest version")
        pattern = _config["sources.chembl.version_pattern"]
        result = _re.findall(pattern, response.text)
        text = str(result[0])
        version = text.split("_")[1]
        version_cache = version
    else:
        version = version_cache
    return version


def download_chembl():
    version = get_latest_chembl_version()

    url = _config["sources.chembl.sqlite.url"].format(version)
    logger.info(f"Downloading ChEMBL v{version} from {url}")

    zip_fname = url.rsplit("/", 1)[1]
    chembl_dir = _Path(_config.get("db.root_directory")) / _config.get("sources.directory") / "chembl"
    unichem_url = _config.get("sources.chembl.unichem")["url"]
    unichem_name = unichem_url.rsplit("/", 1)[1]

    chembl_dir.mkdir(exist_ok=True, parents=True)

    def download_with_retry(url, fname, retries=3):
        for attempt in range(retries):
            try:
                _urlretrieve(url, fname)
                return
            except Exception as e:
                logger.warning(f"Chembl Download failed for {url} (attempt {attempt+1}/{retries}): {e}")
                if attempt < retries - 1:
                    time.sleep(5 * (attempt + 1))
        raise RuntimeError(f"Chembl Download failed after {retries} retries: {url}")

    with _cd(chembl_dir):
        download_with_retry(url, zip_fname)
        download_with_retry(unichem_url, unichem_name)
    return version