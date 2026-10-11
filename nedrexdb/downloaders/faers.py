import os as _os
from datetime import datetime as _datetime
from pathlib import Path as _Path

import requests as _requests
from tqdm import tqdm as _tqdm

from nedrexdb import config as _config
from nedrexdb.logger import logger


START_YEAR = 2013
QUARTERS = (1, 2, 3, 4)
FILE_TYPE = "xml"

HEADERS = {
    "User-Agent": "FAERS-Downloader/1.0",
}


def _build_candidates(base_url: str, year: int, quarter: int, file_type: str):
    """
    FAERS has historically used slightly inconsistent naming conventions,
    so try both known URL patterns.
    """
    base_url = base_url.rstrip("/") + "/"

    return [
        f"{base_url}faers_{file_type}_{year}Q{quarter}.zip",
        f"{base_url}faers_{file_type}_{year}q{quarter}.zip",
        f"{base_url}faers_{file_type}*{year}Q{quarter}.zip",
        f"{base_url}faers*{file_type}_{year}q{quarter}.zip",
    ]


def _download_file(url: str, output_path: _Path) -> bool:
    """
    Download one FAERS archive.

    Returns False for a 404 so the caller can try another URL candidate.
    """
    if output_path.exists():
        logger.debug(f"FAERS file already exists: {output_path}")
        return True

    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with _requests.get(
            url,
            stream=True,
            headers=HEADERS,
            timeout=60,
        ) as response:

            if response.status_code == 404:
                return False

            response.raise_for_status()

            total = int(response.headers.get("content-length", 0))

            with output_path.open("wb") as output, _tqdm(
                total=total,
                unit="B",
                unit_scale=True,
                desc=output_path.name,
            ) as progress:

                for chunk in response.iter_content(
                    chunk_size=1024 * 1024
                ):
                    if chunk:
                        output.write(chunk)
                        progress.update(len(chunk))

        return True

    except Exception as exc:
        logger.warning(
            f"FAERS download failed for {url}: {exc}"
        )

        # Don't leave a partial archive around.
        if output_path.exists():
            output_path.unlink()

        return False


def _download_one(
    base_url: str,
    year: int,
    quarter: int,
    file_type: str,
    output_dir: _Path,
):
    filename = (
        f"faers_{file_type}_{year}Q{quarter}.zip"
    )

    output_path = (
        output_dir
        / str(year)
        / f"Q{quarter}"
        / file_type
        / filename
    )

    for url in _build_candidates(
        base_url,
        year,
        quarter,
        file_type,
    ):
        logger.debug(
            f"Trying FAERS download: {url}"
        )

        # The "*" in some of the historical candidate patterns
        # cannot be interpreted by HTTP servers as a wildcard.
        # Skip those candidates and only use concrete URLs.
        if "*" in url:
            continue

        if _download_file(url, output_path):
            logger.info(
                f"Downloaded FAERS {year} Q{quarter} "
                f"{file_type}: {url}"
            )
            return True

    logger.warning(
        f"FAERS archive not found: "
        f"{year} Q{quarter} {file_type}"
    )

    return False


def download_faers():
    """
    Download all available quarterly FAERS XML archives.

    FAERS data starts in 2013. The current year is used as the
    upper bound; missing future quarters are simply skipped.
    """
    base_url = _config["sources.faers.quarterly.url"]

    output_dir = (
        _Path(_config["db.root_directory"])
        / _config["sources.directory"]
        / "faers"
    )

    current_year = _datetime.utcnow().year

    logger.info(
        f"Downloading FAERS quarterly data "
        f"from {START_YEAR} to {current_year}"
    )

    downloaded = 0
    missing = 0

    for year in range(START_YEAR, current_year + 1):
        for quarter in QUARTERS:

            success = _download_one(
                base_url=base_url,
                year=year,
                quarter=quarter,
                file_type=FILE_TYPE,
                output_dir=output_dir,
            )

            if success:
                downloaded += 1
            else:
                missing += 1

    logger.info(
        f"FAERS download finished: "
        f"{downloaded} downloaded, {missing} missing"
    )

    return current_year