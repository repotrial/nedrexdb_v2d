import os
import subprocess as _sp
import zipfile as _zipfile
from pathlib import Path as _Path
import shutil as _shutil

from requests.exceptions import HTTPError as _HTTPError

from nedrexdb import config as _config
from nedrexdb.common import Downloader, change_directory
from nedrexdb.logger import logger


def download_orphanet():
    root = _Path(_config["db.root_directory"]) / _config["sources.directory"]
    target_dir = root / "orphanet"
    target_dir.mkdir(exist_ok=True, parents=True)

    # FIRST, download the mapping (zip file)
    orphanet = _config["sources.orphanet"]
    orphanet_mapping = orphanet["mapping"]

    url_mapping = orphanet_mapping["url"]
    zip_fname = target_dir / "Orphanet_Nomenclature_Pack_EN.zip"
    unzip_fname = target_dir / "Orphanet_Nomenclature_Pack_EN"
    target_mapping_fname = (unzip_fname / orphanet_mapping["filename"]).resolve()

    d = Downloader(
        url=url_mapping,
        target=zip_fname,
        username=None,
        password=None,
    )

    try:
        d.download()
    except _HTTPError as E:
        logger.warning(f"Unable to download Orphanet mapping: {E}")
        return

    if not _zipfile.is_zipfile(zip_fname):
        logger.warning(
            f"Orphanet mapping download from {url_mapping!r} did not produce a valid zip file "
            f"(server may have returned an error page or the URL has changed). Skipping."
        )
        zip_fname.unlink(missing_ok=True)
        return

    # Unzip the zip
    with change_directory(target_dir):
        call = ["unzip"]
        if os.environ["LOG_LEVEL"] != "DEBUG":
            call.append("-q")
        call.append(f"{zip_fname.resolve()}")
        result = _sp.call(call)
        zip_fname.unlink(missing_ok=True)

    if result != 0:
        logger.warning(f"unzip returned exit code {result} for Orphanet mapping. Skipping.")
        _shutil.rmtree(unzip_fname, ignore_errors=True)
        return

    # Move the target file from the unzipped directory to the desired target directory
    file = unzip_fname / orphanet_mapping["filename"]
    if not file.exists():
        logger.warning(f"Expected file {file} not found after unzipping Orphanet mapping. Skipping.")
        _shutil.rmtree(unzip_fname, ignore_errors=True)
        return

    target_file_path = target_dir / orphanet_mapping["filename"]
    file.rename(target_file_path)

    # Delete the unzipped directory
    _shutil.rmtree(unzip_fname)

    # SECOND, download the data
    orphanet = _config["sources.orphanet"]
    orphanet_data = orphanet["data"]

    url_data = orphanet_data["url"]
    # zip_fname = target_dir / "all.zip"
    target_fname = (target_dir / orphanet_data["filename"]).resolve()

    d = Downloader(
        url=url_data,
        target=target_fname,
        username=None,
        password=None,
    )
    try:
        d.download()
    except _HTTPError as E:
        logger.warning(f"Unable to download Orphanet data: {E}")
        return
