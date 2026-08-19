"""パーサが知っている地方大会名と、DBのマスタ(migrations)のズレを検出する。

    uv run pytest tests/test_master_data.py

1998夏(第80回記念大会)は埼玉・神奈川を**東西**で分割しており、
`normalize.QUALIFIER_TO_PREF` にはあるのに `summer_qualifiers` のシードには
北南しか無かった。結果 load で 4 entry(優勝校の横浜を含む)+ 13 試合が
未解決になった。片側だけ足して終わる事故を止めるためのテストなので、DBは触らない。
"""
import re
from pathlib import Path

from koshien.normalize import PREF_TO_REGION, QUALIFIER_TO_PREF

MIGRATIONS = Path(__file__).resolve().parents[1] / "supabase" / "migrations"

# 通常県の45枠は prefectures から select で生成されるためSQLにリテラルで現れない。
# 照合対象は分割枠(北北海道・東東京・東埼玉…)= 県名そのものでないキー。
SPLIT_QUALIFIERS = {q: p for q, p in QUALIFIER_TO_PREF.items() if q not in PREF_TO_REGION}


def _statements() -> list[str]:
    out = []
    for sql in sorted(MIGRATIONS.glob("*.sql")):
        out += re.split(r";\s*", sql.read_text(encoding="utf-8"))
    return out


def _seeded_prefecture_ids() -> dict[str, int]:
    """prefectures のシード行 `( 11,'埼玉', …)` から 県名 → JISコード を作る。"""
    ids = {}
    for stmt in _statements():
        if "insert into prefectures" not in stmt:
            continue
        for num, name in re.findall(r"\(\s*(\d+)\s*,\s*'([^']+)'", stmt):
            ids[name] = int(num)
    return ids


def _seeded_qualifiers() -> dict[str, int]:
    """summer_qualifiers のシードから リテラルの 枠名 → prefecture_id を作る。

    `('東埼玉', 11, '…')` と `select '北北海道', 1, '…'` の両形式に対応する。
    """
    quals = {}
    for stmt in _statements():
        if "insert into summer_qualifiers" not in stmt:
            continue
        for name, num in re.findall(r"'([^']+)'\s*,\s*(\d+)", stmt):
            quals[name] = int(num)
    return quals


def test_split_qualifiers_are_seeded():
    """分割枠がすべて migrations に入っていること(1998夏の欠落の再発防止)。"""
    missing = sorted(set(SPLIT_QUALIFIERS) - set(_seeded_qualifiers()))
    assert not missing, f"summer_qualifiers のシードに無い分割枠: {missing}"


def test_no_unknown_qualifier_in_migrations():
    """SQL 側に、パーサが解決できない枠名が無いこと(綴り違いの検出)。"""
    unknown = sorted(set(_seeded_qualifiers()) - set(SPLIT_QUALIFIERS))
    assert not unknown, f"QUALIFIER_TO_PREF に無い枠名: {unknown}"


def test_qualifier_prefecture_ids_match():
    """分割枠の prefecture_id が、対応する県のJISコードと一致すること。"""
    pref_ids = _seeded_prefecture_ids()
    bad = []
    for name, pref_id in _seeded_qualifiers().items():
        want = pref_ids.get(SPLIT_QUALIFIERS[name])
        if pref_id != want:
            bad.append(f"{name}: prefecture_id={pref_id}(期待 {want})")
    assert not bad, bad


if __name__ == "__main__":
    test_split_qualifiers_are_seeded()
    test_no_unknown_qualifier_in_migrations()
    test_qualifier_prefecture_ids_match()
    print("OK")
