"""loader の名寄せ純関数の回帰テスト(DB 非依存)。

    uv run pytest tests/test_load.py

同名別県校(海星=三重/長崎)が同じ entry に潰れて games_distinct_teams_ck で
落ちた 1989夏の再発防止。build_entry_index / resolve_entry は DB を触らないので
ここで直接検証する。
"""
from koshien.load import build_entry_index, resolve_entry


def _kaisei_index():
    # (school_name, canonical_pref, entry_id)。entries 側は括弧なしの校名 + 県。
    return build_entry_index([
        ("海星", "三重", 100),
        ("海星", "長崎", 959),
        ("帝京", "東京", 200),
    ])


def test_dupname_resolves_to_distinct_entries():
    """海星(三重) と 海星(長崎) が別の entry_id に解決すること。"""
    idx = _kaisei_index()
    e1 = resolve_entry(idx, "海星(三重)")
    e2 = resolve_entry(idx, "海星(長崎)")
    assert e1 == 100, e1
    assert e2 == 959, e2
    assert e1 != e2
    print("  OK: 同名別県校が別 entry に解決")


def test_unique_name_without_paren():
    """括弧なしの一意な校名は従来どおり引けること。"""
    idx = _kaisei_index()
    assert resolve_entry(idx, "帝京") == 200


def test_ambiguous_without_paren_is_unresolved():
    """括弧なしで多義(海星)なら None(未解決)を返すこと。"""
    idx = _kaisei_index()
    assert resolve_entry(idx, "海星") is None


def test_paren_pref_without_match_is_unresolved():
    """県指定はあるが一致する候補が無ければ None を返すこと。"""
    idx = _kaisei_index()
    assert resolve_entry(idx, "海星(北海道)") is None


def test_unknown_name_is_unresolved():
    idx = _kaisei_index()
    assert resolve_entry(idx, "存在しない校") is None
    assert resolve_entry(idx, "") is None
