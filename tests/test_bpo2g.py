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
from datetime import datetime, timedelta

import pytest

import bpo2g


def test_parse_datetime():
    dt = bpo2g.parse_datetime("Jan 6 2025", "08:46")
    assert dt == datetime(2025, 1, 6, 8, 46)


def test_list_omron_bp_csv_files_matches_only_omron_csvs(tmp_path, omron_csv_path):
    # An Omron report, a non-Omron CSV, and a non-CSV file.
    (tmp_path / omron_csv_path.name).write_text(omron_csv_path.read_text())
    (tmp_path / "groceries.csv").write_text("a,b\n1,2\n")
    (tmp_path / "Your Requested OMRON Report notes.txt").write_text("nope")

    found = bpo2g.list_omron_bp_csv_files(str(tmp_path))

    assert len(found) == 1
    assert found[0].endswith(omron_csv_path.name)


def test_read_omron_bp_csv_file_parses_all_rows(omron_csv_path):
    readings = bpo2g.read_omron_bp_csv_file(str(omron_csv_path))

    assert len(readings) == 3
    first = readings[0]
    assert isinstance(first, bpo2g.BPReading)
    assert first.time == datetime(2025, 1, 12, 8, 12)
    assert (first.systolic, first.diastolic, first.bpm) == (114, 74, 47)


def test_read_omron_bp_csv_file_rejects_bad_header(tmp_path):
    bad = tmp_path / "Your Requested OMRON Report bad.csv"
    bad.write_text("Wrong,Header\n1,2\n")

    with pytest.raises(ValueError, match="Invalid Omron BP .csv format"):
        bpo2g.read_omron_bp_csv_file(str(bad))


def test_read_csv_data_sorts_by_datetime(tmp_path, omron_csv_path):
    (tmp_path / omron_csv_path.name).write_text(omron_csv_path.read_text())

    sorted_readings = bpo2g.read_csv_data(str(tmp_path))

    keys = list(sorted_readings.keys())
    assert keys == sorted(keys)
    assert keys[0] == datetime(2025, 1, 6, 8, 46)
    assert keys[-1] == datetime(2025, 1, 12, 8, 12)


def test_datetime_to_iso_string_adds_utc_when_naive():
    iso = bpo2g.datetime_to_iso_string(datetime(2025, 1, 6, 8, 46))
    assert iso == "2025-01-06T08:46:00+00:00"


def test_is_within_last_six_months():
    assert bpo2g.is_within_last_six_months(datetime.now() - timedelta(days=10))
    assert not bpo2g.is_within_last_six_months(datetime.now() - timedelta(days=400))


def test_output_basic_stats_handles_no_recent_readings():
    """Old-only readings must not raise ZeroDivisionError on the averages."""
    old = datetime.now() - timedelta(days=400)
    readings = bpo2g.sort_dict_by_datetime_keys(
        {old: bpo2g.BPReading(old, 120, 80, 60)}
    )
    bpo2g.output_basic_stats(readings)  # no exception == pass


def test_output_basic_stats_averages_recent_readings(caplog):
    import logging

    now = datetime.now()
    readings = bpo2g.sort_dict_by_datetime_keys(
        {
            now - timedelta(days=1): bpo2g.BPReading(now, 110, 70, 50),
            now - timedelta(days=2): bpo2g.BPReading(now, 130, 90, 70),
        }
    )
    with caplog.at_level(logging.INFO):
        bpo2g.output_basic_stats(readings)
    assert "Avg Systolic: 120.0" in caplog.text


def test_login_garmin_missing_session_exits(tmp_path, monkeypatch):
    """A missing token store should exit(1) with a bootstrap hint, not crash."""

    def fake_login(self, tokenstore=None):
        raise FileNotFoundError(tokenstore)

    monkeypatch.setattr(bpo2g.Garmin, "login", fake_login)

    with pytest.raises(SystemExit) as exc:
        bpo2g.login_garmin(str(tmp_path / "nope"))
    assert exc.value.code == 1
