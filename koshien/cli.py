"""koshien-scraper のコマンドラインインタフェース。

    python -m koshien.cli fetch    --from 1978 --to 2025
    python -m koshien.cli parse    --from 1978 --to 2025
    python -m koshien.cli validate --from 1978 --to 2025
    python -m koshien.cli load     --from 1978 --to 2025 --dsn "$SUPABASE_DSN"
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from .parse import EntryRow, GameRow, TournamentData, parse_page
from .titles import candidate_titles, iter_targets
from .validate import summarize, validate
from .wiki import WikiClient

PARSED_DIR = Path("data/parsed")


def _slug(year: int, season: str) -> str:
    return f"{season}_{year}"


def cmd_fetch(args) -> int:
    client = WikiClient(cache_dir=args.cache, min_interval=args.interval)
    missing = []
    for year, season in iter_targets(args.start, args.end, args.seasons):
        page = client.get_first_existing(candidate_titles(year, season))
        if page is None:
            missing.append((year, season))
            print(f"  [MISS] {year} {season}")
        else:
            print(f"  [ok]   {year} {season}: {page.title} (rev {page.revid})")
    if missing:
        print(f"\n記事が見つからなかった大会: {missing}", file=sys.stderr)
    return 0


def cmd_parse(args) -> int:
    client = WikiClient(cache_dir=args.cache, min_interval=args.interval)
    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    ng = 0
    for year, season in iter_targets(args.start, args.end, args.seasons):
        page = client.get_first_existing(candidate_titles(year, season))
        if page is None:
            print(f"  [MISS] {year} {season}")
            ng += 1
            continue
        td = parse_page(page.html, year, season, page.title, page.revid)
        issues = validate(td)
        print(" ", summarize(td, issues))
        for i in issues:
            if i.level == "error" or args.verbose:
                print(f"      - {i.level}: {i.code}: {i.detail}")
        if any(i.level == "error" for i in issues):
            ng += 1
        out = PARSED_DIR / f"{_slug(year, season)}.json"
        out.write_text(json.dumps(td.to_dict(), ensure_ascii=False, indent=1),
                       encoding="utf-8")
    print(f"\n問題のある大会: {ng} 件")
    return 0


def cmd_validate(args) -> int:
    ng = 0
    for year, season in iter_targets(args.start, args.end, args.seasons):
        p = PARSED_DIR / f"{_slug(year, season)}.json"
        if not p.exists():
            print(f"  [SKIP] {year} {season}: 未パース")
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        td = TournamentData(
            year=d["year"], season=d["season"], title=d["title"], revid=d["revid"],
            source_url=d["source_url"],
            entries=[EntryRow(**e) for e in d["entries"]],
            games=[GameRow(**g) for g in d["games"]],
        )
        issues = validate(td)
        print(" ", summarize(td, issues))
        for i in issues:
            if i.level == "error" or args.verbose:
                print(f"      - {i.code}: {i.detail}")
        ng += any(i.level == "error" for i in issues)
    print(f"\nエラーのある大会: {ng} 件")
    return 1 if ng else 0


def cmd_load(args) -> int:
    from .load import load_file
    dsn = args.dsn or os.environ.get("SUPABASE_DSN")
    if not dsn:
        print("DSN が必要です (--dsn または環境変数 SUPABASE_DSN)", file=sys.stderr)
        return 2
    for year, season in iter_targets(args.start, args.end, args.seasons):
        p = PARSED_DIR / f"{_slug(year, season)}.json"
        if not p.exists():
            continue
        res = load_file(p, dsn, auto_create_schools=args.auto_create_schools,
                        dry_run=args.dry_run)
        print(f"  {year} {season}: {res}")
    return 0


def main(argv=None) -> int:
    # .env を読み込む(既存の環境変数が優先。シェルの export や CI 注入が勝つ)
    load_dotenv()
    ap = argparse.ArgumentParser(prog="koshien")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--from", dest="start", type=int, default=1978)
        p.add_argument("--to", dest="end", type=int, default=2025)
        p.add_argument("--seasons", nargs="+", default=["spring", "summer"])
        p.add_argument("--cache", default="data/cache")
        p.add_argument("--interval", type=float, default=1.0)
        p.add_argument("-v", "--verbose", action="store_true")

    for name, fn in [("fetch", cmd_fetch), ("parse", cmd_parse),
                     ("validate", cmd_validate), ("load", cmd_load)]:
        p = sub.add_parser(name)
        common(p)
        if name == "load":
            p.add_argument("--dsn")
            p.add_argument("--auto-create-schools", action="store_true")
            p.add_argument("--dry-run", action="store_true")
        p.set_defaults(func=fn)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
