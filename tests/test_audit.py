"""Tests for the evidence collection, testing and retest scripts."""

from __future__ import annotations

import shutil
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "audit"))

import collect_evidence  # noqa: E402
import retest  # noqa: E402
import run_tests  # noqa: E402

EVIDENCE = sorted((ROOT / "evidence").glob("directory-*"))[0]
SCENARIO = ROOT / "scenario"


@pytest.fixture(scope="module")
def results():
    ev, tests = run_tests.run_all(EVIDENCE, SCENARIO)
    return ev, {t.test_id: t for t in tests}


def exceptions(test):
    return sorted(i.item.split(":")[0] for i in test.exceptions())


def test_working_days_skip_weekends_and_bank_holidays():
    # Saturday 29 August 2026, then Monday 31 August is a bank holiday.
    assert run_tests.working_days_after(date(2026, 8, 29), 1) == date(2026, 9, 1)
    assert run_tests.working_days_after(date(2026, 9, 14), 5) == date(2026, 9, 21)


def test_account_types():
    assert run_tests.account_type("Administrator") == "Built in"
    assert run_tests.account_type("adm.jcarter") == "Administrator"
    assert run_tests.account_type("svc-backup") == "Service"
    assert run_tests.account_type("priya.shah", "NW1007") == "Personal"
    assert run_tests.account_type("finance.shared") == "Generic"


def test_ldif_parsing_handles_folded_and_base64_lines():
    ldif = (
        "# record 1\ndn: CN=a,DC=x\nmanager: CN=olivia.bennett,OU=Finance,DC=northwi\n"
        " nd,DC=internal\ndescription:: SGVsbG8gd29ybGQ=\n\n"
    )
    rec = collect_evidence.parse_ldif(ldif)[0]
    assert rec["manager"] == ["CN=olivia.bennett,OU=Finance,DC=northwind,DC=internal"]
    assert rec["description"] == ["Hello world"]


def test_filetime_conversion():
    assert collect_evidence.filetime("134375402072038480").startswith("2026-10-27T02:")
    assert collect_evidence.filetime("0") == ""
    assert collect_evidence.filetime("9223372036854775807") == ""


def test_evidence_is_complete_and_intact():
    assert run_tests.verify_evidence(EVIDENCE) == []
    log = (EVIDENCE / "extraction-log.txt").read_text()
    assert "user objects in raw-users.ldif: 32" in log and "rows in users.csv: 32" in log


def test_tampered_evidence_is_rejected(tmp_path):
    copy = tmp_path / EVIDENCE.name
    shutil.copytree(EVIDENCE, copy)
    users = copy / "users.csv"
    users.write_text(users.read_text().replace("mark.taylor,Mark", "mark.taylor,Marc"))
    assert run_tests.verify_evidence(copy) == ["users.csv: modified since extraction"]


@pytest.mark.parametrize(
    ("test_id", "expected"),
    [
        ("AC-01", ["mark.taylor"]),
        ("AC-02", ["emma.wilson"]),
        ("AC-03", []),
        ("AC-04", ["leo.martin", "mark.taylor"]),
        ("AC-05", ["leo.martin"]),
        ("AC-06", ["leo.martin", "svc-financeapp"]),
        ("AC-07", ["Account lockout threshold (attempts)", "Minimum password length"]),
        ("AC-08", ["finance.shared", "sarah.mitchell"]),
        ("AC-09", ["finance.shared"]),
        ("AC-10", ["liam.brooks", "svc-backup"]),
        ("AC-11", ["priya.shah"]),
        ("AC-12", ["REQ-2025-118"]),
        ("AC-13", ["Domain Admins", "Domain Admins", "Finance-Payments-Initiators"]),
        ("AC-14", ["Q3 2026 access review"]),
    ],
)
def test_each_control_finds_exactly_the_expected_exceptions(results, test_id, expected):
    _, tests = results
    assert exceptions(tests[test_id]) == expected


def test_passing_items_are_recorded_not_just_failures(results):
    _, tests = results
    leavers = {i.item.split(":")[0]: i.result for i in tests["AC-01"].items}
    assert leavers == {"mark.taylor": "Exception", "oliver.scott": "Pass", "isla.wright": "Pass"}


def test_every_finding_is_raised_by_a_test(results):
    _, tests = results
    raised = {f for t in tests.values() for f in t.findings}
    assert raised == {f"F{n}" for n in range(1, 11)}


def test_retest_on_unremediated_evidence_leaves_every_finding_open():
    ev = run_tests.Evidence(EVIDENCE, SCENARIO)
    assert {status for status, _ in retest.check(ev).values()} == {"Open"}


def test_no_dashes_in_any_text():
    for path in ROOT.rglob("*"):
        if (
            path.is_file()
            and ".git" not in path.parts
            and path.suffix in {".md", ".py", ".sh", ".csv", ".txt", ".yml"}
        ):
            text = path.read_text()
            assert "\u2014" not in text and "\u2013" not in text, path


def test_every_test_is_mapped_to_both_frameworks(results):
    _, tests = results
    for t in tests.values():
        assert t.iso27001.startswith("A."), t.test_id
        assert t.cis_controls[0].isdigit(), t.test_id
