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
    exclude_keys = ignored_sources.union({"directory", "username", "password"})

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

        # Catch case to skip sources with bespoke downloaders.
        if source in {
            "biogrid",
            "drugbank",
            "chembl",
            "disgenet"
        }:
            continue

        # update metadata
        match source:
            ## omim just date
            case "uniprot":
                ##sources[source]["version_url"]
                url = "https://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/taxonomic_divisions"
                pattern = r">uniprot_sprot_human\.dat\.gz</a>                            [\d-]+"
                metadata["source_databases"][source] = update_version("uniprot", url, pattern)
            case "reactome":
                url = "https://reactome.org/download/current/"
                pattern = r'>UniProt2Reactome_All_Levels\.txt</a></td><td align="right">[\d-]+'
                metadata["source_databases"][source] = update_version("reactome", url, pattern, skip_digits=1)
            case "unichem":
                url = "http://ftp.ebi.ac.uk/pub/databases/chembl/UniChem/data/wholeSourceMapping/src_id2/"
                pattern = r'>src2src22\.txt\.gz</a></td><td align="right">[\d-]+'
                metadata["source_databases"][source] = update_version("unichem", url, pattern, skip_digits=3)
            case "ncbi":
                url = "https://ftp.ncbi.nih.gov/gene/DATA/GENE_INFO/Mammalia/"
                pattern = r">Homo_sapiens\.gene_info\.gz</a>      [\d-]+"
                metadata["source_databases"][source] = update_version("ncbi", url, pattern)
            case "mondo":
                url = "https://github.com/monarch-initiative/mondo/tags"
                pattern = r"/monarch-initiative/mondo/releases/tag/v[\d-]+"
                metadata["source_databases"][source] = update_version("mondo", url, pattern)
            case "intact":
                url = "http://ftp.ebi.ac.uk/pub/databases/intact/current/psimitab/"
                pattern = r'>intact\.zip</a></td><td align="right">[\d-]+'
                metadata["source_databases"][source] = update_version("intact", url, pattern)
            case "iid":
                url = "http://iid.ophid.utoronto.ca/static/Search_By_Proteins.css"
                pattern = r'content: "version [\d-]+'
                metadata["source_databases"][source] = update_version("iid", url, pattern)
            case "hpo":
                url = "https://github.com/obophenotype/human-phenotype-ontology/releases/"
                pattern = r'href="/obophenotype/human-phenotype-ontology/releases/tag/v[\d-]+'
                metadata["source_databases"][source] = update_version("hpo", url, pattern)
            case "hpa":
                url = "https://www.proteinatlas.org/about/download"
                pattern = r"data available in the Human Protein Atlas version \d+\.\d+"
                metadata["source_databases"][source] = update_version("hpa", url, pattern, "serial")
            case "ctd":
                url = "https://ctdbase.org/reports/"
                pattern = r'>CTD_chemicals_diseases\.tsv\.gz</a></td><td align="right">[\d-]+'
                metadata["source_databases"][source] = update_version("ctd", url, pattern)
            case "clinvar":
                # url = sources["clinvar"]["human_data"][1].get("url").rsplit("/", 1)[1]
                # '--> can be used to get the URL from config (instead of hard coding url)
                url = "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_GRCh38/"
                metadata["source_databases"][source] = (
                    update_version("clinvar", url, r'href="clinvar_\d+\.vcf\.error\.txt"'))
            case "go":
                # write it as json interpreter, maybe use just requests?
                url = "https://current.geneontology.org/release_stats/go-stats-summary.json"
                pattern = r'"release_date": "[\d-]+'
                metadata["source_databases"][source] = update_version("go", url, pattern)
            case "uberon":
                #url = "https://github.com/obophenotype/uberon/releases/download/v2022-04-05"
                #version = sources["uberon"]["ext"][1].get("url").rsplit("/", 2)[1]
                #version = version[1:]
                date = _datetime.datetime.now().date()
                version = "2022-04-05"
                metadata["source_databases"][source] = {"date": f"{date}", "version": version}
            case "drug_central":
                #url = "https://unmtid-shinyapps.net/download/drugcentral.dump.11012023.sql.gz"
                #version = sources["drug_central"]["postgres_dump"][1].get("url").rsplit(".", 3)[1]
                #version = f"{version[4:]}-{version[2:4]}-{version[0:2]}"
                date = _datetime.datetime.now().date()
                version = "2023-01-11"
                metadata["source_databases"][source] = {"date": f"{date}", "version": version}
            case "sider":
                metadata["source_databases"][source] = {"date": f"{_datetime.datetime.now().date()}", "version": "4.1"}
            case _:
                metadata["source_databases"][source] = {"date": f"{_datetime.datetime.now().date()}", "version": None}

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
        version = "0.0.0"
    else:
        raise Exception("should only be one document in the metadata collection")

    v = Version(version)
    v.increment("patch")

    metadata["version"] = f"{v}"

    print(1000*"metadata")
    print(metadata)

    MongoInstance.DB["metadata"].replace_one({}, metadata, upsert=True)
