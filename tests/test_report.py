"""Tests for the HTML report renderer and repro-pkg exporter."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from harnessprobe.matrix import GapMatrix, MatrixRow, build_matrix
from harnessprobe.profile import load_profile
from harnessprobe.report import export_repro_pkg, render_report
from harnessprobe.runner import MatchedRun, run_match


@pytest.fixture()
def runs_and_matrix():
    runs = [run_match(load_profile(k), n=6) for k in ["deepseek-v4", "qwen3-8", "kimi-k3"]]
    m = build_matrix(runs)
    return runs, m


class TestRenderReport:
    def test_renders_html(self, runs_and_matrix) -> None:
        runs, m = runs_and_matrix
        html = render_report(m, runs)
        assert html.startswith("<!DOCTYPE html>")
        assert "GapMatrix" in html
        assert "AIME" in html

    def test_writes_to_file(self, runs_and_matrix, tmp_path: Path) -> None:
        runs, m = runs_and_matrix
        out = tmp_path / "report.html"
        render_report(m, runs, out=out)
        assert out.exists()
        text = out.read_text()
        assert "DeepSeek" in text or "deepseek" in text
        assert "<table" in text

    def test_contains_all_vendors(self, runs_and_matrix) -> None:
        runs, m = runs_and_matrix
        html = render_report(m, runs)
        for v in ("deepseek", "qwen", "kimi"):
            assert v in html

    def test_stub_banner_when_all_stub(self, runs_and_matrix) -> None:
        runs, m = runs_and_matrix
        html = render_report(m, runs)
        assert "STUB" in html

    def test_contains_provenance(self, runs_and_matrix) -> None:
        runs, m = runs_and_matrix
        html = render_report(m, runs)
        assert "provenance" in html.lower()

    def test_renders_without_runs(self) -> None:
        rows = [MatrixRow("deepseek", "m", 79.8, 70.0, 7, 10, -9.8, True)]
        m = GapMatrix(bench="aime", rows=rows, n_problems=10)
        html = render_report(m, runs=None)
        assert "deepseek" in html


class TestReproPkg:
    def test_exports_zip(self, runs_and_matrix, tmp_path: Path) -> None:
        runs, m = runs_and_matrix
        out = tmp_path / "repro.zip"
        path = export_repro_pkg(runs, m, out=out)
        assert path.exists()
        assert path.suffix == ".zip"

    def test_zip_contains_manifest(self, runs_and_matrix, tmp_path: Path) -> None:
        runs, m = runs_and_matrix
        out = tmp_path / "repro.zip"
        export_repro_pkg(runs, m, out=out)
        with zipfile.ZipFile(out) as zf:
            names = zf.namelist()
            assert "manifest.json" in names
            manifest = json.loads(zf.read("manifest.json"))
            assert manifest["tool"] == "harnessprobe"
            assert manifest["bench"] == "aime"
            assert len(manifest["models"]) == 3
            assert "matrix" in manifest

    def test_zip_contains_profiles_and_responses(self, runs_and_matrix, tmp_path: Path) -> None:
        runs, m = runs_and_matrix
        out = tmp_path / "repro.zip"
        export_repro_pkg(runs, m, out=out)
        with zipfile.ZipFile(out) as zf:
            names = zf.namelist()
            # profile + results + prompts + responses per model
            assert any("profile.txt" in n for n in names)
            assert any("results.json" in n for n in names)
            assert any("prompts/" in n for n in names)
            assert any("responses/" in n for n in names)

    def test_zip_results_have_correct_count(self, runs_and_matrix, tmp_path: Path) -> None:
        runs, m = runs_and_matrix
        out = tmp_path / "repro.zip"
        export_repro_pkg(runs, m, out=out)
        with zipfile.ZipFile(out) as zf:
            for name in zf.namelist():
                if name.endswith("results.json"):
                    data = json.loads(zf.read(name))
                    assert len(data["results"]) == 6
                    break
            else:
                pytest.fail("no results.json found in zip")
