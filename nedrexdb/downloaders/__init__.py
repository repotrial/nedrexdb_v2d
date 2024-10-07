import datetime as _datetime
import shutil as _shutil
import re as _re
import requests
from pathlib import Path as _Path

from nedrexdb import config as _config
from nedrexdb.common import Downloader
from nedrexdb.db import MongoInstance
from nedrexdb.downloaders.biogrid import download_biogrid as _download_biogrid
from nedrexdb.downloaders.chembl import download_chembl as _download_chembl
from nedrexdb.exceptions import (
    ProcessError as _ProcessError,
)


class Version:
    def __init__(self, string):
        self.major, self.minor, self.patch = [int(i) for i in string.split(".")]

    def increment(self, level):
        if level == "major":
            self.major += 1
        elif level == "minor":
            self.minor += 1
        elif level == "patch":
            self.patch += 1

    def __repr__(self):
        return f"{self.major}.{self.minor}.{self.patch}"

def update_version(name, source_url, unique_pattern, mode="date", skip_digits=0):
    response = requests.get(source_url)
    if response.status_code != 200:
        raise _ProcessError(f"got non-zero status code while updating metadata.\n source:{name}\n URL: {source_url}")
    result = _re.findall(unique_pattern, response.text)
    text = str(result[0])
    #version = text.split("_")[1].split(".")[0]     \\ old way to split for version, may be removed
    if mode == "date":
        # create version number from date
        version = "".join(_re.findall(r"\d+", text))
        version = version[skip_digits:]
        version = f"{version[0:4]}-{version[4:6]}-{version[6:]}"
    else:
        version = "".join(_re.findall(r"\d+", text))
        version = version[skip_digits:]
        version = f"{version[0:2]}.{version[2:]}"
    date = _datetime.datetime.now().date()
    print(f"{name}: date: {date}, version: {version}")
    return {"date": f"{date}", "version": version}

def download_all(force=False, ignored_sources=set()):
    base = _Path(_config["db.root_directory"])
    download_dir = base / _config["sources.directory"]

    if force and (download_dir).exists():
        _shutil.rmtree(download_dir)
    download_dir.mkdir(exist_ok=True, parents=True)

    sources = _config["sources"]
    # Remove the source keys (in filter)
    exclude_keys = {"directory", "username", "password", "default_version", "version",
                    "version_url", "version_pattern", "version_mode", "skip_digits"}
    exclude_keys.update(ignored_sources)

    metadata = {"source_databases": {}}

    print(f"ignore sources: {ignored_sources}")

    if "chembl" not in ignored_sources:
        chembl_date = _datetime.datetime.now().date()
        chembl_version = _download_chembl()
        metadata["source_databases"]["chembl"] = {"date": f"{chembl_date}", "version": chembl_version}
    if "biogrid" not in ignored_sources:
        biogrid_date = _datetime.datetime.now().date()
        biogrid_version = _download_biogrid()
        metadata["source_databases"]["biogrid"] = {"date": f"{biogrid_date}", "version": biogrid_version}

    for source in filter(lambda i: i not in exclude_keys, sources):

        # Catch case to skip sources with bespoke downloaders entirely.
        if source in {
            "biogrid",
            "chembl"
        }:
            continue

        # update metadata
        meta = sources[source]
        if "version_url" in meta.keys():
            version_url = meta["version_url"]
            version_pattern = rf"{meta['version_pattern']}"
            skip_digits = meta["skip_digits"] if "skip_digits" in meta.keys() else 0
            version_mode = meta["version_mode"] if "version_mode" in meta.keys() else "date"
            metadata["source_databases"][source] = update_version(name=source,
                                                                  source_url=version_url,
                                                                  unique_pattern=version_pattern,
                                                                  mode=version_mode,
                                                                  skip_digits=skip_digits)
        else:
            date = _datetime.datetime.now().date()
            version = meta["version"] if "version" in meta.keys() else f"{date}"
            metadata["source_databases"][source] = {"date": f"{date}", "version": version}

        # Catch case to skip sources with bespoke downloaders after setting metadata.
        if source in {
            "drugbank",
            "disgenet"
        }:
            continue

        (download_dir / source).mkdir(exist_ok=True)

        data = sources[source]
        username = data.get("username")
        password = data.get("password")

        for _, download in filter(lambda i: i[0] not in exclude_keys, data.items()):
            url = download.get("url")
            filename = download.get("filename")
            if url is None:
                continue
            if filename is None:
                filename = url.rsplit("/", 1)[1]

            d = Downloader(
                url=url,
                target=download_dir / source / filename,
                username=username,
                password=password,
            )
            d.download()

    docs = list(MongoInstance.DB["metadata"].find())
    if len(docs) == 1:
        version = docs[0]["version"]
    elif len(docs) == 0:
        version = sources["default_version"]
    else:
        raise Exception("should only be one document in the metadata collection")

    v = Version(version)
    v.increment("patch")

    metadata["version"] = f"{v}"

    MongoInstance.DB["metadata"].replace_one({}, metadata, upsert=True)
