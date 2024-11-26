#!/usr/bin/env python

import time

import click
import os

import nedrexdb
from nedrexdb import config, downloaders
from nedrexdb.control.docker import NeDRexDevInstance, NeDRexLiveInstance
from nedrexdb.db import MongoInstance, mongo_to_neo, collection_stats
from nedrexdb.db.parsers import (
    biogrid,
    disgenet,
    ctd,
    drugbank,
    drug_central,
    hpo,
    hpa,
    iid,
    intact,
    uniprot,
    uniprot_signatures,
    ncbi,
    mondo,
    omim,
    reactome,
    go,
    clinvar,
    chembl,
    unichem,
    bioontology,
    sider,
    uberon,
    repotrial,
)
from nedrexdb.downloaders import get_and_update_versions
from nedrexdb.post_integration import trim_uberon, drop_empty_collections


@click.group()
def cli():
    pass


@click.option("--conf", required=True, type=click.Path(exists=True))
@click.option("--download", is_flag=True, default=False)
@click.option("--version_update", is_flag=True, default=False)
@cli.command()
def update(conf, download, version_update):
    print(f"Config file: {conf}")
    print(f"Download updates: {download}")
    print(f"Update DB versions: {version_update}")

    nedrexdb.parse_config(conf)

    version = config["db.version"]

    if version not in ["open", "licensed"]:
        raise Exception(f"invalid version {version!r}")

    version_update_skip = set()

    dev_instance = NeDRexDevInstance()
    dev_instance.remove()
    dev_instance.set_up(use_existing_volume=False, neo4j_mode="import")
    MongoInstance.connect("dev")
    MongoInstance.set_indexes()

    if os.environ.get("TEST_MINIMUM", 0) == '1':
        parse_dev(version=version, download=download, version_update=version_update)
    else:
        if download:
            downloaders.download_all()

        # Parse sources contributing only nodes (and edges amongst those nodes)
        go.parse_go()
        mondo.parse_mondo_json()
        ncbi.parse_gene_info()
        uberon.parse()
        uniprot.parse_proteins()

        # Sources that add node type but require existing nodes, too
        clinvar.parse()

        if version == "licensed":
            drugbank._parse_drugbank()  # requires proteins to be parsed first
        elif version == "open":
            drugbank.parse_drugbank()
            chembl.parse_chembl()
        uniprot_signatures.parse()  # requires proteins to be parsed first
        hpo.parse()  # requires disorders to be parsed first
        reactome.parse()  # requires protein to be parsed first
        bioontology.parse()  # requires phenotype to be parsed

        # Sources that add data to existing nodes
        drug_central.parse_drug_central()
        unichem.parse()
        repotrial.parse()

        # Sources adding edges.
        biogrid.parse_ppis()
        ctd.parse()
        disgenet.parse_gene_disease_associations()
        go.parse_goa()
        hpa.parse_hpa()
        iid.parse_ppis()
        intact.parse()

        if version == "licensed":
            omim.parse_gene_disease_associations()
            version_update_skip.add("omim")

        sider.parse()
        uniprot.parse_idmap()

        from nedrexdb.analyses import molecule_similarity
        molecule_similarity.run()

        # Post-processing
        trim_uberon.trim_uberon()
        if download or version_update:
            get_and_update_versions(version_update_skip)

    # clean up for export
    drop_empty_collections.drop_empty_collections()

    # export to Neo4j
    mongo_to_neo.mongo_to_neo(dev_instance, MongoInstance.DB)

    # Profile the collections
    collection_stats.profile_collections(MongoInstance.DB)

    # remove dev instance and set up live instance
    dev_instance.remove()
    live_instance = NeDRexLiveInstance()
    live_instance.remove()
    live_instance.set_up(use_existing_volume=True, neo4j_mode="db")

def parse_dev(version, download, version_update):
    # control source downloads
    ignored_sources = {"chembl",
                       "biogrid",
                       "go",
                       "uberon",
                       "clinvar",
                       "uniprot",
                       "hpo",
                       "hpa",
                       "reactome",
                       "bioontology",
                       "drug_central",
                       "unichem",
                       "repotrial",
                       "iid",
                       "intact",
                       "omim",
                       "sider"}
    if download:
        downloaders.download_all(ignored_sources=ignored_sources)

    mondo.parse_mondo_json()
    ncbi.parse_gene_info()
    if version == "licensed":
        drugbank._parse_drugbank()  # requires proteins to be parsed first
    elif version == "open":
        drugbank.parse_drugbank()
    ctd.parse()
    disgenet.parse_gene_disease_associations()
    if download or version_update:
        get_and_update_versions(ignored_sources=ignored_sources)
@click.option("--conf", required=True, type=click.Path(exists=True))
@cli.command()
def restart_live(conf):
    print(f"Config file: {conf}")
    nedrexdb.parse_config(conf)

    live_instance = NeDRexLiveInstance()
    live_instance.remove()
    live_instance.set_up(use_existing_volume=True, neo4j_mode="db")


if __name__ == "__main__":
    cli()
