import os as _os
import shutil as _shutil
import subprocess as _subprocess
from pathlib import Path as _Path

import requests  # type: ignore
from bs4 import BeautifulSoup

from nedrexdb import config as _config
from nedrexdb.common import Downloader
from nedrexdb.common import change_directory as _cd


def get_latest_intogen_download() -> str:
    url = _config.get("sources.intogen.drivers.url")
    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, features="lxml")
    download_url = url + soup.select_one("section", class_="download-current").select_one("a[href*=Drivers]")["href"]
    return download_url


def download_intogen():
    url = get_latest_intogen_download()
    zip_fname = url.rsplit("file=", 1)[1]
    zip_dir = _os.path.splitext(zip_fname)[0]
    target_fname = _config.get("sources.intogen.drivers.filename")

    intogen_dir = _Path(_config.get("db.root_directory")) / _config.get("sources.directory") / "intogen"
    intogen_dir.mkdir(exist_ok=True, parents=True)

    d = Downloader(
        url=url,
        target=intogen_dir / zip_fname,
    )
    d.download()
    with _cd(intogen_dir):
        _subprocess.call(
            ["unzip", "-d", zip_dir, zip_fname],
            stdout=_subprocess.DEVNULL,
            stderr=_subprocess.DEVNULL,
        )
        _os.remove(zip_fname)

        for f in _Path(zip_dir).rglob(target_fname):
            _shutil.move(f, target_fname)

        _shutil.rmtree(zip_dir)
        assert _os.path.isfile(intogen_dir / target_fname)