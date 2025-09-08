import subprocess as _sp
from pathlib import Path as _Path
import shutil as _shutil
import os as _os


from requests.exceptions import HTTPError as _HTTPError


from nedrexdb import config as _config
from nedrexdb.common import Downloader, change_directory
from nedrexdb.logger import logger

def getData(target_dir, url):
    _sp.call(
        (
            "wget",
            "--no-verbose",
            "--read-timeout",
            "10",
            "--recursive",
            "--no-parent",
            "--no-host-directories",
            "--cut-dirs",
            "6",
            "-P",
            f"{target_dir.resolve()}/",
            url,
        )
    )
    

def download_opentargets():
    logger.info("Downloading OpenTargets")

    root = _Path(_config["db.root_directory"]) / _config["sources.directory"]
    target_dir = root / "opentargets"
    target_dir.mkdir(exist_ok=True, parents=True)

    target = target_dir / _config["sources.opentargets"]["gene_disease_associations"]["filename"]
    url = _config["sources.opentargets"]["gene_disease_associations"]["url"]
    url_mapping = _config["sources.opentargets"]["mapping_diseases"]["url"]
    url_associations_summary = _config["sources.opentargets"]["gene_disease_associations_summary"]["url"]
    logger.debug(target_dir.resolve())


    # OpenTargets downloads a directory -> delete old directory first, in case content was changed
    if _os.path.exists(target.resolve()) and _os.path.isdir(target.resolve()):
        _shutil.rmtree(target.resolve())

    # Download (Downloader class does not work, since target is a directory)
    getData(target_dir, url)
    getData(target_dir, url_mapping)
    getData(target_dir, url_associations_summary)
