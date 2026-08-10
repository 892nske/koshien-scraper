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

from .normalize import normalize_school
from .parse import EntryRow, GameRow, TournamentData


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
                    entry_by_name: dict[str, int]) -> None:
        e1 = entry_by_name.get(normalize_school(g.winner_name or ""))
        e2 = entry_by_name.get(normalize_school(g.loser_name or ""))
        if e1 is None or e2 is None:
            self.unresolved.append(f"試合の学校未解決: {g.raw}")
            return

        first_bat = None
        if g.first_bat_name:
            first_bat = entry_by_name.get(normalize_school(g.first_bat_name))
        status = "draw" if g.is_draw else "final"
        winner = None if g.is_draw else e1
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

    # ------------------------------------------------------------------
    def load(self, td: TournamentData) -> dict:
        tid = self.upsert_tournament(td)
        entry_by_name: dict[str, int] = {}
        for e in td.entries:
            eid = self.upsert_entry(tid, td, e)
            if eid:
                entry_by_name[normalize_school(e.school_name)] = eid
        for g in td.games:
            self.upsert_game(tid, td, g, entry_by_name)

        if self.dry_run:
            self.conn.rollback()
        else:
            self.conn.commit()
        return {"tournament_id": tid, "entries": len(entry_by_name),
                "games": len(td.games), "unresolved": len(self.unresolved)}


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
