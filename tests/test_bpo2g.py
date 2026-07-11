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
import logging
from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest
from click.testing import CliRunner

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


def test_fetch_existing_bp_timestamps_parses_nested_response():
    garmin = Mock()
    garmin.get_blood_pressure.return_value = {
        "measurementSummaries": [
            {
                "measurements": [
                    {
                        "systolic": 108,
                        "diastolic": 80,
                        "pulse": 61,
                        "measurementTimestampGMT": "2026-07-10T06:51:00.0",
                    },
                    {
                        "systolic": 120,
                        "diastolic": 82,
                        "pulse": 65,
                        "measurementTimestampGMT": "2026-07-11T07:15:00.0",
                    },
                ]
            },
            {
                "measurements": [
                    {
                        "systolic": 115,
                        "diastolic": 75,
                        "pulse": 58,
                        "measurementTimestampGMT": "2026-07-12T08:00:00.0",
                    },
                ]
            },
        ]
    }

    start = datetime(2026, 7, 10)
    end = datetime(2026, 7, 12)
    readings = bpo2g.fetch_existing_bp_timestamps(garmin, start, end)

    garmin.get_blood_pressure.assert_called_once_with("2026-07-10", "2026-07-12")
    assert readings == {
        datetime(2026, 7, 10, 6, 51): (108, 80, 61),
        datetime(2026, 7, 11, 7, 15): (120, 82, 65),
        datetime(2026, 7, 12, 8, 0): (115, 75, 58),
    }


def test_fetch_existing_bp_timestamps_handles_missing_summaries():
    garmin = Mock()
    garmin.get_blood_pressure.return_value = {}

    readings = bpo2g.fetch_existing_bp_timestamps(
        garmin, datetime(2026, 7, 1), datetime(2026, 7, 31)
    )

    assert readings == {}


def test_fetch_existing_bp_timestamps_handles_missing_measurements_key():
    garmin = Mock()
    garmin.get_blood_pressure.return_value = {
        "measurementSummaries": [{}, {"measurements": []}]
    }

    readings = bpo2g.fetch_existing_bp_timestamps(
        garmin, datetime(2026, 7, 1), datetime(2026, 7, 31)
    )

    assert readings == {}


def test_fetch_existing_bp_timestamps_normalizes_to_minute_precision():
    """A CSV reading's naive datetime must match the normalized Garmin timestamp."""
    garmin = Mock()
    garmin.get_blood_pressure.return_value = {
        "measurementSummaries": [
            {
                "measurements": [
                    {
                        "systolic": 114,
                        "diastolic": 74,
                        "pulse": 47,
                        "measurementTimestampGMT": "2025-01-12T08:12:00.0",
                    },
                ]
            }
        ]
    }

    readings = bpo2g.fetch_existing_bp_timestamps(
        garmin, datetime(2025, 1, 12), datetime(2025, 1, 12)
    )

    csv_reading_time = datetime(2025, 1, 12, 8, 12)
    assert csv_reading_time.replace(second=0, microsecond=0) in readings


def test_fetch_existing_bp_timestamps_parses_timestamp_with_no_fractional_part():
    """Garmin timestamps without a "." (no fractional seconds) must still parse."""
    garmin = Mock()
    garmin.get_blood_pressure.return_value = {
        "measurementSummaries": [
            {
                "measurements": [
                    {
                        "systolic": 114,
                        "diastolic": 74,
                        "pulse": 47,
                        "measurementTimestampGMT": "2025-01-12T08:12:00",
                    },
                ]
            }
        ]
    }

    readings = bpo2g.fetch_existing_bp_timestamps(
        garmin, datetime(2025, 1, 12), datetime(2025, 1, 12)
    )

    assert readings == {datetime(2025, 1, 12, 8, 12): (114, 74, 47)}


def test_fetch_existing_bp_timestamps_chunks_wide_range_into_28_day_windows():
    """A range spanning ~60 days must be split into multiple <=28-day requests
    that together cover the full span with no gap or overlap."""
    garmin = Mock()
    garmin.get_blood_pressure.return_value = {}

    start = datetime(2026, 1, 1)
    end = datetime(2026, 3, 2)  # 60 days later

    bpo2g.fetch_existing_bp_timestamps(garmin, start, end)

    assert garmin.get_blood_pressure.call_count >= 3

    calls = garmin.get_blood_pressure.call_args_list
    windows = [
        (
            datetime.strptime(call.args[0], "%Y-%m-%d"),
            datetime.strptime(call.args[1], "%Y-%m-%d"),
        )
        for call in calls
    ]

    # Windows must be sorted by start.
    assert windows == sorted(windows, key=lambda w: w[0])

    # No window exceeds 28 days (inclusive span).
    for window_start, window_end in windows:
        assert (window_end - window_start).days < 28

    # First window starts at start_date; last window ends at end_date.
    assert windows[0][0] == start
    assert windows[-1][1] == end

    # No gaps or overlaps: each window starts exactly one day after the
    # previous window ended.
    for (prev_start, prev_end), (next_start, _next_end) in zip(
        windows, windows[1:]
    ):
        assert next_start == prev_end + timedelta(days=1)


def test_login_garmin_missing_session_exits(tmp_path, monkeypatch):
    """A missing token store should exit(1) with a bootstrap hint, not crash."""

    def fake_login(self, tokenstore=None):
        raise FileNotFoundError(tokenstore)

    monkeypatch.setattr(bpo2g.Garmin, "login", fake_login)

    with pytest.raises(SystemExit) as exc:
        bpo2g.login_garmin(str(tmp_path / "nope"))
    assert exc.value.code == 1


def test_main_logs_warning_on_timestamp_match_with_differing_values(
    tmp_path, monkeypatch, caplog
):
    """A timestamp already in Garmin with different values must WARN and skip,
    not silently swallow the discrepancy or overwrite the existing value."""
    reading_time = datetime(2025, 1, 12, 8, 12)
    csv_readings = bpo2g.sort_dict_by_datetime_keys(
        {reading_time: bpo2g.BPReading(reading_time, 130, 85, 70)}
    )

    monkeypatch.setattr(bpo2g, "read_csv_data", lambda csv_directory: csv_readings)
    monkeypatch.setattr(bpo2g, "login_garmin", lambda tokenstore: Mock())
    monkeypatch.setattr(
        bpo2g,
        "fetch_existing_bp_timestamps",
        lambda garmin, start_date, end_date: {reading_time: (114, 74, 47)},
    )

    runner = CliRunner()
    with caplog.at_level(logging.WARNING):
        result = runner.invoke(
            bpo2g.main,
            ["-c", str(tmp_path), "--dry_run"],
        )

    assert result.exit_code == 0
    assert "already exists in Garmin with different values" in caplog.text
    assert "existing=(114, 74, 47)" in caplog.text
    assert "incoming=(130, 85, 70)" in caplog.text
