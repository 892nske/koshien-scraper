"""パーサの回帰テスト。フィクスチャに対して実行する。

    uv run python tests/make_fixtures.py
    uv run pytest
"""
from collections import Counter
from pathlib import Path

from koshien.normalize import normalize_school
from koshien.parse import parse_page
from koshien.validate import validate

FIX = Path(__file__).parent / "fixtures"
EXPECTED_ROUNDS = {"r1": 17, "r2": 16, "r3": 8, "qf": 4, "sf": 2, "f": 1}


def load(name, year):
    html = (FIX / name).read_text(encoding="utf-8")
    return parse_page(html, year, "summer", f"fixture{year}", 0)


def test_table_format():
    """表形式(2014年夏を模写): 出場校49・試合48・ラウンド構成が一致すること。"""
    td = load("summer_2014.html", 2014)
    assert len(td.entries) == 49, len(td.entries)
    assert len(td.games) == 48, len(td.games)
    assert Counter(g.round_code for g in td.games) == Counter(EXPECTED_ROUNDS)

    e = {x.school_name: x for x in td.entries}
    assert e["近江"].prefecture == "滋賀" and e["近江"].region == "近畿"
    assert e["佐久長聖"].prefecture == "長野" and e["佐久長聖"].region == "北信越"
    assert e["武修館"].summer_qualifier == "北北海道"
    assert e["武修館"].prefecture == "北海道"
    assert e["聖光学院"].appearance_no == 11 and e["聖光学院"].consecutive_no == 8
    assert all(not x.is_21st_century for x in td.entries)     # 夏なので必ずFalse

    final = [g for g in td.games if g.round_code == "f"][0]
    assert (final.winner_name, final.winner_score, final.loser_score) == ("大阪桐蔭", 4, 3)

    walkoff = [g for g in td.games if g.is_walkoff]
    assert len(walkoff) == 5, len(walkoff)
    assert all(g.first_bat_name == g.loser_name for g in walkoff)   # サヨナラ=勝者が後攻

    ext = [g for g in td.games if g.innings]
    assert {g.innings for g in ext} == {10, 11, 12}

    assert not [i for i in validate(td) if i.level == "error"]
    print("  OK: 表形式 (2014)")


def test_list_format():
    """箇条書き形式(1978年夏を模写): 見出しが無くてもラウンドを逆算できること。"""
    td = load("summer_1978.html", 1978)
    assert len(td.games) == 48, len(td.games)
    assert Counter(g.round_code for g in td.games) == Counter(EXPECTED_ROUNDS)

    first = td.games[0]
    assert (first.winner_name, first.loser_name, first.game_date) == ("天理", "松商学園", "08-07")

    ext17 = [g for g in td.games if g.innings == 17][0]
    assert ext17.winner_name == "仙台育英" and ext17.is_walkoff
    assert ext17.first_bat_name == "高松商"

    final = [g for g in td.games if g.round_code == "f"][0]
    assert final.winner_name == "PL学園" and final.innings == 12
    print("  OK: 箇条書き形式 (1978)")


def test_real_article_pitfalls():
    """実記事レイアウト(1978年夏)の地雷を踏まないこと。

      - 概要 infobox の行(優勝校/試合数/…)がダミー出場校として混入しない。
      - multicol ラッパの二重取りで出場校が重複しない。
      - 決勝がイニングスコア表だけ(ヘッダが2行目)でも拾えて no_final にならない。
    """
    td = load("summer_1978_real.html", 1978)

    # 出場校: 4校ちょうど、ダミー混入なし、全件 都道府県 解決
    assert len(td.entries) == 4, [e.school_name for e in td.entries]
    names = {e.school_name for e in td.entries}
    assert names == {"中京", "松商学園", "PL学園", "高知商"}, names
    junk = {"優勝校", "試合数", "選手宣誓", "始球式", "大会本塁打", "出場校",
            "テンプレートを表示"}
    assert not (names & junk)
    assert all(e.prefecture for e in td.entries)
    assert all(e.summer_qualifier for e in td.entries)   # 夏なので地方大会必須

    # 決勝はイニングスコアのみ。ヘッダ行が先頭でなくても拾えること
    finals = [g for g in td.games if g.round_code == "f"]
    assert len(finals) == 1, td.games
    assert finals[0].winner_name == "PL学園" and finals[0].first_bat_name == "高知商"

    # トーナメント構造として無矛盾(エラーゼロ)
    assert not [i for i in validate(td) if i.level == "error"], validate(td)
    print("  OK: 実記事レイアウト (1978)")


def test_normalize_school_aliases():
    """校名の名寄せ: 改称・脚注マーカーを吸収し、既存の接尾辞/括弧除去は不変。"""
    # 旧校名 → 現校名(明徳 → 明徳義塾)
    assert normalize_school("明徳") == normalize_school("明徳義塾")
    # 脚注マーカー [注釈N] / [N] を除去
    assert normalize_school("龍谷大平安[注釈4]") == normalize_school("龍谷大平安")
    assert normalize_school("高松商[注釈10]") == normalize_school("高松商")
    # 既存の接尾辞・括弧除去は不変
    assert normalize_school("大阪桐蔭高等学校") == normalize_school("大阪桐蔭")
    assert normalize_school("大阪桐蔭高") == normalize_school("大阪桐蔭")
    print("  OK: 校名の名寄せ")


def test_bracket_format():
    """トーナメント表 + 箇条書き出場校(1978年春を模写)。

      - 出場校が箇条書き(校名 （ 都道府県 、…))でも拾えて都道府県が解決する。
      - 試合結果が左右2枚のブラケットでも抽出でき、byes があっても
        ラウンド逆算・検証が通る。
      - 決勝がイニングスコアだけでも拾えて no_final にならない。
    """
    html = (FIX / "spring_1978.html").read_text(encoding="utf-8")
    td = parse_page(html, 1978, "spring", "fixture-spring", 0)

    # 出場校: 6校、全件 都道府県 解決、春なので地方大会は無い
    assert len(td.entries) == 6, [e.school_name for e in td.entries]
    assert all(e.prefecture for e in td.entries), td.entries
    assert all(e.summer_qualifier is None for e in td.entries)
    gunma = [e for e in td.entries if e.prefecture == "群馬"]
    assert {e.school_name for e in gunma} == {"桐生", "前橋"}   # 1県複数校

    # 試合: 6校なので5試合。決勝1試合(浜松商優勝)、無敗1校
    assert len(td.games) == 5, td.games
    final = [g for g in td.games if g.round_code == "f"]
    assert len(final) == 1 and final[0].winner_name == "浜松商", td.games

    # サヨナラ(スコア末尾 x)でもペアリングが崩れないこと。勝者が後攻なので先攻=敗者
    walkoff = [g for g in td.games if g.is_walkoff]
    assert len(walkoff) == 1, td.games
    assert walkoff[0].winner_name == "桐生" and walkoff[0].loser_name == "前橋"
    assert walkoff[0].first_bat_name == "前橋"

    # byes を含んでも検証エラーが出ないこと
    errs = [i for i in validate(td) if i.level == "error"]
    assert not errs, errs
    print("  OK: トーナメント表形式 (1978春)")


def test_duplicate_name_schools():
    """同名校が別県に存在(海星=三重/長崎)しても、県で区別して名寄せできること。"""
    html = (FIX / "summer_dupname.html").read_text(encoding="utf-8")
    td = parse_page(html, 1989, "summer", "fixture-dupname", 0)

    # 海星が三重・長崎の2校とも残る(校名だけで dedup しない)
    assert len(td.entries) == 16, [(e.school_name, e.prefecture) for e in td.entries]
    kaisei = {e.prefecture for e in td.entries if e.school_name == "海星"}
    assert kaisei == {"三重", "長崎"}, kaisei

    # 県込み照合で multi_loss / champion / dup_entries / game_count が出ないこと
    errs = [i for i in validate(td) if i.level == "error"]
    assert not errs, errs
    print("  OK: 同名校・別県の名寄せ")


def test_validation_catches_breakage():
    """試合を1件削れば検証がエラーを出すこと。"""
    td = load("summer_2014.html", 2014)
    td.games.pop()
    codes = {i.code for i in validate(td) if i.level == "error"}
    assert "game_count" in codes and "champion" in codes, codes
    print("  OK: 検証が欠損を検出")


if __name__ == "__main__":
    test_table_format()
    test_list_format()
    test_real_article_pitfalls()
    test_normalize_school_aliases()
    test_bracket_format()
    test_duplicate_name_schools()
    test_validation_catches_breakage()
    print("すべて通過")
