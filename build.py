#!/usr/bin/env python

import click
import os
import subprocess

import nedrexdb
from nedrexdb import config, downloaders
from nedrexdb.control.docker import NeDRexDevInstance, NeDRexLiveInstance, update_neo4j_image_version
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
    cosmic,
    ncg,
    intogen,
    orphanet,
    opentargets,
    hippie
)
from nedrexdb.downloaders import get_versions, update_versions
from nedrexdb.post_integration import (trim_uberon, drop_empty_collections)
from nedrexdb.post_integration.neo4j_db_adjustments import create_constraints, create_vector_indices


@click.group()
def cli():
    pass


@click.option("--conf", required=True, type=click.Path(exists=True))
@click.option("--download", is_flag=True, default=False)
@click.option("--version_update", is_flag=False, default="")
@click.option("--create_embeddings", is_flag=True, default=False)
@cli.command()
def update(conf, download, version_update, create_embeddings):
    print(f"Config file: {conf}")
    print(f"Download updates: {download}")
    print(f"Update DB versions: {version_update}")
    print(f"Create embeddings: {create_embeddings}")

    nedrexdb.parse_config(conf)

    version = config["db.version"]

    if version not in ["open", "licensed"]:
        raise Exception(f"invalid version {version!r}")

    version_update_skip = set()
    prev_metadata = {}

    update_neo4j_image_version()

# check for metadata of the current live version before fetching new data
    if download:
        try:
            MongoInstance.connect("live")
            prev_metadata = list(MongoInstance.DB["metadata"].find())
            prev_metadata = {} if prev_metadata is None else prev_metadata[0]["source_databases"]
            # log printing
            print("PREVIOUS METADATA")
            for source in prev_metadata:
                print(f"{source}:\t{prev_metadata[source]['version']}"
                      f" [{prev_metadata[source]['date']}]")
        except:
            print("No previous metadata found")

    dev_instance = NeDRexDevInstance()
    dev_instance.remove()
    dev_instance.set_up(use_existing_volume=False, neo4j_mode="import")
    MongoInstance.connect("dev")
    MongoInstance.set_indexes()

    if os.environ.get("TEST_MINIMUM", 0) == '1':
        parse_dev(version=version, download=download, version_update=version_update, prev_metadata=prev_metadata)
    else:
        if download:
            # update metadata
            # fallback version is rarely needed. Do not change that file, only use the config!
            default_version = None
            if os.path.exists("/data/nedrex_files/nedrex_data/fallback_version"):
                with open("/data/nedrex_files/nedrex_data/fallback_version") as fallback_file:
                    default_version = fallback_file.readline().rstrip()
            nedrex_versions = update_versions(version_update_skip, default_version=default_version)
            with open("/data/nedrex_files/nedrex_data/fallback_version", "w") as fallback_file:
                fallback_file.write(f"{nedrex_versions['version']}")

            # do the download
            print("Download: ON")
            current_metadata = nedrex_versions["source_databases"]
            subprocess.run(["./setup_data.sh", "/data/nedrex_files"])
            downloaders.download_all(prev_metadata=prev_metadata, current_metadata=current_metadata)

        if version_update:
            get_versions(version_update)

        # Parse sources contributing only nodes (and edges amongst those nodes)
        go.parse_go()
        mondo.parse_mondo_json()
        ncbi.parse_gene_info()
        uberon.parse()
        uniprot.parse_proteins()

        # Sources that add node type but require existing nodes, too
        cosmic.parse_gene_disease_associations()
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

        #Loading annotation information
        hippie_method_scores = hippie.parse_perplexity_techinque_scores()

        # Sources adding edges.
        ctd.parse()
        disgenet.parse_gene_disease_associations()
        intogen.parse_gene_disease_associations()
        orphanet.parse_gene_disease_associations()
        opentargets.parse_gene_disease_associations()
        ncg.parse_gene_disease_associations()

        go.parse_goa()
        hpa.parse_hpa()

        biogrid.parse_ppis(hippie_method_scores)
        iid.parse_ppis(hippie_method_scores)
        intact.parse(hippie_method_scores)

        if version == "licensed":
            omim.parse_gene_disease_associations()
            version_update_skip.add("omim")

        sider.parse()
        uniprot.parse_idmap()

        from nedrexdb.analyses import molecule_similarity
        molecule_similarity.run()

        # Post-processing
        trim_uberon.trim_uberon()
        
        #if download:
            # fallback version is rarely needed. Do not change that file, only use the config!
         #   default_version = None
         #   if os.path.exists("/data/nedrex_files/nedrex_data/fallback_version"):
         #       with open("/data/nedrex_files/nedrex_data/fallback_version") as fallback_file:
         #           default_version = fallback_file.readline().rstrip()
         #   nedrex_version = update_versions(version_update_skip, default_version=default_version)
         #   with open("/data/nedrex_files/nedrex_data/fallback_version", "w") as fallback_file:
         #       fallback_file.write(f"{nedrex_version}")
        #if version_update:
         #   get_versions(version_update)





    # clean up for export
    drop_empty_collections.drop_empty_collections()

    # export to Neo4j
    mongo_to_neo.mongo_to_neo(dev_instance, MongoInstance.DB)

    # Profile the collections
    collection_stats.profile_collections(MongoInstance.DB)

    collection_stats.verify_collections_after_profiling(MongoInstance.DB)


    # remove dev instance and set up live instance
    dev_instance.remove(neo4j_mode="import")

    dev_instance = NeDRexDevInstance()
    dev_instance.set_up(use_existing_volume=True, neo4j_mode="db-write")
    create_constraints()

    if create_embeddings:

        # create embeddings
        # try:
        create_vector_indices()
        # except Exception as e:
        #     print(e)
        #     print("Failed to create vector indices")

    dev_instance.remove()
    live_instance = NeDRexLiveInstance()
    live_instance.remove()
    live_instance.set_up(use_existing_volume=True, neo4j_mode="db")


def parse_dev(version, download, version_update, prev_metadata):
    # control source downloads
    ignored_sources = {"chembl",
                       "biogrid",
                       "go",
                       "uberon",
                       "clinvar",
                       "hpo",
                       "hpa",
                       "uniprot",
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
        # fallback version is rarely needed. Do not change that file, only use the config!
        default_version = None
        if os.path.exists("/data/nedrex_files/nedrex_data/fallback_version"):
            with open("/data/nedrex_files/nedrex_data/fallback_version") as fallback_file:
                default_version = fallback_file.readline().rstrip()
        nedrex_versions = update_versions(ignored_sources=ignored_sources, default_version=default_version)
        with open("/data/nedrex_files/nedrex_data/fallback_version", "w") as fallback_file:
            fallback_file.write(f"{nedrex_versions['version']}")

        # do the download
        print("Download: ON")
        current_metadata = nedrex_versions["source_databases"]
        subprocess.run(["./setup_data.sh", "/data/nedrex_files"])
        downloaders.download_all(ignored_sources=ignored_sources,
                                 prev_metadata=prev_metadata,
                                 current_metadata=current_metadata)

    if version_update:
        get_versions(version_update)

    mondo.parse_mondo_json()
    ncbi.parse_gene_info()
    opentargets.parse_gene_disease_associations()
    if version == "licensed":
        drugbank._parse_drugbank()
    elif version == "open":
        drugbank.parse_drugbank()
    ctd.parse()
    disgenet.parse_gene_disease_associations()


#    if download:
#        # fallback version is rarely needed. Do not change that file, only use the config!
#        default_version = None
#        if os.path.exists("/data/nedrex_files/nedrex_data/fallback_version"):
#            with open("/data/nedrex_files/nedrex_data/fallback_version") as fallback_file:
#                default_version = fallback_file.readline().rstrip()
#        nedrex_version = update_versions(ignored_sources=ignored_sources, default_version=default_version)
#        with open("/data/nedrex_files/nedrex_data/fallback_version", "w") as fallback_file:
#            fallback_file.write(f"{nedrex_version}")
#    if version_update:
#        get_versions(version_update)


@click.option("--conf", required=True, type=click.Path(exists=True))
# @click.option("--create_embeddings", is_flag=True, default=False)
@cli.command()
def restart_live(conf):
    print(f"Config file: {conf}")
    nedrexdb.parse_config(conf)
    
    # if create_embeddings:
    #     dev_instance = NeDRexDevInstance()
    #     dev_instance.remove(neo4j_mode="import")
    #     dev_instance.set_up(use_existing_volume=True, neo4j_mode="db-write")
    #     # create embeddings
    #     time.sleep(60)
    #     try:
    #         create_vector_indices.create_vector_indices()
    #     except Exception as e:
    #         print(e)
    #         print("Failed to create vector indices")
    #     dev_instance.remove()
    
    live_instance = NeDRexLiveInstance()
    live_instance.remove()
    live_instance.set_up(use_existing_volume=True, neo4j_mode="db")


if __name__ == "__main__":
    cli()
