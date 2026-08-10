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
    "school": ("代表校", "出場校", "学校名", "校名", "高校名"),
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


def _detect_group(headers: list[str]) -> tuple[int, list[str | None]]:
    """1行に複数パネルが並ぶ表(例: 6列 = 3列×2)のグループ幅を推定する。"""
    fields = [_classify_header(h) for h in headers]
    n = len(fields)
    for g in range(1, n + 1):
        if n % g:
            continue
        if all(fields[i] == fields[i % g] for i in range(n)):
            if any(f is not None for f in fields[:g]):
                return g, fields[:g]
    return n, fields


def parse_entries(soup: BeautifulSoup, season: str) -> list[EntryRow]:
    root = soup.select_one(".mw-parser-output") or soup
    entries: list[EntryRow] = []
    seen: set[str] = set()

    for table in root.find_all("table"):
        grid = table_to_grid(table)
        if len(grid) < 2:
            continue
        headers = grid[0]
        group, fields = _detect_group(headers)
        if "school" not in [f for f in fields if f]:
            continue

        # 表の直前の見出しに21世紀枠の記載があるか
        heading_text = ""
        prev = table.find_previous(["h2", "h3", "h4", "caption", "p"])
        if prev:
            heading_text = normalize_text(prev.get_text(" ", strip=True))
        table_is_21c = "21世紀枠" in heading_text

        for row in grid[1:]:
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

                key = normalize_school(school)
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
        headers = [normalize_text(h) for h in grid[0]]
        if not any("勝利" in h for h in headers) or not any("敗戦" in h for h in headers):
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
        for row in grid[1:]:
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
            ws, ls = int(m.group("ws")), int(m.group("ls"))
            wx, lx = bool(m.group("wx")), bool(m.group("lx"))
            note = m.group("note") or ""
            im = _INNING_RE.search(note) or _INNING_RE.search(text)
            games.append(GameRow(
                round_code=cur_round,
                game_date=cur_date,
                day_no=cur_day,
                winner_name=m.group("w").strip(),
                loser_name=m.group("l").strip(),
                winner_score=ws, loser_score=ls,
                is_draw=(ws == ls),
                is_walkoff=(wx or lx),
                first_bat_name=(m.group("l").strip() if wx else None),
                innings=int(im.group(1)) if im else None,
                note=note or None,
                raw=text,
            ))
    return games


def parse_games(soup: BeautifulSoup) -> list[GameRow]:
    root = soup.select_one(".mw-parser-output") or soup
    games = parse_games_table(root)
    if len(games) < 10:                 # 表が無ければ箇条書き形式とみなす
        games = parse_games_list(root)
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
        if code == "r1":
            size = i                              # 残り全部
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
