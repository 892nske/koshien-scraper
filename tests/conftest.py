"""テスト実行前にフィクスチャHTMLが無ければ生成する。"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))


@pytest.fixture(scope="session", autouse=True)
def _ensure_fixtures():
    from make_fixtures import (
        build_1978,
        build_1978_real,
        build_1978_spring,
        build_2014,
        build_bracket_table_mix_summer,
        build_dupname_summer,
        build_episode_prose_summer,
        build_mixed_format_summer,
        build_spring_entries_table,
    )

    fix = Path(__file__).parent / "fixtures"
    if not (fix / "summer_2014.html").exists():
        build_2014()
    if not (fix / "summer_1978.html").exists():
        build_1978()
    if not (fix / "summer_1978_real.html").exists():
        build_1978_real()
    if not (fix / "spring_1978.html").exists():
        build_1978_spring()
    if not (fix / "summer_dupname.html").exists():
        build_dupname_summer()
    if not (fix / "summer_mixed.html").exists():
        build_mixed_format_summer()
    if not (fix / "summer_bracket_table.html").exists():
        build_bracket_table_mix_summer()
    if not (fix / "summer_episode.html").exists():
        build_episode_prose_summer()
    if not (fix / "spring_entries_table.html").exists():
        build_spring_entries_table()
