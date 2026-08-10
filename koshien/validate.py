"""パース結果の整合性検証。

スクレイピングは「取れたか」ではなく「正しいか」を機械的に確かめられるかが要。
甲子園はトーナメントなので、以下の性質から強い検証がかけられる。

  - 試合数 = 出場校数 - 1 (引き分け再試合は加算)
  - 敗戦は1校につき最大1回
  - 無敗の学校がちょうど1校(優勝校)
  - ラウンドごとの試合数が末尾から 1, 2, 4, 8, … になる
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .normalize import ROUND_CODES, normalize_school
from .parse import TournamentData


@dataclass
class Issue:
    level: str      # 'error' | 'warn'
    code: str
    detail: str


def validate(td: TournamentData) -> list[Issue]:
    issues: list[Issue] = []
    entry_keys = {normalize_school(e.school_name) for e in td.entries}

    # ---- 出場校 -------------------------------------------------------
    if not td.entries:
        issues.append(Issue("error", "no_entries", "出場校を1件も抽出できませんでした"))
    if len(td.entries) != len(entry_keys):
        issues.append(Issue("error", "dup_entries", "出場校に重複があります"))

    if td.season == "summer" and td.entries and not 47 <= len(td.entries) <= 60:
        issues.append(Issue("warn", "entry_count",
                            f"夏の出場校数が想定外です: {len(td.entries)}"))
    if td.season == "spring" and td.entries and not 28 <= len(td.entries) <= 40:
        issues.append(Issue("warn", "entry_count",
                            f"春の出場校数が想定外です: {len(td.entries)}"))

    for e in td.entries:
        if e.prefecture is None:
            issues.append(Issue("error", "no_prefecture",
                                f"都道府県が解決できません: {e.school_name}"))
        if td.season == "summer" and not e.summer_qualifier:
            issues.append(Issue("error", "no_qualifier",
                                f"夏なのに地方大会が空です: {e.school_name}"))
        if td.season == "spring" and e.summer_qualifier:
            issues.append(Issue("error", "spring_qualifier",
                                f"春なのに地方大会が入っています: {e.school_name}"))

    # ---- 試合 ---------------------------------------------------------
    if not td.games:
        issues.append(Issue("error", "no_games", "試合を1件も抽出できませんでした"))
        return issues

    replays = sum(1 for g in td.games if g.replay_seq > 0)
    expected = len(td.entries) - 1 + replays
    if td.entries and len(td.games) != expected:
        issues.append(Issue("error", "game_count",
                            f"試合数が合いません: 実際{len(td.games)} / 期待{expected}"))

    unknown = set()
    losses: Counter = Counter()
    wins: Counter = Counter()
    for g in td.games:
        for name in (g.winner_name, g.loser_name):
            k = normalize_school(name or "")
            if entry_keys and k not in entry_keys:
                unknown.add(name)
        if not g.is_draw:
            losses[normalize_school(g.loser_name or "")] += 1
            wins[normalize_school(g.winner_name or "")] += 1
    if unknown:
        issues.append(Issue("error", "unknown_school",
                            "出場校表に無い学校名: " + ", ".join(sorted(unknown)[:10])))

    for k, c in losses.items():
        if c > 1:
            issues.append(Issue("error", "multi_loss", f"{k} が {c} 敗しています"))

    if entry_keys:
        undefeated = entry_keys - set(losses)
        if len(undefeated) != 1:
            issues.append(Issue("error", "champion",
                                f"無敗の学校が{len(undefeated)}校です(1校であるべき)"))

    # ---- ラウンド -----------------------------------------------------
    by_round = Counter(g.round_code for g in td.games if g.replay_seq == 0)
    for i, code in enumerate(reversed(ROUND_CODES)):
        if code == "r1":
            break
        want = 2 ** i
        if by_round.get(code, 0) not in (0, want):
            issues.append(Issue("error", "round_count",
                                f"{code} の試合数が {by_round[code]}(期待 {want})"))
    if by_round.get("f", 0) != 1:
        issues.append(Issue("error", "no_final", "決勝が1試合ではありません"))

    return issues


def summarize(td: TournamentData, issues: list[Issue]) -> str:
    errs = [i for i in issues if i.level == "error"]
    warns = [i for i in issues if i.level == "warn"]
    mark = "NG" if errs else ("WARN" if warns else "OK")
    return (f"[{mark}] {td.year} {td.season}: "
            f"entries={len(td.entries)} games={len(td.games)} "
            f"errors={len(errs)} warns={len(warns)}")
