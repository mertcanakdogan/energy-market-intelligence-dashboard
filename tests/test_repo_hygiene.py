"""Confidentiality guard: the repository must stay free of real names, contacts and local paths.

The test scans every tracked text file (``git ls-files``, or a directory walk outside git) for
patterns that would indicate employer, customer or personal data leaking into a public repo.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

TEXT_SUFFIXES = {
    ".py",
    ".md",
    ".sql",
    ".yaml",
    ".yml",
    ".toml",
    ".txt",
    ".csv",
    ".json",
    ".cfg",
    ".ini",
}
IGNORED_PARTS = {".git", ".venv", "venv", "__pycache__", "data", "powerbi/data", "build", "dist"}
SELF = Path(__file__).name

# Real energy-sector company names (word-bounded, case-sensitive). The data set is fictional, so
# none of these should appear anywhere in the repository.
FORBIDDEN_COMPANY_NAMES = [
    "Vattenfall",
    "Iberdrola",
    "TotalEnergies",
    "Statkraft",
    "Centrica",
    "Uniper",
    "Enel",
    "Engie",
    "EnBW",
    "Eneco",
    "RWE",
    "E.ON",
    "British Gas",
    "Octopus Energy",
]
FORBIDDEN_PATTERNS = {
    "e-mail address": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z]{2,}"),
    "local user path": re.compile(r"(?i)(?:[A-Z]:\\+Users\\+|/Users/[^/\s]+/|/home/[^/\s]+/)"),
    "cloud-sync path": re.compile(r"(?i)onedrive"),
    "private key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "API token": re.compile(r"\b(?:sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,})\b"),
    "IBAN": re.compile(r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){3,7}\b"),
}


def _candidate_files(root: Path) -> list[Path]:
    try:
        output = subprocess.run(
            ["git", "ls-files"], cwd=root, capture_output=True, text=True, check=True
        ).stdout
        files = [root / line for line in output.splitlines() if line]
    except (OSError, subprocess.CalledProcessError):
        files = [path for path in root.rglob("*") if path.is_file()]
    selected = []
    for path in files:
        relative = path.relative_to(root).as_posix()
        if path.name == SELF or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(relative == part or relative.startswith(f"{part}/") for part in IGNORED_PARTS):
            continue
        if path.exists():
            selected.append(path)
    return selected


@pytest.fixture(scope="module")
def repository_files(project_root: Path) -> list[Path]:
    files = _candidate_files(project_root)
    assert files, "hygiene scan found no files"
    return files


def test_scan_covers_the_main_artifacts(repository_files: list[Path], project_root: Path) -> None:
    names = {path.relative_to(project_root).as_posix() for path in repository_files}
    assert {"README.md", "config/default.yaml", "sql/08_price_waterfall.sql"}.issubset(names)


@pytest.mark.parametrize("name", FORBIDDEN_COMPANY_NAMES)
def test_no_real_company_names(repository_files: list[Path], name: str) -> None:
    pattern = re.compile(rf"(?<![A-Za-z]){re.escape(name)}(?![A-Za-z])")
    offenders = [
        str(path.name)
        for path in repository_files
        if pattern.search(path.read_text(encoding="utf-8", errors="ignore"))
    ]
    assert not offenders, f"{name!r} found in {offenders}"


@pytest.mark.parametrize("label", sorted(FORBIDDEN_PATTERNS))
def test_no_personal_contacts_paths_or_secrets(repository_files: list[Path], label: str) -> None:
    pattern = FORBIDDEN_PATTERNS[label]
    offenders = [
        path.name
        for path in repository_files
        if pattern.search(path.read_text(encoding="utf-8", errors="ignore"))
    ]
    assert not offenders, f"{label} found in {offenders}"


def test_readme_states_the_data_are_synthetic(project_root: Path) -> None:
    readme = (project_root / "README.md").read_text(encoding="utf-8").lower()
    assert "synthetic" in readme
    assert "no employer" in readme
