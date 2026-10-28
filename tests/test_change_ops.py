"""Tests for the change management, IT operations and server access testing."""

from __future__ import annotations

import random
import shutil
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "audit"))

import change_ops_findings  # noqa: E402
import run_change_ops_tests as co  # noqa: E402
import run_tests  # noqa: E402

EVIDENCE = ROOT / "evidence"
APP = sorted(EVIDENCE.glob("app-*"))[0]
HOSTS = sorted(EVIDENCE.glob("host-*"))
DIRECTORY = EVIDENCE / "directory-20261027T030229Z"
SCENARIO = ROOT / "scenario"


@pytest.fixture(scope="module")
def results():
    ev, tests, samples = co.run_all(APP, HOSTS, DIRECTORY, SCENARIO)
    return ev, {t.test_id: t for t in tests}, samples


def exception_items(test):
    return sorted(i.item for i in test.exceptions())


def test_all_evidence_is_intact():
    for folder in [APP, *HOSTS]:
        assert run_tests.verify_evidence(folder) == [], folder.name


def test_tampered_app_evidence_is_rejected(tmp_path):
    copy = tmp_path / APP.name
    shutil.copytree(APP, copy)
    log = copy / "deployments.log"
    log.write_text(log.read_text().replace("ticket=none", "ticket=CHG-2026-0999", 1))
    assert run_tests.verify_evidence(copy) == ["deployments.log: modified since extraction"]


def test_extraction_counts_reconcile():
    log = (APP / "extraction-log.txt").read_text()
    assert "pull requests in the database: 47" in log
    assert "rows in gitea-pull-requests.csv: 47" in log
    assert "commits on main (git rev-list --count): 52" in log
    assert "rows in git-main-commits.csv: 52" in log
    for host in HOSTS:
        log = (host / "extraction-log.txt").read_text()
        passwd = int(log.split("lines in /etc/passwd: ")[1].split()[0])
        assert f"rows in local-accounts.csv: {passwd}" in log


@pytest.mark.parametrize(
    ("population", "size"),
    [(1, 1), (4, 4), (5, 5), (12, 5), (13, 15), (40, 15), (52, 15), (53, 25), (250, 25), (251, 40)],
)
def test_sample_size_table(population, size):
    assert co.sample_size(population) == size


def test_sample_is_reproducible_and_independent_of_order():
    keys = [f"item-{n:02d}" for n in range(40)]
    shuffled = keys[:]
    random.Random(1).shuffle(shuffled)
    assert co.select_sample(keys) == co.select_sample(shuffled)
    assert len(co.select_sample(keys)) == 15 and len(set(co.select_sample(keys))) == 15


def test_working_days_between():
    # Wednesday 23 September 2026 to Tuesday 6 October 2026.
    assert co.working_days_between(date(2026, 9, 23), date(2026, 10, 6)) == 9
    # Friday 28 August to Tuesday 1 September, over the bank holiday.
    assert co.working_days_between(date(2026, 8, 28), date(2026, 9, 1)) == 1


def test_population_completeness(results):
    ev, _, _ = results
    deployed = {d["commit"] for d in ev.period_deployments()}
    commits = {c["commit"] for c in ev.period_commits()}
    assert len(ev.period_deployments()) == 40
    assert deployed == commits


@pytest.mark.parametrize(
    ("test_id", "count"),
    [
        ("AC-15", 1),
        ("AC-16", 2),
        ("AC-17", 10),
        ("AC-18", 4),
        ("CM-01", 3),
        ("CM-02", 5),
        ("CM-03", 8),
        ("CM-04", 2),
        ("CM-05", 1),
        ("CM-06", 4),
        ("CM-07", 4),
        ("OP-01", 6),
        ("OP-02", 5),
        ("OP-03", 1),
        ("OP-04", 1),
        ("OP-05", 1),
        ("OP-06", 1),
        ("OP-07", 0),
    ],
)
def test_each_control_finds_the_expected_number_of_exceptions(results, test_id, count):
    _, tests, _ = results
    assert len(tests[test_id].exceptions()) == count


def test_server_access_exceptions(results):
    _, tests, _ = results
    assert exception_items(tests["AC-15"]) == ["linux2: support"]
    assert exception_items(tests["AC-16"]) == [
        "linux2: ryan.patel via ryan.patel",
        "linux2: support via %sudo",
    ]
    assert exception_items(tests["AC-18"]) == [
        "leo.martin",
        "liam.brooks",
        "priya.shah",
        "ryan.patel",
    ]


def test_change_exceptions(results):
    ev, tests, _ = results
    direct = [i for i in tests["CM-02"].exceptions() if "Pushed directly" in i.comment]
    assert len(direct) == 4 and all("ryan.patel" in i.comment for i in direct)
    assert [i.item for i in tests["CM-05"].exceptions()] == ["CHG-2026-0137"]
    assert all("ryan.patel" in i.comment for i in tests["CM-03"].exceptions())
    assert {i.item for i in tests["CM-07"].exceptions()} == {
        "aisha.khan",
        "leo.martin",
        "ryan.patel",
        "support",
    }


def test_operations_exceptions(results):
    _, tests, _ = results
    assert exception_items(tests["OP-01"]) == [
        "2026-07-19",
        "2026-08-08",
        "2026-08-09",
        "2026-08-10",
        "2026-08-11",
        "2026-09-20",
    ]
    passed = [i.item for i in tests["OP-02"].items if i.result == "Pass"]
    assert passed == ["2026-09-20"]
    assert exception_items(tests["OP-05"]) == ["linux2: finance-tidy"]


def test_samples_are_recorded_with_the_population(results):
    _, tests, samples = results
    for test_id in ("AC-18", "CM-04"):
        s = samples[test_id]
        assert len(s["sample"]) == co.sample_size(len(s["population"])) == 15
        assert set(s["sample"]) <= set(s["population"])
        assert tests[test_id].sample.startswith("15 of ")
        assert len(tests[test_id].items) == 15


def test_every_finding_is_raised_by_a_test(results):
    _, tests, _ = results
    raised = {f for t in tests.values() for f in t.findings}
    for f in change_ops_findings.FINDINGS:
        assert f.finding_id in raised, f.finding_id
        for test_id in f.tests:
            assert f.finding_id in tests[test_id].findings, (f.finding_id, test_id)


def test_every_test_is_mapped_to_both_frameworks(results):
    _, tests, _ = results
    for t in tests.values():
        assert t.iso27001.startswith("A.") and t.cis_controls[0].isdigit(), t.test_id
