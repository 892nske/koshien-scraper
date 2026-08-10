"""日本語版WikipediaのMediaWiki APIクライアント。

- 通常のHTMLスクレイピングではなく公式APIを使う(サーバ負荷が軽く、構造も安定)
- Wikimedia の User-Agent ポリシーに従い、連絡先入りUAを必須とする
- 取得結果はディスクにキャッシュし、再実行時はネットワークに出ない
- maxlag と最小リクエスト間隔でレート制御する
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

import requests

API_ENDPOINT = "https://ja.wikipedia.org/w/api.php"


@dataclass
class Page:
    title: str          # 正規化後(リダイレクト解決後)のタイトル
    revid: int
    html: str
    fetched_at: str


class WikiClient:
    def __init__(
        self,
        cache_dir: str | Path = "data/cache",
        user_agent: str | None = None,
        min_interval: float = 1.0,
    ):
        ua = user_agent or os.environ.get("KOSHIEN_UA")
        if not ua or "@" not in ua:
            raise ValueError(
                "連絡先を含む User-Agent が必要です。"
                "例: KOSHIEN_UA='koshien-db/0.1 (you@example.com)'"
            )
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers["User-Agent"] = ua
        self.min_interval = min_interval
        self._last_call = 0.0

    # ------------------------------------------------------------------
    def _sleep(self) -> None:
        wait = self.min_interval - (time.time() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.time()

    def _cache_path(self, title: str) -> Path:
        safe = title.replace("/", "_")
        return self.cache_dir / f"{safe}.json"

    # ------------------------------------------------------------------
    def get_page(self, title: str, force: bool = False) -> Page | None:
        """記事のレンダリング済みHTMLを取得する。存在しなければ None。"""
        cache = self._cache_path(title)
        if cache.exists() and not force:
            d = json.loads(cache.read_text(encoding="utf-8"))
            return Page(**d) if d else None

        self._sleep()
        params = {
            "action": "parse",
            "page": title,
            "prop": "text|revid",
            "format": "json",
            "formatversion": "2",
            "redirects": "1",
            "maxlag": "5",
        }
        r = self.session.get(API_ENDPOINT, params=params, timeout=30)
        if r.status_code == 429 or "maxlag" in r.text[:200]:
            time.sleep(10)
            r = self.session.get(API_ENDPOINT, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()

        if "error" in data:
            code = data["error"].get("code")
            if code in ("missingtitle", "nosuchpageid"):
                cache.write_text("null", encoding="utf-8")   # 不在をキャッシュ
                return None
            raise RuntimeError(f"MediaWiki API error: {data['error']}")

        p = data["parse"]
        page = Page(
            title=p["title"],
            revid=p.get("revid", 0),
            html=p["text"],
            fetched_at=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        )
        cache.write_text(json.dumps(page.__dict__, ensure_ascii=False), encoding="utf-8")
        return page

    def get_first_existing(self, titles: list[str]) -> Page | None:
        """候補タイトルを順に試し、最初に存在したページを返す。"""
        for t in titles:
            page = self.get_page(t)
            if page is not None:
                return page
        return None
