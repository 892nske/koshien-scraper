"""パース済みJSON → PostgreSQL(Supabase) への冪等な取り込み。

すべて自然キーに対する UPSERT で書くため、何度実行しても結果は同じになる。
学校の名寄せは schools / school_aliases を正規化キーで引き当て、
見つからない場合は --auto-create-schools 指定時のみ新規作成する。
"""
from __future__ import annotations

import json
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from .normalize import canonical_prefecture, normalize_school, split_school_pref
from .parse import EntryRow, GameRow, TournamentData

# 校名(正規化)→ [(canonical_pref, entry_id), ...]。同名別県校を県で区別するための索引。
EntryIndex = dict[str, list[tuple[str | None, int]]]


def build_entry_index(rows: list[tuple[str, str | None, int]]) -> EntryIndex:
    """(school_name, canonical_pref, entry_id) の並びから校名+県の索引を作る。

    校名だけでキー化すると同名別県校(海星=三重/長崎)が潰れるため、
    正規化校名をキーに、県付き候補のリストを値に持つ。
    """
    index: EntryIndex = {}
    for name, pref, eid in rows:
        index.setdefault(normalize_school(name), []).append((pref, eid))
    return index


def resolve_entry(index: EntryIndex, name: str) -> int | None:
    """試合側の校名(例 '海星(三重)')から entry_id を引く。

    括弧内に県があればそれで一意化する。括弧なしで候補が複数あるときは
    あいまいなので None を返す(未解決として扱う)。
    """
    key, pref = split_school_pref(name or "")
    cands = index.get(key, [])
    if pref is not None:
        for p, eid in cands:
            if p == pref:
                return eid
        return None
    if len(cands) == 1:
        return cands[0][1]
    return None


class Loader:
    def __init__(self, dsn: str, auto_create_schools: bool = False, dry_run: bool = False):
        self.conn = psycopg.connect(dsn, row_factory=dict_row)
        self.auto_create = auto_create_schools
        self.dry_run = dry_run
        self._pref_cache: dict[str, int] = {}
        self._region_cache: dict[str, int] = {}
        self._qual_cache: dict[str, int] = {}
        self._school_cache: dict[tuple[str, int], int] = {}
        self.unresolved: list[str] = []

    # ------------------------------------------------------------------
    def _lookup(self, cache: dict, table: str, name: str) -> int | None:
        if name in cache:
            return cache[name]
        with self.conn.cursor() as cur:
            cur.execute(f"select id from {table} where name = %s", (name,))
            row = cur.fetchone()
        if row:
            cache[name] = row["id"]
            return row["id"]
        return None

    def prefecture_id(self, name: str) -> int | None:
        return self._lookup(self._pref_cache, "prefectures", name)

    def region_id(self, name: str) -> int | None:
        return self._lookup(self._region_cache, "regions", name)

    def qualifier_id(self, name: str) -> int | None:
        return self._lookup(self._qual_cache, "summer_qualifiers", name)

    # ------------------------------------------------------------------
    def resolve_school(self, name: str, prefecture_id: int) -> int | None:
        """校名 + 都道府県 から school_id を引く。別名テーブルも参照する。"""
        key = normalize_school(name)
        ck = (key, prefecture_id)
        if ck in self._school_cache:
            return self._school_cache[ck]

        with self.conn.cursor() as cur:
            cur.execute(
                """
                select s.id
                from schools s
                left join school_aliases a on a.school_id = s.id
                where s.prefecture_id = %s
                  and (%s = any(array[s.name]) or a.alias = %s
                       or s.name = %s or a.alias = %s)
                limit 1
                """,
                (prefecture_id, name, name, key, key),
            )
            row = cur.fetchone()
            if not row:
                # 正規化キーでの照合(接尾辞ゆらぎ吸収)
                cur.execute(
                    "select id, name from schools where prefecture_id = %s", (prefecture_id,)
                )
                for r in cur.fetchall():
                    if normalize_school(r["name"]) == key:
                        row = {"id": r["id"]}
                        break

            if not row:
                if not self.auto_create:
                    self.unresolved.append(f"{name}(pref_id={prefecture_id})")
                    return None
                cur.execute(
                    """insert into schools (name, prefecture_id) values (%s, %s)
                       on conflict (name, prefecture_id) do update set name = excluded.name
                       returning id""",
                    (key, prefecture_id),
                )
                row = cur.fetchone()
                cur.execute(
                    """insert into school_aliases (school_id, alias, kind)
                       values (%s, %s, 'source_label') on conflict do nothing""",
                    (row["id"], name),
                )

        self._school_cache[ck] = row["id"]
        return row["id"]

    # ------------------------------------------------------------------
    def upsert_tournament(self, td: TournamentData) -> int:
        from .titles import edition
        with self.conn.cursor() as cur:
            cur.execute(
                """
                insert into tournaments (year, season, edition, is_memorial, team_count)
                values (%s, %s, %s, %s, %s)
                on conflict (year, season) do update
                  set edition = excluded.edition,
                      is_memorial = excluded.is_memorial,
                      team_count = excluded.team_count,
                      updated_at = now()
                returning id
                """,
                (td.year, td.season, edition(td.year, td.season),
                 "記念" in td.title, len(td.entries)),
            )
            return cur.fetchone()["id"]

    def upsert_entry(self, tid: int, td: TournamentData, e: EntryRow) -> int | None:
        pref = self.prefecture_id(e.prefecture) if e.prefecture else None
        region = self.region_id(e.region) if e.region else None
        if pref is None or region is None:
            self.unresolved.append(f"pref/region未解決: {e.school_name}")
            return None
        school = self.resolve_school(e.school_name, pref)
        if school is None:
            return None
        qual = self.qualifier_id(e.summer_qualifier) if e.summer_qualifier else None
        if td.season == "summer" and qual is None:
            self.unresolved.append(f"地方大会未解決: {e.summer_qualifier}")
            return None

        with self.conn.cursor() as cur:
            cur.execute(
                """
                insert into entries (tournament_id, season, school_id, name_at_time,
                                     prefecture_id, region_id, summer_qualifier_id,
                                     is_21st_century, appearance_no, consecutive_no,
                                     source_url, scraped_at)
                values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, now())
                on conflict (tournament_id, school_id) do update
                  set name_at_time = excluded.name_at_time,
                      prefecture_id = excluded.prefecture_id,
                      region_id = excluded.region_id,
                      summer_qualifier_id = excluded.summer_qualifier_id,
                      is_21st_century = excluded.is_21st_century,
                      appearance_no = excluded.appearance_no,
                      consecutive_no = excluded.consecutive_no,
                      source_url = excluded.source_url,
                      scraped_at = now(),
                      updated_at = now()
                returning id
                """,
                (tid, td.season, school, e.school_name, pref, region, qual,
                 e.is_21st_century, e.appearance_no, e.consecutive_no, td.source_url),
            )
            return cur.fetchone()["id"]

    def upsert_game(self, tid: int, td: TournamentData, g: GameRow,
                    index: EntryIndex) -> bool:
        """1試合を UPSERT する。学校を解決できず投入しなかった場合は False。"""
        e1 = resolve_entry(index, g.winner_name or "")
        e2 = resolve_entry(index, g.loser_name or "")
        if e1 is None or e2 is None:
            self.unresolved.append(f"試合の学校未解決: {g.raw}")
            return False
        if e1 == e2:
            # 同名別県校の区別に失敗している。CHECK 制約で落ちる前に検知する。
            self.unresolved.append(f"試合の学校が同一に解決: {g.raw}")
            return False

        first_bat = None
        if g.first_bat_name:
            first_bat = resolve_entry(index, g.first_bat_name)
        status = "draw" if g.is_draw else ("forfeit" if g.is_forfeit else "final")
        winner = None if g.is_draw else e1     # 不戦勝は進出校(=winner_name=e1)が勝者
        game_date = f"{td.year}-{g.game_date}" if g.game_date else None

        with self.conn.cursor() as cur:
            cur.execute(
                """
                insert into games (tournament_id, round_code, day_no, game_no, game_date,
                                   entry1_id, entry2_id, score1, score2, innings,
                                   winner_entry_id, first_bat_entry_id, is_walkoff,
                                   status, replay_seq, note, source_url, scraped_at)
                values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, now())
                on conflict (tournament_id, round_code, pair_lo, pair_hi, replay_seq)
                do update set
                    score1 = excluded.score1, score2 = excluded.score2,
                    innings = excluded.innings,
                    winner_entry_id = excluded.winner_entry_id,
                    first_bat_entry_id = excluded.first_bat_entry_id,
                    is_walkoff = excluded.is_walkoff,
                    status = excluded.status,
                    game_date = excluded.game_date,
                    note = excluded.note, source_url = excluded.source_url,
                    scraped_at = now(), updated_at = now()
                """,
                (tid, g.round_code, g.day_no, g.game_no, game_date,
                 e1, e2, g.winner_score, g.loser_score, g.innings,
                 winner, first_bat, g.is_walkoff, status, g.replay_seq,
                 g.note, td.source_url),
            )
        return True

    # ------------------------------------------------------------------
    def load(self, td: TournamentData) -> dict:
        tid = self.upsert_tournament(td)
        index_rows: list[tuple[str, str | None, int]] = []
        for e in td.entries:
            eid = self.upsert_entry(tid, td, e)
            if eid:
                pref = canonical_prefecture(e.prefecture) if e.prefecture else None
                index_rows.append((e.school_name, pref, eid))
        index = build_entry_index(index_rows)
        games = sum(self.upsert_game(tid, td, g, index) for g in td.games)

        if self.dry_run:
            self.conn.rollback()
        else:
            self.conn.commit()
        # entries / games は**投入できた数**。総数と並べて返さないと、
        # マスタ不足で entry が捨てられていること自体に気づけない
        # (1998夏は summer_qualifiers に東埼玉等が無く 55 → 51 になっていた)。
        return {"tournament_id": tid,
                "entries": len(index_rows), "entry_total": len(td.entries),
                "games": games, "game_total": len(td.games),
                "unresolved": len(self.unresolved), "details": list(self.unresolved)}


def load_file(path: str | Path, dsn: str, **kw) -> dict:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    td = TournamentData(
        year=d["year"], season=d["season"], title=d["title"], revid=d["revid"],
        source_url=d["source_url"],
        entries=[EntryRow(**e) for e in d["entries"]],
        games=[GameRow(**g) for g in d["games"]],
    )
    loader = Loader(dsn, **kw)
    return loader.load(td)
