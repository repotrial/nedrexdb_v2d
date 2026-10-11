import gzip
import json
import shutil
import sqlite3
import subprocess
import zipfile
import xml.etree.ElementTree as ET

from collections import defaultdict
from pathlib import Path

from tqdm import tqdm

from nedrexdb.db import MongoInstance
from nedrexdb.db.models.nodes.drug import Drug
from nedrexdb.db.models.nodes.side_effect import SideEffect
from nedrexdb.db.parsers import _get_file_location_factory
from nedrexdb import config as _config
from nedrexdb.logger import logger


get_file_location = _get_file_location_factory("faers")


def normalize_name(value):
    if value is None:
        return ""

    return " ".join(str(value).lower().strip().split())


def local_name(tag):
    if "}" in tag:
        return tag.rsplit("}", 1)[1]

    return tag


def get_text(element, tag):
    for child in element:
        if local_name(child.tag) != tag:
            continue

        if child.text is None:
            return None

        return child.text.strip()

    return None


def find_children(element, tag):
    return [
        child
        for child in element
        if local_name(child.tag) == tag
    ]


def build_drug_name_map():
    logger.info("Building FAERS drug name map")

    drug_name_map = {}
    collisions = 0

    collection = MongoInstance.DB[Drug.collection_name]

    for drug in collection.find(
        {},
        {
            "primaryDomainId": 1,
            "displayName": 1,
            "synonyms": 1,
            "rxnormNames": 1,
        },
    ):
        domain_id = drug.get("primaryDomainId")

        if not domain_id:
            continue

        names = []

        if drug.get("displayName"):
            names.append(drug["displayName"])

        names.extend(drug.get("synonyms", []) or [])
        names.extend(drug.get("rxnormNames", []) or [])

        for name in names:
            normalized = normalize_name(name)

            if not normalized:
                continue

            existing = drug_name_map.get(normalized)

            if existing is not None and existing != domain_id:
                collisions += 1
                continue

            drug_name_map[normalized] = domain_id

    logger.info(
        "Built FAERS drug name map: %s names, %s collisions",
        len(drug_name_map),
        collisions,
    )

    return drug_name_map


def build_side_effect_name_map():
    logger.info("Building FAERS side-effect name map")

    side_effect_name_map = {}
    collisions = 0

    collection = MongoInstance.DB[
        SideEffect.collection_name
    ]

    for side_effect in collection.find(
        {},
        {
            "primaryDomainId": 1,
            "displayName": 1,
            "synonyms": 1,
        },
    ):
        domain_id = side_effect.get("primaryDomainId")

        if not domain_id:
            continue

        names = []

        if side_effect.get("displayName"):
            names.append(side_effect["displayName"])

        names.extend(
            side_effect.get("synonyms", []) or []
        )

        for name in names:
            normalized = normalize_name(name)

            if not normalized:
                continue

            existing = side_effect_name_map.get(normalized)

            if (
                existing is not None
                and existing != domain_id
            ):
                collisions += 1
                continue

            side_effect_name_map[normalized] = domain_id

    logger.info(
        "Built FAERS side-effect name map: %s names, %s collisions",
        len(side_effect_name_map),
        collisions,
    )

    return side_effect_name_map

def create_case_db(path):
    connection = sqlite3.connect(path)

    connection.execute(
        """
        CREATE TABLE cases (
            report_id TEXT PRIMARY KEY,
            report_version INTEGER NOT NULL,
            payload TEXT NOT NULL
        )
        """
    )

    connection.execute(
        """
        CREATE INDEX idx_cases_version
        ON cases(report_version)
        """
    )

    connection.commit()

    return connection


def extract_report(
    report,
    drug_name_map,
    side_effect_name_map,
):
    report_id = get_text(report, "safetyreportid")

    if not report_id:
        return None

    version_text = get_text(report, "safetyreportversion")

    try:
        report_version = int(version_text or 0)
    except ValueError:
        report_version = 0

    nullified = get_text(report, "casenullification") == "1"

    if nullified:
        return {
            "report_id": report_id,
            "report_version": report_version,
            "nullified": True,
        }

    serious = get_text(report, "serious") == "1"
    fatal = get_text(report, "seriousnessdeath") == "1"
    country = get_text(report, "occurcountry")

    drug_ids = set()
    side_effect_ids = set()

    patient = None

    for child in report:
        if local_name(child.tag) == "patient":
            patient = child
            break

    if patient is not None:
        for patient_child in patient:
            child_name = local_name(patient_child.tag)

            if child_name == "drug":
                medicinal_product = get_text(
                    patient_child,
                    "medicinalproduct",
                )

                normalized = normalize_name(medicinal_product)

                if normalized:
                    drug_id = drug_name_map.get(normalized)

                    if drug_id:
                        drug_ids.add(drug_id)

            elif child_name == "reaction":
                reaction_term = get_text(
                    patient_child,
                    "reactionmeddrapt",
                )

                normalized = normalize_name(reaction_term)

                if normalized:
                    side_effect_id = side_effect_name_map.get(
                        normalized
                    )

                    if side_effect_id:
                        side_effect_ids.add(side_effect_id)

    return {
        "report_id": report_id,
        "report_version": report_version,
        "nullified": False,
        "serious": serious,
        "fatal": fatal,
        "country": country,
        "drug_ids": list(drug_ids),
        "side_effect_ids": list(side_effect_ids),
    }


def parse_xml_stream(
    raw,
    connection,
    drug_name_map,
    side_effect_name_map,
):
    reports = 0
    higher_versions_replaced = 0
    older_versions_ignored = 0
    nullified_current_versions = 0

    for _, element in ET.iterparse(raw, events=("end",)):
        if local_name(element.tag) != "safetyreport":
            continue

        report = extract_report(
            element,
            drug_name_map,
            side_effect_name_map,
        )

        if report is not None:
            reports += 1

            report_id = report["report_id"]
            report_version = report["report_version"]

            row = connection.execute(
                """
                SELECT report_version
                FROM cases
                WHERE report_id = ?
                """,
                (report_id,),
            ).fetchone()

            if row is None:
                connection.execute(
                    """
                    INSERT INTO cases (
                        report_id,
                        report_version,
                        payload
                    )
                    VALUES (?, ?, ?)
                    """,
                    (
                        report_id,
                        report_version,
                        json.dumps(report),
                    ),
                )

                if report["nullified"]:
                    nullified_current_versions += 1

            elif report_version > row[0]:
                connection.execute(
                    """
                    UPDATE cases
                    SET
                        report_version = ?,
                        payload = ?
                    WHERE report_id = ?
                    """,
                    (
                        report_version,
                        json.dumps(report),
                        report_id,
                    ),
                )

                higher_versions_replaced += 1

                if report["nullified"]:
                    nullified_current_versions += 1

            else:
                older_versions_ignored += 1

        # Only clear the completed safetyreport.
        #
        # Clearing child elements such as patient/drug/reaction before
        # extract_report() has completed would destroy the information
        # needed to build the report.
        element.clear()

    connection.commit()

    logger.info(
        "Parsed XML: reports=%s, higher_versions_replaced=%s, "
        "older_versions_ignored=%s, nullified_current_versions=%s",
        reports,
        higher_versions_replaced,
        older_versions_ignored,
        nullified_current_versions,
    )


def parse_archive(
    archive_path,
    connection,
    drug_name_map,
    side_effect_name_map,
):
    logger.info("Parsing FAERS archive: %s", archive_path)

    with zipfile.ZipFile(archive_path) as archive:
        xml_files = [
            info
            for info in archive.infolist()
            if info.filename.lower().endswith(".xml")
        ]

        logger.info(
            "Found %s XML files in %s",
            len(xml_files),
            archive_path,
        )

        for info in xml_files:
            logger.info(
                "Parsing XML: %s",
                info.filename,
            )

            try:
                with archive.open(info) as raw:
                    parse_xml_stream(
                        raw,
                        connection,
                        drug_name_map,
                        side_effect_name_map,
                    )

            except NotImplementedError:
                logger.warning(
                    "Python zipfile does not support compression "
                    "method 9 for %s; using system unzip",
                    info.filename,
                )

                unzip_path = shutil.which("unzip")

                if not unzip_path:
                    raise RuntimeError(
                        "Archive requires system unzip, but "
                        "'unzip' was not found"
                    )

                process = subprocess.Popen(
                    [
                        unzip_path,
                        "-p",
                        str(archive_path),
                        info.filename,
                    ],
                    stdout=subprocess.PIPE,
                )

                try:
                    parse_xml_stream(
                        process.stdout,
                        connection,
                        drug_name_map,
                        side_effect_name_map,
                    )
                finally:
                    process.stdout.close()

                    return_code = process.wait()

                    if return_code != 0:
                        raise RuntimeError(
                            f"unzip failed for {info.filename} "
                            f"with exit code {return_code}"
                        )

                # Important:
                # The system-unzip path successfully processed this XML.
                # Continue with the next XML in the archive.
                continue


def find_faers_archives():
    from nedrexdb import config as _config

    faers_dir = (
        Path(_config["db.root_directory"])
        / _config["sources.directory"]
        / "faers"
    )

    if not faers_dir.exists():
        raise FileNotFoundError(
            f"FAERS directory does not exist: {faers_dir}"
        )

    archives = sorted(
        faers_dir.glob(
            "*/*/xml/faers_xml_*.zip"
        )
    )

    if not archives:
        raise FileNotFoundError(
            f"No FAERS archives found below {faers_dir}"
        )

    return archives


def create_edge_snapshot(
    connection,
    output_file,
):
    logger.info(
        "Creating FAERS edge snapshot: %s",
        output_file,
    )

    pair_data = defaultdict(
        lambda: {
            "report_ids": set(),
            "serious_count": 0,
            "fatal_count": 0,
            "countries": set(),
        }
    )

    current_cases = 0
    nullified_cases = 0
    pairs = 0

    cursor = connection.execute(
        """
        SELECT payload
        FROM cases
        """
    )

    for (payload,) in tqdm(
        cursor,
        desc="Building FAERS edge data",
    ):
        report = json.loads(payload)

        if report.get("nullified"):
            nullified_cases += 1
            continue

        current_cases += 1

        drug_ids = report.get("drug_ids", [])
        side_effect_ids = report.get(
            "side_effect_ids",
            [],
        )

        for drug_id in drug_ids:
            for side_effect_id in side_effect_ids:
                pair = (
                    drug_id,
                    side_effect_id,
                )

                data = pair_data[pair]

                data["report_ids"].add(
                    report["report_id"]
                )

                if report.get("serious"):
                    data["serious_count"] += 1

                if report.get("fatal"):
                    data["fatal_count"] += 1

                country = report.get("country")

                if country:
                    data["countries"].add(country)

                pairs += 1

    logger.info(
        "Current cases=%s, nullified=%s, pairs=%s, edges=%s",
        current_cases,
        nullified_cases,
        pairs,
        len(pair_data),
    )

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with gzip.open(
        output_file,
        "wt",
        encoding="utf-8",
    ) as output:
        for (
            drug_id,
            side_effect_id,
        ), data in tqdm(
            pair_data.items(),
            desc="Writing FAERS snapshot",
            total=len(pair_data),
        ):
            record = {
                "sourceDomainId": drug_id,
                "targetDomainId": side_effect_id,
                "report_count": len(
                    data["report_ids"]
                ),
                "serious_count": data[
                    "serious_count"
                ],
                "fatal_count": data[
                    "fatal_count"
                ],
                "report_ids": list(
                    data["report_ids"]
                ),
                "countries": list(
                    data["countries"]
                ),
                "dataSources": ["faers"],
            }

            output.write(
                json.dumps(record)
                + "\n"
            )

    logger.info(
        "FAERS snapshot complete: %s",
        output_file,
    )


def create_faers_snapshot():
    logger.info(
        "Creating FAERS current-state snapshot"
    )

    drug_name_map = build_drug_name_map()
    side_effect_name_map = (
        build_side_effect_name_map()
    )

    archives = find_faers_archives()

    latest_archive = archives[-1]

    logger.info(
        "Latest FAERS archive: %s",
        latest_archive,
    )

    name = latest_archive.name.lower()

    quarter = None

    for part in name.replace(".zip", "").split("_"):
        if (
            part.startswith("20")
            and len(part) >= 6
            and part[4] == "q"
        ):
            quarter = part
            break

    if quarter is None:
        raise ValueError(
            f"Could not determine FAERS quarter "
            f"from archive name: {latest_archive.name}"
        )

    output_directory = (
            Path(_config["db.root_directory"])
            / "downloads"
            / "faers"
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    snapshot_file = (
        output_directory
        / f"faers_{quarter}.edges.jsonl.gz"
    )

    sqlite_file = (
        output_directory
        / f".faers_{quarter}.sqlite"
    )

    logger.info(
        "FAERS snapshot output: %s",
        snapshot_file,
    )

    logger.info(
        "FAERS staging database: %s",
        sqlite_file,
    )

    if sqlite_file.exists():
        logger.info(
            "Removing existing temporary FAERS "
            "SQLite database: %s",
            sqlite_file,
        )

        sqlite_file.unlink()

    connection = None

    try:
        connection = create_case_db(
            sqlite_file
        )

        for archive in archives:
            parse_archive(
                archive,
                connection,
                drug_name_map,
                side_effect_name_map,
            )

        create_edge_snapshot(
            connection,
            snapshot_file,
        )

    finally:
        if connection is not None:
            connection.close()

    # Only remove the staging database after the
    # snapshot has been successfully created.
    if sqlite_file.exists():
        sqlite_file.unlink()

        logger.info(
            "Removed temporary FAERS SQLite database: %s",
            sqlite_file,
        )

    logger.info(
        "FAERS snapshot creation finished: %s",
        snapshot_file,
    )


def parse_faers(snapshot_file=None, chunk_size=5000):
    """Bulk-insert the aggregated FAERS edge snapshot into MongoDB."""

    if snapshot_file is None:
        output_directory = (
            Path(_config["db.root_directory"])
            / "downloads"
            / "faers"
        )

        snapshots = sorted(
            output_directory.glob("faers_*.edges.jsonl.gz")
        )

        if not snapshots:
            raise FileNotFoundError(
                f"No FAERS edge snapshots found in {output_directory}"
            )

        snapshot_file = snapshots[-1]

    snapshot_file = Path(snapshot_file)

    if not snapshot_file.exists():
        raise FileNotFoundError(
            f"FAERS snapshot does not exist: {snapshot_file}"
        )

    from datetime import datetime
    from nedrexdb.db.models.edges.drug_has_adverse_reaction import (
        DrugHasAdverseReaction,
    )

    collection = MongoInstance.DB[
        DrugHasAdverseReaction.collection_name
    ]

    logger.info("Importing FAERS snapshot into MongoDB: %s", snapshot_file)

    batch = []
    imported = 0
    now = datetime.utcnow()

    with gzip.open(snapshot_file, "rt", encoding="utf-8") as input_file:
        for line in tqdm(input_file, desc="Importing FAERS edges"):
            record = json.loads(line)

            record["type"] = "DrugHasAdverseReaction"
            record["created"] = now
            record["updated"] = now

            batch.append(record)

            if len(batch) >= chunk_size:
                collection.insert_many(batch, ordered=False)
                imported += len(batch)
                batch.clear()

        if batch:
            collection.insert_many(batch, ordered=False)
            imported += len(batch)

    logger.info(
        "Imported %s FAERS edges from %s",
        imported,
        snapshot_file,
    )
