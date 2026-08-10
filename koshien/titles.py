"""年・季節 → 大会回次と、Wikipedia記事タイトルの候補生成。

回次の算出:
  夏 = 年 - 1918   (1978→第60回, 2014→第96回)
  春 = 年 - 1928   (1978→第50回, 2024→第96回)

記念大会は記事タイトルに「記念」が入るが、春夏で語順が異なる。
存在するタイトルはAPIで実際に引いて確定させるため、候補を列挙する方式をとる。
"""
from __future__ import annotations

SEASONS = ("spring", "summer")

# 中止・不開催の大会(本大会の試合が存在しない)
CANCELLED = {
    (2020, "spring"),   # 新型コロナで中止
    (2020, "summer"),   # 中止(甲子園高校野球交流試合は別大会として扱う)
}


def edition(year: int, season: str) -> int:
    if season == "summer":
        return year - 1918
    if season == "spring":
        return year - 1928
    raise ValueError(season)


def candidate_titles(year: int, season: str) -> list[str]:
    n = edition(year, season)
    if season == "summer":
        return [
            f"第{n}回全国高等学校野球選手権大会",
            f"第{n}回全国高等学校野球選手権記念大会",
        ]
    return [
        f"第{n}回選抜高等学校野球大会",
        f"第{n}回記念選抜高等学校野球大会",
        f"第{n}回選抜高等学校野球記念大会",
    ]


def iter_targets(start_year: int, end_year: int, seasons=SEASONS):
    """(year, season) を古い順に列挙する。中止大会は除外。"""
    for y in range(start_year, end_year + 1):
        for s in seasons:
            if (y, s) in CANCELLED:
                continue
            yield y, s
