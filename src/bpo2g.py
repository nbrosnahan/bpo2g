# Copyright 2026 Tumbling Potato
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import csv
import logging
import os
import sys
import time
from collections import OrderedDict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import NamedTuple

import click
from garminconnect import Garmin

# Default location of the persisted Garmin OAuth token session, matching the
# garminconnect convention. Override with --tokenstore or the GARMINTOKENS env
# var. Mint/refresh it with: uv run python bootstrap_garmin_session.py
DEFAULT_TOKENSTORE = "~/.garminconnect"

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Create a logger
logger = logging.getLogger(__name__)


class BPReading(NamedTuple):
    time: datetime
    systolic: int
    diastolic: int
    bpm: int


def list_omron_bp_csv_files(directory: str) -> list[str]:
    paths = []
    for filename in os.listdir(directory):
        file_path = os.path.abspath(os.path.join(directory, filename))
        # logger.debug(f"Considering path: {file_path}")

        if "Your Requested OMRON Report" in file_path and file_path.endswith(".csv"):
            # logger.debug(f"Adding path: {file_path}")
            paths.append(file_path)

    return paths


def read_omron_bp_csv_file(csv_file_path: str) -> list[BPReading]:
    logger.debug(f"Loading file: {csv_file_path}")

    readings = []

    # Open and read the CSV file
    with open(csv_file_path, newline="") as file:
        expected_columns = [
            "Date",
            "Time",
            "Systolic (mmHg)",
            "Diastolic (mmHg)",
            "Pulse (bpm)",
            "Symptoms",
            "Consumed",
            "TruRead",
            "Notes",
        ]

        csv_reader = csv.reader(file)  # Create a CSV reader object
        found_columns = next(csv_reader)

        if found_columns != expected_columns:
            logger.error(
                "First line of .csv file does not match expected Omron BP .csv header."
            )
            logger.error(f"Expected: {expected_columns}")
            logger.error(f"Found: {found_columns}")
            raise ValueError("Invalid Omron BP .csv format")

        for row in csv_reader:
            # End of file, stop
            if len(row) == 0:
                break

            date_object = parse_datetime(row[0], row[1])
            systolic = int(row[2])
            diastolic = int(row[3])
            bpm = int(row[4])

            reading = BPReading(date_object, systolic, diastolic, bpm)

            readings.append(reading)

    return readings


def parse_datetime(date_string: str, time_string: str) -> datetime:
    datetime_string = f"{date_string} {time_string}"
    date_object = datetime.strptime(datetime_string, "%b %d %Y %H:%M")
    return date_object


def sort_dict_by_datetime_keys(my_dict: dict[datetime, BPReading]) -> OrderedDict[datetime, BPReading]:
    """
    Sorts a dictionary by its datetime keys in ascending order.

    Args:
      my_dict: The dictionary to be sorted.

    Returns:
      An OrderedDict with the keys sorted by their datetime values.
    """
    return OrderedDict(sorted(my_dict.items(), key=lambda item: item[0]))


def datetime_to_iso_string(dt_obj: datetime) -> str:
    """
    Converts a datetime object to an ISO 8601 format string.

    Args:
      dt_obj: The datetime object to convert.

    Returns:
      The ISO 8601 format string representing the datetime object.
    """
    if dt_obj.tzinfo is None:
        dt_obj = dt_obj.replace(tzinfo=UTC)
    return dt_obj.isoformat()


def is_within_last_six_months(date_obj: datetime) -> bool:
    """
    Checks if the given datetime object is within the last 6 months.

    Args:
      date_obj: The datetime object to check.

    Returns:
      True if the date_obj is within the last 6 months, False otherwise.
    """
    six_months_ago = datetime.now() - timedelta(days=180)  # Approximate 6 months
    return date_obj >= six_months_ago


def output_basic_stats(sorted_readings: OrderedDict[datetime, BPReading]) -> None:
    tot_sys = 0
    tot_dia = 0
    tot_bpm = 0
    tot_in_last_6_months = 0

    for key, value in sorted_readings.items():
        if is_within_last_six_months(value.time):
            tot_sys += value.systolic
            tot_dia += value.diastolic
            tot_bpm += value.bpm
            tot_in_last_6_months += 1

        logger.debug(value)

    logger.info(f"Readings in the last 6 months: {tot_in_last_6_months}")
    if tot_in_last_6_months == 0:
        logger.info("No readings in the last 6 months; skipping averages.")
        return
    logger.info(f"Avg Systolic: {tot_sys / tot_in_last_6_months * 1.0}")
    logger.info(f"Avg Diastolic: {tot_dia / tot_in_last_6_months * 1.0}")
    logger.info(f"Avg BPM: {tot_bpm / tot_in_last_6_months * 1.0}")


def read_csv_data(filepath: str) -> OrderedDict[datetime, BPReading]:
    all_readings: dict[datetime, BPReading] = {}
    paths = list_omron_bp_csv_files(filepath)
    for path in paths:
        if path.endswith(".csv"):
            readings = read_omron_bp_csv_file(path)
            for reading in readings:
                all_readings[reading.time] = reading
        else:
            logger.info("Skipping non-CSV path: {path}")
    sorted_readings = sort_dict_by_datetime_keys(all_readings)

    num_readings = len(all_readings)
    logger.info(f"Total Readings: {num_readings}")

    return sorted_readings


def login_garmin(tokenstore: str) -> Garmin:
    """Resume a persisted Garmin Connect session from ``tokenstore``.

    Garmin blocks ``garth``'s credential login endpoint (HTTP 429), so bpo2g
    never logs in with a username/password. It loads the OAuth token session
    minted by ``bootstrap_garmin_session.py`` and auto-refreshes the OAuth2
    token. If the session is missing or expired, instruct the user to (re-)run
    the bootstrap rather than falling back to the blocked credential flow.

    Args:
      tokenstore: Path to the saved garth token session directory.

    Returns:
      A logged-in ``Garmin`` client.
    """
    resolved = str(Path(tokenstore).expanduser())
    garmin = Garmin()
    try:
        garmin.login(tokenstore=resolved)
    except FileNotFoundError:
        logger.error(
            "No Garmin session found at %s. Mint one with:\n"
            "    uv run python bootstrap_garmin_session.py",
            resolved,
        )
        sys.exit(1)
    except Exception as e:  # noqa: BLE001 — surface a clear remediation hint
        logger.error(
            "Failed to resume the Garmin session at %s (%s). The token session "
            "may be missing or expired (~yearly). Re-mint it with:\n"
            "    uv run python bootstrap_garmin_session.py",
            resolved,
            e,
        )
        sys.exit(1)
    return garmin


@click.command()
@click.option("--dry_run", "-d", default=False, is_flag=True, help="Do a dry-run")
@click.option(
    "--csv_directory",
    "-c",
    required=True,
    help="Local directory with Omron BP .csv export files",
)
@click.option(
    "--tokenstore",
    "-t",
    default=lambda: os.getenv("GARMINTOKENS", DEFAULT_TOKENSTORE),
    show_default=DEFAULT_TOKENSTORE,
    help="Path to the persisted Garmin OAuth token session "
    "(default: $GARMINTOKENS or ~/.garminconnect). "
    "Mint it with bootstrap_garmin_session.py.",
)
@click.option(
    "--requestdelayms",
    "-r",
    required=False,
    default=0,
    help="Garmin Connect Request Delay (in ms)",
)
def main(dry_run: bool, csv_directory: str, tokenstore: str, requestdelayms: int) -> None:
    try:
        logger.debug(
            f"Inputs received: dry_run={dry_run}, csv_directory={csv_directory}, tokenstore={tokenstore}"
        )

        # Add your file processing logic here
        sorted_readings = read_csv_data(csv_directory)

        if len(sorted_readings) == 0:
            logger.info(f"No BP readings found in csv_directory: {csv_directory}")
            sys.exit(1)

        output_basic_stats(sorted_readings)

        # Resume the persisted Garmin Connect session (no credential login).
        garmin = login_garmin(tokenstore)
        logger.info(garmin)

        # Upload BP data to Garmin Connect
        for key, value in sorted_readings.items():
            if dry_run:
                log_prefix = "DRYRUN: garmin.set_blood_pressure"
            else:
                log_prefix = "garmin.set_blood_pressure"

            logger.info(
                f"{log_prefix}({value.systolic}, {value.diastolic}, {value.bpm}, {datetime_to_iso_string(value.time)})"
            )

            if not dry_run:
                garmin.set_blood_pressure(
                    value.systolic,
                    value.diastolic,
                    value.bpm,
                    datetime_to_iso_string(value.time),
                )
            if requestdelayms > 0:
                logger.info(f"Delaying by {requestdelayms} ms")
                time.sleep(requestdelayms / 1000)
    except KeyboardInterrupt:
        print("\nInput cancelled.")
        sys.exit(1)


if __name__ == "__main__":
    main()
