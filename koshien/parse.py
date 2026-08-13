"""Wikipedia記事HTML → 出場校 / 試合結果 の構造化。

甲子園の大会記事は年代によって書式が2系統ある。

  A. 表形式(概ね2000年代以降)
     | 試合日 | 試合順 | 勝利 | スコア | 敗戦 | 備考 | 試合時間 |

  B. 箇条書き形式(概ね1990年代以前)
     8月7日
     - 天理 6 - 0 松商学園
     - 仙台育英 1x - 0 高松商(延長17回)

どちらも「勝利校・敗戦校・スコア」であって先攻/後攻ではない点に注意。
サヨナラを示す x が付いた側が後攻と確定できるため、その場合のみ打順を復元する。
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from bs4 import BeautifulSoup, Tag

from .normalize import (
    LABEL_TO_CODE,
    ROUND_CODES,
    canonical_prefecture,
    normalize_school,
    normalize_text,
    parse_appearance,
    prefecture_to_region,
    qualifier_to_prefecture,
    round_code_from_label,
)

# --------------------------------------------------------------------------
# データクラス
# --------------------------------------------------------------------------


@dataclass
class EntryRow:
    school_name: str
    prefecture: str | None = None
    region: str | None = None
    summer_qualifier: str | None = None
    is_21st_century: bool = False
    appearance_no: int | None = None
    consecutive_no: int | None = None
    appearance_raw: str | None = None


@dataclass
class GameRow:
    round_code: str | None = None
    game_date: str | None = None          # 'MM-DD'
    day_no: int | None = None
    game_no: int | None = None
    winner_name: str | None = None
    loser_name: str | None = None
    winner_score: int | None = None
    loser_score: int | None = None
    is_draw: bool = False
    is_walkoff: bool = False
    first_bat_name: str | None = None     # 判明した場合のみ
    innings: int | None = None
    replay_seq: int = 0
    note: str | None = None
    raw: str | None = None


@dataclass
class TournamentData:
    year: int
    season: str
    title: str
    revid: int
    source_url: str
    entries: list[EntryRow] = field(default_factory=list)
    games: list[GameRow] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


# --------------------------------------------------------------------------
# HTMLテーブル → グリッド(rowspan/colspan展開)
# --------------------------------------------------------------------------

def table_to_grid(table: Tag) -> list[list[str]]:
    grid: list[list[str | None]] = []
    for r_idx, tr in enumerate(table.find_all("tr")):
        while len(grid) <= r_idx:
            grid.append([])
        row = grid[r_idx]
        c_idx = 0
        for cell in tr.find_all(["th", "td"], recursive=False):
            while c_idx < len(row) and row[c_idx] is not None:
                c_idx += 1
            text = normalize_text(cell.get_text(" ", strip=True))
            rs = int(cell.get("rowspan", 1) or 1)
            cs = int(cell.get("colspan", 1) or 1)
            for dr in range(rs):
                while len(grid) <= r_idx + dr:
                    grid.append([])
                target = grid[r_idx + dr]
                for dc in range(cs):
                    pos = c_idx + dc
                    while len(target) <= pos:
                        target.append(None)
                    target[pos] = text
            c_idx += cs
    return [[c if c is not None else "" for c in row] for row in grid]


# --------------------------------------------------------------------------
# 出場校テーブル
# --------------------------------------------------------------------------

_HEADER_FIELDS = {
    "qualifier": ("地方大会", "地区大会", "代表大会"),
    "region": ("地区", "ブロック"),
    "prefecture": ("都道府県", "所属", "県名"),
    "school": ("代表校", "出場校", "選出校", "学校名", "校名", "高校名"),
    "appearance": ("出場回数", "回数", "出場"),
    "selection": ("選出", "区分", "枠"),
}


def _classify_header(h: str) -> str | None:
    h = normalize_text(h)
    for fld, keys in _HEADER_FIELDS.items():
        for k in keys:
            if k in h:
                return fld
    return None


def _resolve_school_span(fields: list[str | None]) -> list[str | None]:
    """校名見出しが colspan=2 で校名列+都道府県列を覆う表を救う。

    近年の春(選抜)の出場校表は「選出校」見出しが colspan=2 で、実データは
    校名 + 都道府県 の2列。table_to_grid が colspan を複製するため school が
    2列続き、そのままでは都道府県列を school が上書きして県が解決できない。
    都道府県列が別に無い場合に限り、連続する school の2列目を prefecture とみなす。
    """
    if "prefecture" in fields:
        return fields
    out = list(fields)
    for i in range(1, len(out)):
        if out[i] == "school" and out[i - 1] == "school":
            out[i] = "prefecture"
    return out


def _detect_group(headers: list[str]) -> tuple[int, list[str | None]]:
    """1行に複数パネルが並ぶ表(例: 6列 = 3列×2)のグループ幅を推定する。"""
    fields = [_classify_header(h) for h in headers]
    n = len(fields)
    for g in range(1, n + 1):
        if n % g:
            continue
        if all(fields[i] == fields[i % g] for i in range(n)):
            if any(f is not None for f in fields[:g]):
                return g, _resolve_school_span(fields[:g])
    return n, _resolve_school_span(fields)


def _find_header_row(grid: list[list[str]], max_scan: int = 4) -> tuple[int, int, list]:
    """ヘッダ行を先頭数行から探す。

    実記事の出場校表は先頭行が「東日本 / 西日本」のような見出し行で、
    実際の列名はその次の行にあることが多い。先頭行決め打ちだと全滅する。
    戻り値: (ヘッダ行index, グループ幅, フィールド並び)
    """
    best = (-1, len(grid[0]) if grid else 1, [])
    best_score = 0
    for i, row in enumerate(grid[:max_scan]):
        group, fields = _detect_group(row)
        named = [f for f in fields if f]
        # school 単独の表(「記録」表の校名列など)は出場校表ではない。
        # 正規の出場校表は school + 地方大会/都道府県/出場回数 等を必ず持つ。
        if "school" not in named or len(set(named)) < 2:
            continue
        score = len(set(named))
        if score > best_score:
            best_score = score
            best = (i, group, fields)
    return best


# 出場校表ではありえないテーブル。概要 infobox は「出場校 / 優勝校 / 試合数 …」の
# 2列表で、「出場校」行が school 列と誤検出されると後続行がダミー出場校になる。
_SKIP_ENTRY_TABLE_CLASSES = frozenset(
    {"infobox", "navbox", "vertical-navbox", "navbox-inner", "ambox", "metadata"}
)


def parse_entries(soup: BeautifulSoup, season: str) -> list[EntryRow]:
    root = soup.select_one(".mw-parser-output") or soup
    entries: list[EntryRow] = []
    seen: set[tuple[str, str | None]] = set()

    for table in root.find_all("table"):
        # infobox/navbox は出場校表ではない。multicol 等のレイアウト用ラッパは
        # 中の実テーブルが find_all で別途拾われるため、ラッパ自身を解析すると
        # 二重取りになる(decompose ではなく continue で飛ばす — 子表を巻き込まない)。
        if _SKIP_ENTRY_TABLE_CLASSES.intersection(table.get("class") or ()):
            continue
        if table.find("table") is not None:
            continue

        grid = table_to_grid(table)
        if len(grid) < 2:
            continue
        header_idx, group, fields = _find_header_row(grid)
        if header_idx < 0:
            continue

        # 表の直前の見出しに21世紀枠の記載があるか
        heading_text = ""
        prev = table.find_previous(["h2", "h3", "h4", "caption", "p"])
        if prev:
            heading_text = normalize_text(prev.get_text(" ", strip=True))
        table_is_21c = "21世紀枠" in heading_text

        for row in grid[header_idx + 1:]:
            for start in range(0, len(row), group):
                chunk = row[start:start + group]
                rec: dict[str, str] = {}
                for f, v in zip(fields, chunk, strict=False):
                    if f:
                        rec[f] = v
                school = rec.get("school", "").strip()
                if not school or school in ("", "-", "―"):
                    continue
                if _classify_header(school) is not None:
                    continue          # ヘッダ行の繰り返し

                qualifier = rec.get("qualifier") or None
                pref = (canonical_prefecture(rec.get("prefecture", ""))
                        if rec.get("prefecture") else None)
                if pref is None and qualifier:
                    pref = qualifier_to_prefecture(qualifier)
                if pref is None and season == "summer":
                    pref = qualifier_to_prefecture(school)  # 保険
                region = prefecture_to_region(pref) if pref else None
                if region is None and rec.get("region"):
                    region = normalize_text(rec["region"]) or None

                app = parse_appearance(rec.get("appearance", ""))
                is21 = bool(
                    season == "spring"
                    and (table_is_21c or "21世紀枠" in rec.get("selection", ""))
                )

                # 同名校が別県に存在するので、県込みで重複判定する
                # (校名だけで dedup すると海星(三重)/海星(長崎)の片方が消える)
                key = (normalize_school(school), pref)
                if key in seen:
                    continue
                seen.add(key)

                entries.append(EntryRow(
                    school_name=school,
                    prefecture=pref,
                    region=region,
                    summer_qualifier=qualifier if season == "summer" else None,
                    is_21st_century=is21,
                    appearance_no=app["appearance_no"],
                    consecutive_no=app["consecutive_no"],
                    appearance_raw=rec.get("appearance") or None,
                ))

    if not entries:                     # 表が無い年(主に春)は箇条書きから拾う
        entries = _parse_entries_list(root, season)
    return entries


# 箇条書き出場校: '浜松商 （ 静岡 、14年ぶり4回目)' の 校名 / 都道府県 / 出場回数
_ENTRY_LI_RE = re.compile(
    r"^(?P<school>.+?)\s*[（(]\s*(?P<pref>[^、,]+?)\s*[、,]\s*(?P<rest>[^）)]*)"
)


def _parse_entries_list(root: Tag, season: str) -> list[EntryRow]:
    """出場校が箇条書き(校名 （ 都道府県 、出場回数))の年を拾う。

    表形式の parse_entries が0件だったときのフォールバック。春には地方大会が無いので
    summer_qualifier は常に None(spring_qualifier 検証に整合)。
    """
    heading = None
    for h in root.find_all(["h2", "h3"]):
        t = normalize_text(h.get_text(" ", strip=True))
        if "出場校" in t or "代表校" in t or "選出校" in t:
            heading = h
            break
    if heading is None:
        return []

    entries: list[EntryRow] = []
    seen: set[tuple[str, str | None]] = set()
    for sib in heading.find_all_next():
        if sib.name == "h2" and sib is not heading:   # 次の大セクションで打ち切り
            break
        if sib.name != "ul":
            continue
        for li in sib.find_all("li", recursive=False):
            m = _ENTRY_LI_RE.match(normalize_text(li.get_text(" ", strip=True)))
            if not m:
                continue
            school = m.group("school").strip()
            pref = canonical_prefecture(m.group("pref"))
            key = (normalize_school(school), pref)     # 同名校は県込みで区別
            if not school or key in seen:
                continue
            seen.add(key)
            entries.append(EntryRow(
                school_name=school,
                prefecture=pref,
                region=prefecture_to_region(pref) if pref else None,
                summer_qualifier=None,
                appearance_raw=(m.group("rest").strip() or None),
            ))
    return entries


# --------------------------------------------------------------------------
# 試合結果
# --------------------------------------------------------------------------

_SCORE_RE = re.compile(
    r"^(?P<w>.+?)\s*(?P<ws>\d+)(?P<wx>[xX])?\s*[-–—―－]\s*(?P<ls>\d+)(?P<lx>[xX])?\s*(?P<l>[^()（）]+)"
    r"(?:[（(](?P<note>[^)）]*)[)）])?\s*$"
)
_DATE_RE = re.compile(r"(\d{1,2})月(\d{1,2})日")
_DAY_RE = re.compile(r"第(\d+)日")
_GAME_NO_RE = re.compile(r"第(\d+)試合")
_INNING_RE = re.compile(r"延長(\d+)回")


def _score_pair(text: str) -> tuple[int, int, bool, bool] | None:
    """'6x - 5' → (6, 5, walkoff=True, winner_second_bat=True)"""
    t = normalize_text(text)
    m = re.match(r"^(\d+)([xX])?[-–—―－](\d+)([xX])?$", t)
    if not m:
        return None
    ws, wx, ls, lx = int(m.group(1)), bool(m.group(2)), int(m.group(3)), bool(m.group(4))
    return ws, ls, (wx or lx), wx


def parse_games_table(root: Tag) -> list[GameRow]:
    """表形式の試合結果を抽出する。"""
    games: list[GameRow] = []
    for table in root.find_all("table"):
        grid = table_to_grid(table)
        if not grid:
            continue
        # ヘッダ行は必ずしも先頭行ではない
        header_idx = -1
        headers: list[str] = []
        for i, row in enumerate(grid[:4]):
            cells = [normalize_text(h) for h in row]
            if any("勝利" in h for h in cells) and any("敗戦" in h for h in cells):
                header_idx, headers = i, cells
                break
        if header_idx < 0:
            continue

        idx = {}
        for i, h in enumerate(headers):
            if "試合日" in h or h == "日付":
                idx["date"] = i
            elif "試合順" in h:
                idx["order"] = i
            elif "勝利校" in h and "次戦" in h:
                continue
            elif "勝利" in h and "next" not in idx:
                idx.setdefault("winner", i)
            elif "スコア" in h or "得点" in h:
                idx["score"] = i
            elif "敗戦" in h:
                idx["loser"] = i
            elif "備考" in h:
                idx["note"] = i
        if not {"winner", "loser", "score"} <= idx.keys():
            continue

        # 表の直前の見出しからラウンドを推定
        rc = None
        prev = table.find_previous(["h2", "h3", "h4"])
        if prev:
            rc = round_code_from_label(prev.get_text(" ", strip=True))

        cur_date = None
        cur_day = None
        for row in grid[header_idx + 1:]:
            if len(row) <= max(idx.values()):
                continue
            if "date" in idx and row[idx["date"]]:
                dm = _DATE_RE.search(row[idx["date"]])
                if dm:
                    cur_date = f"{int(dm.group(1)):02d}-{int(dm.group(2)):02d}"
                dn = _DAY_RE.search(row[idx["date"]])
                cur_day = int(dn.group(1)) if dn else cur_day

            sp = _score_pair(row[idx["score"]])
            if sp is None:
                continue
            ws, ls, walkoff, winner_second = sp
            win_name = row[idx["winner"]].strip()
            lose_name = row[idx["loser"]].strip()
            if not win_name or not lose_name:
                continue
            note = row[idx["note"]] if "note" in idx and len(row) > idx["note"] else ""
            gm = _GAME_NO_RE.search(row[idx["order"]]) if "order" in idx else None
            im = _INNING_RE.search(note)

            games.append(GameRow(
                round_code=rc,
                game_date=cur_date,
                day_no=cur_day,
                game_no=int(gm.group(1)) if gm else None,
                winner_name=win_name, loser_name=lose_name,
                winner_score=ws, loser_score=ls,
                is_draw=(ws == ls),
                is_walkoff=walkoff,
                first_bat_name=(lose_name if winner_second else None),
                innings=int(im.group(1)) if im else None,
                note=note or None,
                raw=" ".join(row),
            ))
    return games


# 散文に埋め込まれたスコア(「…当初 市船橋 1-9 文徳と8点の大差…」等)を試合と
# 誤認しないための校名らしさ判定。実データの校名は最長9文字で、読点・句点を含まない。
_TEAM_MAX_LEN = 12


def _looks_like_team(name: str) -> bool:
    name = name.strip()
    return bool(name) and len(name) <= _TEAM_MAX_LEN and not any(c in name for c in "、。")


def parse_games_list(root: Tag) -> list[GameRow]:
    """箇条書き形式の試合結果を抽出する。"""
    games: list[GameRow] = []
    cur_round = None
    cur_date = None
    cur_day = None

    for node in root.find_all(["h2", "h3", "h4", "dt", "p", "b", "ul"]):
        if node.name in ("h2", "h3", "h4", "dt", "p", "b"):
            text = normalize_text(node.get_text(" ", strip=True))
            rc = round_code_from_label(text)
            if rc:
                cur_round = rc
            dm = _DATE_RE.search(text)
            if dm and len(text) <= 20:
                cur_date = f"{int(dm.group(1)):02d}-{int(dm.group(2)):02d}"
            dn = _DAY_RE.search(text)
            if dn:
                cur_day = int(dn.group(1))
            continue

        for li in node.find_all("li", recursive=False):
            text = normalize_text(li.get_text(" ", strip=True))
            m = _SCORE_RE.match(text)
            if not m:
                continue
            win, lose = m.group("w").strip(), m.group("l").strip()
            # 散文の埋め込みスコアは _SCORE_RE に誤マッチするが、勝者/敗者名が
            # 文章になる。校名らしくない側があれば試合として採用しない。
            if not (_looks_like_team(win) and _looks_like_team(lose)):
                continue
            ws, ls = int(m.group("ws")), int(m.group("ls"))
            wx, lx = bool(m.group("wx")), bool(m.group("lx"))
            note = m.group("note") or ""
            im = _INNING_RE.search(note) or _INNING_RE.search(text)
            games.append(GameRow(
                round_code=cur_round,
                game_date=cur_date,
                day_no=cur_day,
                winner_name=win,
                loser_name=lose,
                winner_score=ws, loser_score=ls,
                is_draw=(ws == ls),
                is_walkoff=(wx or lx),
                first_bat_name=(lose if wx else None),
                innings=int(im.group(1)) if im else None,
                note=note or None,
                raw=text,
            ))
    return games


def parse_linescores(root: Tag) -> list[GameRow]:
    """イニングスコア(スコアボード)形式の試合を抽出する。

    実記事では決勝(および一部の注目試合)が一覧表ではなく
    イニングごとの得点表で掲載されており、一覧表からは漏れる。

        | チーム | 1 | 2 | ... | 9 | 計 |
        | 三重   | 0 | 0 | ... | 0 | 3  |
        | 大阪桐蔭 | 1 | 0 | ... | X | 4  |

    先攻が上段という野球の記載慣習を利用し、打順もここから復元できる。
    """
    games: list[GameRow] = []
    for table in root.find_all("table"):
        grid = table_to_grid(table)
        if len(grid) < 3:
            continue

        # ヘッダ(1 2 3 … の列)は先頭行とは限らない。実記事の決勝スコアボードは
        # 1行目が「スコアボード」等のバナーで、列番号は2行目にあることが多い。
        header_idx = -1
        header: list[str] = []
        digit_cols: list[int] = []
        for i, row in enumerate(grid[:4]):
            cells = [normalize_text(c) for c in row]
            dcols = [j for j, c in enumerate(cells) if c.isdigit()]
            if len(dcols) >= 6 and [int(cells[j]) for j in dcols][:3] == [1, 2, 3]:
                header_idx, header, digit_cols = i, cells, dcols
                break
        if header_idx < 0:
            continue

        total_col = None
        for i, c in enumerate(header):
            if c in ("計", "R", "得点", "合計"):
                total_col = i
        if total_col is None:
            total_col = max(digit_cols) + 1
        if total_col >= len(header):
            continue

        rows = []
        for row in grid[header_idx + 1:]:
            if len(row) <= total_col:
                continue
            name = normalize_text(row[0])
            total = normalize_text(row[total_col])
            if not name or name.isdigit() or not total.isdigit():
                continue
            innings_cells = [normalize_text(row[i]) for i in digit_cols if i < len(row)]
            rows.append((name, int(total), innings_cells))
        if len(rows) < 2:
            continue

        rc = None
        prev = table.find_previous(["h2", "h3", "h4"])
        if prev:
            rc = round_code_from_label(prev.get_text(" ", strip=True))

        for a, b in zip(rows[::2], rows[1::2], strict=False):
            (n1, t1, _inn1), (n2, t2, _inn2) = a, b
            if t1 == t2:
                win, lose, ws, ls, draw = n1, n2, t1, t2, True
            elif t1 > t2:
                win, lose, ws, ls, draw = n1, n2, t1, t2, False
            else:
                win, lose, ws, ls, draw = n2, n1, t2, t1, False
            games.append(GameRow(
                round_code=rc,
                winner_name=win, loser_name=lose,
                winner_score=ws, loser_score=ls,
                is_draw=draw,
                is_walkoff=False,          # サヨナラ判定は一覧表/箇条書き側を優先
                first_bat_name=n1,          # 上段が先攻
                # 9イニングを超える列がある場合のみ延長と判断する
                innings=len(digit_cols) if len(digit_cols) > 9 else None,
                note="linescore",
                raw=f"{n1} {t1} - {t2} {n2}",
            ))
    return games


def _bracket_date_innings(label: str | None) -> tuple[str | None, int | None]:
    """ブラケットの日付セル(例: '3月27日(1):延長13回')から日付と延長回を取る。"""
    if not label:
        return None, None
    innings = None
    m = re.search(r"延長\s*(\d+)\s*回", label)
    if m:
        innings = int(m.group(1))
    md = re.search(r"(\d+)\s*月\s*(\d+)\s*日", label)
    gdate = f"{int(md.group(1)):02d}-{int(md.group(2)):02d}" if md else None
    return gdate, innings


_BRACKET_SCORE_RE = re.compile(r"^(\d+)([xX])?$")   # 末尾 x = サヨナラ(勝者=後攻)


def parse_bracket(root: Tag) -> list[GameRow]:
    """トーナメント表(ブラケット)形式の試合を抽出する。

    主に春(選抜)記事。左右2枚の表に、各ラウンドが「名前列 + スコア列」の対で並ぶ。
    試合は連続2行(勝敗校名 + スコア)。日付は両列にまたがる colspan 行、値は rowspan で
    複数行に複製される。掲載順が先攻/後攻を表すわけではないので打順は復元しない。

    ラウンドはラベルを直訳せず round_code=None のまま返し、`assign_rounds_by_bracket`
    に構造から逆算させる(byes のある代表数だとラベル直訳では検証が通らないため)。
    返す試合はラウンド昇順(1回戦→決勝)に整列する(逆算は末尾から数えるため)。
    """
    collected: list[tuple[str, GameRow]] = []      # (round_code, game)
    for table in root.find_all("table"):
        grid = table_to_grid(table)
        if len(grid) < 2:
            continue
        header = [normalize_text(c) for c in grid[0]]
        # ラウンドラベルが colspan ペア(名前列/スコア列)で並ぶ列を拾う
        round_cols: list[tuple[int, int, str]] = []
        seen_labels: set[str] = set()
        for j, c in enumerate(header):
            if (c in LABEL_TO_CODE and c not in seen_labels
                    and j + 1 < len(header) and header[j + 1] == c):
                seen_labels.add(c)
                round_cols.append((j, j + 1, LABEL_TO_CODE[c]))
        if len(round_cols) < 2:                    # ブラケットは複数ラウンドが列で並ぶ
            continue

        for name_col, score_col, code in round_cols:
            teams: list[tuple[str, int, bool, str | None]] = []  # (校名,得点,サヨナラ,日付)
            pending_date: str | None = None
            prev: tuple[str, str] | None = None
            for r in range(1, len(grid)):
                row = grid[r]
                name = normalize_text(row[name_col]) if name_col < len(row) else ""
                score = normalize_text(row[score_col]) if score_col < len(row) else ""
                if not name and not score:
                    continue
                if name and name == score:         # 日付など colspan 行 → ブロック境界
                    pending_date = name
                    prev = None
                    continue
                m = _BRACKET_SCORE_RE.match(score)   # 末尾 x(サヨナラ)も許容する
                if not name or not m:
                    continue
                if prev == (name, score):          # rowspan による複製
                    continue
                prev = (name, score)
                teams.append((name, int(m.group(1)), bool(m.group(2)), pending_date))

            for k in range(0, len(teams) - 1, 2):  # 連続2件で1試合
                (n1, s1, x1, d1), (n2, s2, x2, _d2) = teams[k], teams[k + 1]
                if s1 >= s2:
                    win, ws, lose, ls = n1, s1, n2, s2
                else:
                    win, ws, lose, ls = n2, s2, n1, s1
                walkoff = x1 or x2                 # x は勝者=後攻に付く
                gdate, innings = _bracket_date_innings(d1)
                collected.append((code, GameRow(
                    round_code=None,               # 構造から逆算させる
                    game_date=gdate,
                    winner_name=win, winner_score=ws,
                    loser_name=lose, loser_score=ls,
                    is_walkoff=walkoff,
                    first_bat_name=lose if walkoff else None,   # サヨナラ=先攻は敗者
                    innings=innings,
                    note="bracket",
                    raw=f"{n1} {s1} - {s2} {n2}",
                )))

    # 末尾から逆算できるようラウンド昇順に整列(ラベルのランクのみ利用)
    rank = {c: i for i, c in enumerate(ROUND_CODES)}
    collected.sort(key=lambda x: rank.get(x[0], len(ROUND_CODES)))
    return [g for _, g in collected]


def _pair_key(g: GameRow) -> frozenset:
    return frozenset({normalize_school(g.winner_name or ""),
                      normalize_school(g.loser_name or "")})


def _result_sig(g: GameRow) -> tuple:
    """試合の結果指紋。引き分けは勝敗の向きが任意なのでスコアは集合で持つ。

    同一カードの2試合(引き分け決勝 + 決勝再試合)を、再試合か単なる再パースの
    重複かで区別するために使う。スコアと引き分けフラグが同じなら同一試合とみなす。
    """
    return (frozenset({g.winner_score, g.loser_score}), g.is_draw)


def parse_games(soup: BeautifulSoup) -> list[GameRow]:
    root = soup.select_one(".mw-parser-output") or soup
    games: list[GameRow] = []
    known: set[frozenset] = set()

    def _add(cands: list[GameRow], require_round: bool = False) -> None:
        for g in cands:
            # 概要節の説明文は _SCORE_RE に誤マッチするが round_code=None。
            # 箇条書きが補助のときはこれらを除外する。
            if require_round and not g.round_code:
                continue
            key = _pair_key(g)
            if key not in known:
                games.append(g)
                known.add(key)

    # 同じ大会で書式が混在する年があるため全ソースを統合する。
    # ブラケット(早いラウンド, round_code=None)を先に、次に表(遅いラウンド)を足すと、
    # 末尾から逆算する assign_rounds_by_bracket 用のラウンド昇順が保たれる。
    _add(parse_bracket(root))
    _add(parse_games_table(root))
    # 箇条書き: 主データ(まだ試合が乏しい)なら全件、補助データなら round 見出し配下のみ。
    _add(parse_games_list(root), require_round=len(games) >= 10)

    # 一覧表/箇条書きから漏れた試合(主に決勝)をスコアボードから補完する
    for g in parse_linescores(root):
        key = _pair_key(g)
        same_pair = [e for e in games if _pair_key(e) == key]
        if not same_pair:
            games.append(g)
            known.add(key)
        elif all(_result_sig(e) != _result_sig(g) for e in same_pair):
            # 同一カードでも結果(スコア/引き分け)が違えば別試合 = 引き分け再試合。
            # known は据え置き。後段の mark_replays が replay_seq を振る。
            games.append(g)
        else:
            # 同一試合の別ソース再パース。打順が未判明なら補完する。
            for e in same_pair:
                if e.first_bat_name is None:
                    e.first_bat_name = g.first_bat_name
                    break

    games = mark_replays(games)
    if any(g.round_code is None for g in games):
        games = assign_rounds_by_bracket(games)
    return games


# --------------------------------------------------------------------------
# ラウンド推定と再試合
# --------------------------------------------------------------------------

def mark_replays(games: list[GameRow]) -> list[GameRow]:
    """同一カードが連続する場合、後の方を再試合として印を付ける。"""
    seen: dict[frozenset, int] = {}
    for g in games:
        key = frozenset({normalize_school(g.winner_name or ""),
                         normalize_school(g.loser_name or "")})
        if key in seen:
            seen[key] += 1
            g.replay_seq = seen[key]
        else:
            seen[key] = 0
    return games


def assign_rounds_by_bracket(games: list[GameRow]) -> list[GameRow]:
    """トーナメント構造からラウンドを逆算する。

    決勝1試合・準決勝2試合・準々決勝4試合…と末尾から割り当て、
    残りを1回戦とする。引き分け再試合は同じ枠として1つに数える。
    """
    slots: list[list[GameRow]] = []
    for g in games:
        if g.replay_seq > 0 and slots:
            slots[-1].append(g)
        else:
            slots.append([g])

    codes_desc = list(reversed(ROUND_CODES))     # f, sf, qf, r3, r2, r1
    i = len(slots)
    for depth, code in enumerate(codes_desc):
        size = 2 ** depth
        # 残りが1階層(2**depth)を満たさない場合、それは byes を含む初回=r1。
        # 例: 30代表は末尾から f1・sf2・qf4・(2回戦)8 のあと 14 が残るが、これは
        # r2枠(16)に詰めず r1 に集約する(でないと round_count が合わない)。
        if code == "r1" or size >= i:
            code, size = "r1", i                  # 残り全部を1回戦に
        start = max(i - size, 0)
        for slot in slots[start:i]:
            for g in slot:
                g.round_code = code
        i = start
        if i <= 0:
            break
    return games


# --------------------------------------------------------------------------
# エントリポイント
# --------------------------------------------------------------------------

def parse_page(html: str, year: int, season: str, title: str, revid: int) -> TournamentData:
    soup = BeautifulSoup(html, "lxml")
    return TournamentData(
        year=year,
        season=season,
        title=title,
        revid=revid,
        source_url=f"https://ja.wikipedia.org/wiki/{title}?oldid={revid}",
        entries=parse_entries(soup, season),
        games=parse_games(soup),
    )
