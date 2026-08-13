"""HarnessProbe — reverse-engineer per-vendor benchmark-harness assumptions into a matched-score GapMatrix.

Public API:
    HarnessProfile   — pydantic schema for a vendor's reverse-engineered eval-harness assumptions.
    load_profile     — load a YAML HarnessProfile from disk (by vendor key).
    run_match        — run a profile against a benchmark subset, produce a MatchedRun.
    build_matrix     — assemble a GapMatrix from a set of MatchedRuns.
    render_report    — render the HTML matched-score report from a GapMatrix.
"""

from __future__ import annotations

from harnessprobe.profile import (
    HarnessProfile,
    ToolCallTemplate,
    ProfileError,
    load_profile,
    list_profiles,
    PROFILE_DIR,
)
from harnessprobe.runner import MatchedRun, run_match
from harnessprobe.matrix import GapMatrix, MatrixRow, build_matrix
from harnessprobe.report import render_report, export_repro_pkg

__version__ = "0.1.0"

__all__ = [
    "HarnessProfile",
    "ToolCallTemplate",
    "ProfileError",
    "load_profile",
    "list_profiles",
    "PROFILE_DIR",
    "MatchedRun",
    "run_match",
    "GapMatrix",
    "MatrixRow",
    "build_matrix",
    "render_report",
    "export_repro_pkg",
    "__version__",
]
