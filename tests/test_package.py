from __future__ import annotations

import sudoku_csp


def test_package_exposes_version() -> None:
    assert sudoku_csp.__version__ == "0.1.0"
