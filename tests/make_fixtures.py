"""実際のWikipedia記事の構造を再現したフィクスチャHTMLを生成する。

サンドボックスからは ja.wikipedia.org に到達できないため、
2014年夏(表形式)と1978年夏(箇条書き形式)の実際のレイアウトを模したHTMLで
パーサの回帰テストを行う。
"""
from pathlib import Path

OUT = Path(__file__).parent / "fixtures"
OUT.mkdir(exist_ok=True)

# ---------------------------------------------------------------- 表形式(2014年夏を模写)
ENTRIES_2014 = [
    ("北北海道", "武修館", "初出場"), ("南北海道", "東海大四", "21年ぶり5回目"),
    ("青森", "八戸学院光星", "2年ぶり7回目"), ("岩手", "盛岡大付", "2年ぶり8回目"),
    ("秋田", "角館", "初出場"), ("山形", "山形中央", "4年ぶり2回目"),
    ("宮城", "利府", "初出場"), ("福島", "聖光学院", "8年連続11回目"),
    ("茨城", "藤代", "3年ぶり3回目"), ("栃木", "作新学院", "4年連続10回目"),
    ("群馬", "健大高崎", "3年ぶり2回目"), ("埼玉", "春日部共栄", "9年ぶり5回目"),
    ("東東京", "二松学舎大付", "2年ぶり12回目"), ("西東京", "日大鶴ヶ丘", "初出場"),
    ("千葉", "東海大望洋", "初出場"), ("神奈川", "東海大相模", "6年ぶり3回目"),
    ("山梨", "東海大甲府", "4年ぶり9回目"), ("長野", "佐久長聖", "2年ぶり6回目"),
    ("新潟", "日本文理", "2年連続8回目"), ("富山", "富山商", "10年ぶり16回目"),
    ("石川", "星稜", "2年連続17回目"), ("福井", "敦賀気比", "5年ぶり6回目"),
    ("静岡", "静岡", "3年ぶり23回目"), ("愛知", "東邦", "6年ぶり16回目"),
    ("岐阜", "大垣日大", "2年連続3回目"),
    ("三重", "三重", "2年連続12回目"), ("滋賀", "近江", "6年ぶり11回目"),
    ("京都", "龍谷大平安", "2年ぶり33回目"), ("大阪", "大阪桐蔭", "3年ぶり17回目"),
    ("兵庫", "神戸国際大付", "10年ぶり4回目"), ("奈良", "智弁学園", "3年連続8回目"),
    ("和歌山", "市和歌山", "初出場"), ("鳥取", "八頭", "3年ぶり9回目"),
    ("島根", "開星", "4年ぶり8回目"), ("岡山", "関西", "4年ぶり21回目"),
    ("広島", "広陵", "3年ぶり9回目"), ("山口", "岩国", "7年ぶり5回目"),
    ("香川", "坂出商", "20年ぶり8回目"), ("徳島", "鳴門", "初出場"),
    ("愛媛", "小松", "3年連続9回目"), ("高知", "明徳義塾", "5年連続16回目"),
    ("福岡", "九州国際大付", "3年ぶり5回目"), ("佐賀", "佐賀北", "2年ぶり4回目"),
    ("長崎", "海星", "3年ぶり17回目"), ("熊本", "城北", "6年ぶり4回目"),
    ("大分", "大分", "初出場"), ("宮崎", "日南学園", "3年ぶり7回目"),
    ("鹿児島", "鹿屋中央", "初出場"), ("沖縄", "沖縄尚学", "2年連続7回目"),
]

GAMES_2014_R1 = [
    ("8月11日 (第1日)", "第1試合", "春日部共栄", "5 - 1", "龍谷大平安", ""),
    ("", "第2試合", "敦賀気比", "16 - 0", "坂出商", ""),
    ("", "第3試合", "富山商", "2 - 0", "日大鶴ヶ丘", ""),
    ("8月12日 (第2日)", "第1試合", "東邦", "11 - 3", "日南学園", ""),
    ("", "第2試合", "星稜", "5 - 4", "静岡", ""),
    ("", "第3試合", "日本文理", "5 - 2", "大分", ""),
    ("", "第4試合", "大垣日大", "12 - 10", "藤代", ""),
    ("8月13日 (第3日)", "第1試合", "健大高崎", "5 - 3", "岩国", ""),
    ("", "第2試合", "鹿屋中央", "2x - 1", "市和歌山", "延長12回"),
    ("", "第3試合", "利府", "4 - 2", "佐賀北", ""),
    ("", "第4試合", "三重", "5x - 4", "広陵", "延長11回"),
    ("8月14日 (第4日)", "第1試合", "佐久長聖", "3 - 1", "東海大甲府", ""),
    ("", "第2試合", "東海大四", "6 - 1", "九州国際大付", ""),
    ("", "第3試合", "聖光学院", "2 - 1", "神戸国際大付", ""),
    ("", "第4試合", "山形中央", "9 - 8", "小松", ""),
    ("8月15日 (第5日)", "第1試合", "明徳義塾", "10 - 4", "智弁学園", ""),
    ("", "第2試合", "大阪桐蔭", "7 - 6", "開星", ""),
]
GAMES_2014_R2 = [
    ("8月15日", "第3試合", "二松学舎大付", "7 - 5", "海星", ""),
    ("8月16日 (第6日)", "第1試合", "近江", "8 - 0", "鳴門", ""),
    ("", "第2試合", "城北", "5 - 3", "東海大望洋", ""),
    ("", "第3試合", "盛岡大付", "4 - 3", "東海大相模", ""),
    ("", "第4試合", "八頭", "6 - 1", "角館", ""),
    ("8月17日 (第7日)", "第1試合", "沖縄尚学", "3 - 1", "作新学院", ""),
    ("", "第2試合", "八戸学院光星", "4 - 2", "武修館", ""),
    ("", "第3試合", "富山商", "3 - 1", "関西", ""),
    ("", "第4試合", "敦賀気比", "10 - 1", "春日部共栄", ""),
    ("8月18日 (第8日)", "第1試合", "三重", "4 - 2", "大垣日大", ""),
    ("", "第2試合", "日本文理", "3 - 2", "東邦", ""),
    ("", "第3試合", "星稜", "4 - 1", "鹿屋中央", ""),
    ("", "第4試合", "健大高崎", "10 - 0", "利府", ""),
    ("8月19日 (第9日)", "第1試合", "山形中央", "2 - 0", "東海大四", "延長10回"),
    ("", "第2試合", "聖光学院", "4 - 2", "佐久長聖", ""),
    ("", "第3試合", "大阪桐蔭", "5 - 3", "明徳義塾", ""),
]
GAMES_2014_R3 = [
    ("8月20日 (第10日)", "第1試合", "八戸学院光星", "5 - 1", "星稜", "延長10回"),
    ("", "第2試合", "沖縄尚学", "6x - 5", "二松学舎大付", ""),
    ("", "第3試合", "三重", "7 - 5", "城北", ""),
    ("", "第4試合", "敦賀気比", "16 - 1", "盛岡大付", ""),
    ("8月21日 (第11日)", "第1試合", "日本文理", "6x - 5", "富山商", ""),
    ("", "第2試合", "大阪桐蔭", "10 - 0", "八頭", ""),
    ("", "第3試合", "聖光学院", "2x - 1", "近江", ""),
    ("", "第4試合", "健大高崎", "8 - 3", "山形中央", ""),
]
GAMES_2014_QF = [
    ("8月22日 (第12日)", "第1試合", "三重", "9 - 3", "沖縄尚学", ""),
    ("", "第2試合", "敦賀気比", "7 - 2", "八戸学院光星", ""),
    ("", "第3試合", "大阪桐蔭", "5 - 2", "健大高崎", ""),
    ("", "第4試合", "日本文理", "5 - 1", "聖光学院", ""),
]
GAMES_2014_SF = [
    ("8月24日 (第13日)", "第1試合", "三重", "5 - 0", "日本文理", ""),
    ("", "第2試合", "大阪桐蔭", "15 - 9", "敦賀気比", ""),
]
GAMES_2014_F = [
    ("8月25日 (第14日)", "決勝", "大阪桐蔭", "4 - 3", "三重", ""),
]


def game_table(rows):
    h = ("<table class='wikitable'><tr><th>試合日</th><th>試合順</th><th>勝利</th>"
         "<th>スコア</th><th>敗戦</th><th>備考</th><th>試合時間</th></tr>")
    body = []
    for d, o, w, sc, lo, n in rows:
        body.append(f"<tr><td>{d}</td><td>{o}</td><td>{w}</td><td>{sc}</td>"
                    f"<td>{lo}</td><td>{n}</td><td>2時間0分</td></tr>")
    return h + "".join(body) + "</table>"


def build_2014():
    half = 25
    left, right = ENTRIES_2014[:half], ENTRIES_2014[half:]
    rows = []
    for i in range(max(len(left), len(right))):
        cells = []
        for src in (left, right):
            if i < len(src):
                q, s, a = src[i]
                cells.append(f"<td>{q}</td><td>{s}</td><td>{a}</td>")
            else:
                cells.append("<td></td><td></td><td></td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    entries_tbl = (
        "<h2>出場校</h2><table class='wikitable'><tr>"
        "<th>地方大会</th><th>代表校</th><th>出場回数</th>"
        "<th>地方大会</th><th>代表校</th><th>出場回数</th></tr>"
        + "".join(rows) + "</table>"
    )
    games = "<h2>試合結果</h2>"
    for label, rws in [("1回戦", GAMES_2014_R1), ("2回戦", GAMES_2014_R2),
                       ("3回戦", GAMES_2014_R3), ("準々決勝", GAMES_2014_QF),
                       ("準決勝", GAMES_2014_SF), ("決勝", GAMES_2014_F)]:
        games += f"<h3>{label}</h3>" + game_table(rws)
    html = f"<div class='mw-parser-output'><p>第96回…</p>{entries_tbl}{games}</div>"
    (OUT / "summer_2014.html").write_text(html, encoding="utf-8")


# ---------------------------------------------------------------- 箇条書き形式(1978年夏を模写)
GAMES_1978 = """
8月7日
- 天理 6 - 0 松商学園
- 岡山東商 3 - 1 取手二
- 広島工 2 - 0 中越
8月8日
- 仙台育英 1x - 0 高松商(延長17回)
- 報徳学園 7 - 0 盛岡一
- 所沢商 9 - 2 小城
- 高知商 5 - 1 東海大四
8月9日
- 静岡 4 - 3 鹿児島実
- 福井商 5 - 1 作新学院
- 南陽工 2 - 0 宇治山田商
- 郡山北工 2 - 1 松山商
8月10日
- 熊本工大 8 - 4 青森北(延長10回)
- 箕島 1 - 0 能代
- 東筑 4 - 3 金沢
- 県岐阜商 3 - 2 京都商
8月11日
- 倉吉北 3 - 2 早稲田実
- 桐生 18 - 0 膳所
- 延岡学園 2 - 1 石動
- 旭川竜谷 10 - 2 三刀屋
8月12日
- PL学園 5 - 2 日川
- 豊見城 3x - 2 我孫子(延長10回)
- 日田林工 3 - 0 鶴商学園
- 横浜 10 - 2 徳島商
8月13日
- 中京 6 - 1 佐世保工
- 東筑 1x - 0 日大二(延長13回)
- 岡山東商 3x - 2 福井商
- 高知商 14 - 6 倉吉北
8月14日
- 仙台育英 4 - 1 所沢商
- 報徳学園 11 - 2 郡山北工
- 熊本工大 5 - 3 静岡(延長13回)
- 箕島 6 - 1 広島工
8月15日
- 県岐阜商 3 - 0 桐生
- 天理 1 - 0 南陽工
- PL学園 2 - 0 熊本工大
- 中京 5 - 4 箕島
8月16日
- 報徳学園 5 - 0 延岡学園
- 岡山東商 4 - 2 旭川竜谷
- 高知商 4 - 2 仙台育英
8月17日
- 豊見城 4 - 1 東筑
- 県岐阜商 3 - 0 横浜
- 天理 5 - 0 日田林工
8月18日
- 中京 5 - 2 天理
- PL学園 1 - 0 県岐阜商
- 岡山東商 6x - 5 豊見城(延長10回)
- 高知商 9 - 2 報徳学園
8月19日
- PL学園 5x - 4 中京(延長12回)
- 高知商 4 - 0 岡山東商
8月20日
- PL学園 3x - 2 高知商(延長12回)
"""


def build_1978():
    parts = ["<div class='mw-parser-output'><h2>出場校</h2>"]
    ent = [("北北海道", "旭川竜谷"), ("南北海道", "函館有斗"), ("青森", "青森北"),
           ("秋田", "能代"), ("岩手", "盛岡一"), ("宮城", "仙台育英"),
           ("長野", "松商学園"), ("滋賀", "膳所"), ("奈良", "天理"),
           ("高知", "高知商"), ("大阪", "PL学園")]
    rows = "".join(f"<tr><td>{q}</td><td>{s}</td><td>初出場</td></tr>" for q, s in ent)
    parts.append("<table class='wikitable'><tr><th>地方大会</th><th>代表校</th>"
                 f"<th>出場回数</th></tr>{rows}</table>")
    parts.append("<h2>試合結果</h2>")
    buf = []
    for line in GAMES_1978.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("- "):
            buf.append(f"<li>{line[2:]}</li>")
        else:
            if buf:
                parts.append("<ul>" + "".join(buf) + "</ul>")
                buf = []
            parts.append(f"<p><b>{line}</b></p>")
    if buf:
        parts.append("<ul>" + "".join(buf) + "</ul>")
    parts.append("</div>")
    (OUT / "summer_1978.html").write_text("".join(parts), encoding="utf-8")


def build_1978_real():
    """実記事のレイアウトを模したフィクスチャ(1978年夏)。

    build_1978() が箇条書きの「素直な」形なのに対し、こちらは実記事で踏んだ地雷を
    最小構成(4校/3試合)で再現し、回帰で固定する:

      - 概要 infobox の「出場校」行が school 列と誤検出され、後続の
        「優勝校 / 試合数 / …」がダミー出場校として混入する。
      - 東日本/西日本 wikitable を包む multicol ラッパを親としても解析すると
        出場校が二重取りになる。
      - 決勝はイニングスコア表だけに載り、しかもヘッダ(1 2 3 … R H)が
        先頭行ではなく2行目にある。
    """
    p = ["<div class='mw-parser-output'>"]

    # (地雷1) 概要 infobox — 「出場校」ラベルが school と誤検出される
    p.append(
        "<table class='infobox'>"
        "<tr><th colspan='2'>第60回全国高等学校野球選手権大会</th></tr>"
        "<tr><th>試合日程</th><td>1978年8月8日-20日</td></tr>"
        "<tr><th>出場校</th><td>49校</td></tr>"
        "<tr><th>優勝校</th><td>PL学園(大阪)</td></tr>"
        "<tr><th>試合数</th><td>48試合</td></tr>"
        "<tr><th>選手宣誓</th><td>某(某校)</td></tr>"
        "<tr><th>始球式</th><td>某</td></tr>"
        "<tr><th>大会本塁打</th><td>0本</td></tr>"
        "<tr><td colspan='2'>テンプレートを表示</td></tr>"
        "</table>"
    )

    # (地雷2) 東日本/西日本 wikitable を multicol ラッパで横並び(ネスト表)
    east = [("愛知", "中京", "2年ぶり18回目"), ("長野", "松商学園", "4年連続23回目")]
    west = [("大阪", "PL学園", "2年ぶり6回目"), ("高知", "高知商", "5年ぶり11回目")]

    def entries_table(banner, rows):
        body = "".join(
            f"<tr><td>{q}</td><td>{s}</td><td>{a}</td></tr>" for q, s, a in rows
        )
        return (
            "<table class='wikitable'>"
            f"<tr><th colspan='3'>{banner}</th></tr>"
            "<tr><th>地方大会</th><th>代表校</th><th>出場回数</th></tr>"
            f"{body}</table>"
        )

    p.append("<h2>代表校</h2>")
    p.append(
        "<table class='multicol'><tr>"
        f"<td>{entries_table('東日本', east)}</td>"
        f"<td>{entries_table('西日本', west)}</td>"
        "</tr></table>"
    )

    # 試合結果: 準決勝は箇条書き、決勝はイニングスコアのみ
    p.append("<h2>試合結果</h2>")
    p.append("<h3>準決勝</h3><ul>"
             "<li>PL学園 3 - 1 松商学園</li>"
             "<li>高知商 4 - 2 中京</li>"
             "</ul>")

    # (地雷3) 決勝 = イニングスコア表。ヘッダは2行目、総得点列は R
    innings = "".join(f"<td>{v}</td>" for v in [0, 0, 1, 0, 0, 1, 0, 0, 0])  # 見た目用
    p.append(
        "<h3>決勝</h3>"
        "<table class='wikitable'>"
        "<tr><th colspan='12'>スコアボード</th></tr>"
        "<tr><th></th><th>1</th><th>2</th><th>3</th><th>4</th><th>5</th>"
        "<th>6</th><th>7</th><th>8</th><th>9</th><th>R</th><th>H</th></tr>"
        f"<tr><td>高知商</td>{innings}<td>2</td><td>6</td></tr>"
        f"<tr><td>PL学園</td>{innings}<td>3</td><td>8</td></tr>"
        "</table>"
    )

    p.append("</div>")
    (OUT / "summer_1978_real.html").write_text("".join(p), encoding="utf-8")


def _bracket_table(rounds):
    """トーナメント表(ブラケット)HTML を生成する。

    実記事のブラケットは各ラウンドが「名前列 + スコア列」を占め、試合は連続2行、
    日付は名前列・スコア列にまたがる colspan 行で載る。さらに rowspan で各セルの
    値が複数行に複製される。ここではそれらの地雷を再現する:

      - ラウンドごとに列ペア(名前, スコア)を割り当て(間にスペーサ列)。
      - 日付行は名前列・スコア列が同一テキスト(colspan 相当)。
      - チーム行は連続2行に同じ (名前, スコア) を複製(rowspan 相当)。

    rounds: [(round_label, [(t1, s1, t2, s2, date), ...]), ...]
    スコア s1/s2 が None の試合は不戦勝(辞退)を表す。勝者セルを「〇〇(不戦勝)」に、
    スコア列を空にして、辞退校(t2)を直下に並べる(2021夏の実構造を再現)。
    """
    ncols = len(rounds) * 3           # 各ラウンド: 名前, スコア, スペーサ
    grid: list[list[str | None]] = []

    def put(r, c, text):
        while len(grid) <= r:
            grid.append([None] * ncols)
        grid[r][c] = text

    for i, (label, _) in enumerate(rounds):
        put(0, i * 3, label)
        put(0, i * 3 + 1, label)      # ラベルは名前列・スコア列にまたがる
    for i, (_, matches) in enumerate(rounds):
        nc, sc = i * 3, i * 3 + 1
        r = 1
        for t1, s1, t2, s2, date in matches:
            put(r, nc, date)                                  # 日付(colspan)
            put(r, sc, date)
            r += 1
            forfeit = s1 is None or s2 is None                # 不戦勝(スコア無し)
            cells = ((t1, s1), (t1, s1), (t2, s2), (t2, s2))  # rowspan複製
            for name, score in cells:
                if forfeit:
                    put(r, nc, f"{name}(不戦勝)" if name == t1 else name)
                    put(r, sc, "")                            # スコア列は空
                else:
                    put(r, nc, name)
                    put(r, sc, str(score))
                r += 1

    rows = []
    for row in grid:
        tds = "".join(f"<td>{c if c is not None else ''}</td>" for c in row)
        rows.append(f"<tr>{tds}</tr>")
    return "<table>" + "".join(rows) + "</table>"


def build_1978_spring():
    """春(選抜)記事のレイアウトを模したフィクスチャ(第50回=1978を模写)。

    春は夏と書式が異なり、現行 A/B/C では拾えない:

      - 出場校が「校名 （ 都道府県 、出場回数)」の箇条書き(単一 <ul>)。
      - 試合結果が左右2枚のトーナメント表(ブラケット)。
      - 決勝はイニングスコアだけに載る。

    6校/5試合の最小構成。byes を含む(準々決勝が無く 1回戦→準決勝)ため、
    ラウンドは末尾から f1・sf2・r1(残り)= r1:2,sf:2,f:1 に逆算される。
    """
    p = ["<div class='mw-parser-output'><h2>出場校</h2>"]

    # 箇条書き出場校(スペースゆれ・同一県複数校=群馬2校 を含む)
    entries = [
        ("浜松商", " 静岡 ", "14年ぶり4回目"),
        ("桐生", "群馬", "11年ぶり12回目"),
        ("前橋", " 群馬 ", "初出場"),
        ("福井商", " 福井 ", "3年ぶり5回目"),
        ("PL学園", "大阪", "6年ぶり6回目"),
        ("箕島", " 和歌山 ", "2年連続5回目"),
    ]
    lis = "".join(f"<li>{s} （{q}、{a})</li>" for s, q, a in entries)
    p.append(f"<ul>{lis}</ul>")

    # 試合結果: 左右2枚のブラケット + 決勝スコアボード
    p.append("<h2>試合結果</h2><h3>トーナメント表</h3>")
    left = _bracket_table([
        # 1回戦はサヨナラ(スコア末尾 x)。勝者は桐生のまま。
        ("1回戦", [("桐生", "3x", "前橋", 2, "3月27日(1):延長13回")]),
        ("準決勝", [("浜松商", 5, "桐生", 1, "3月30日(1)")]),
    ])
    right = _bracket_table([
        ("1回戦", [("PL学園", 4, "箕島", 0, "3月27日(2)")]),
        ("準決勝", [("福井商", 6, "PL学園", 2, "3月30日(2)")]),
    ])
    p.append(left)
    p.append(right)

    # 決勝 = イニングスコア表(ヘッダは2行目、総得点列は R)
    innings = "".join(f"<td>{v}</td>" for v in [0, 0, 1, 0, 0, 1, 0, 0, 0])
    p.append(
        "<h3>決勝</h3>"
        "<table class='wikitable'>"
        "<tr><th colspan='12'>スコアボード</th></tr>"
        "<tr><th></th><th>1</th><th>2</th><th>3</th><th>4</th><th>5</th>"
        "<th>6</th><th>7</th><th>8</th><th>9</th><th>R</th><th>H</th></tr>"
        f"<tr><td>福井商</td>{innings}<td>2</td><td>6</td></tr>"
        f"<tr><td>浜松商</td>{innings}<td>3</td><td>8</td></tr>"
        "</table>"
    )

    # 記録(大会記録)表。「校名」列を持つが出場校表ではない。出場校表として
    # 誤検出されると箇条書きフォールバックが抑止され entries が壊れる(1984春の地雷)。
    p.append(
        "<h2>記録</h2>"
        "<table class='wikitable'>"
        "<tr><th>記録</th><th>校名</th><th>対戦校</th><th>補足</th></tr>"
        "<tr><td>1試合最多本塁打</td><td>浜松商</td><td>1回戦・前橋</td><td>大会タイ</td></tr>"
        "</table>"
    )

    p.append("</div>")
    (OUT / "spring_1978.html").write_text("".join(p), encoding="utf-8")


def build_spring_entries_table():
    """近年の春(選抜)の出場校表を模したフィクスチャ(2000年以降を模写)。

    2000〜2025年の春はすべてこの表形式で、現行パーサでは entries=0 になる:

      - ヘッダが「地区 | 選出校(colspan=2) | 出場回数」。校名列の見出し『選出校』が
        colspan=2 で校名列と都道府県列の2列を覆う(2列目に固有の見出しが無い)。
      - 『選出校』は _classify_header で「選出」を含むため selection(21世紀枠列)と
        誤分類され、school 列なしと判定されてテーブルごと捨てられていた。
      - 地区は rowspan で複数校にまたがり、2校目以降は地区セルを持たない行になる。
      - 21世紀枠は別テーブルで、直前の見出し『21世紀枠』で判定する(列ではない)。

    8校(一般6 + 21世紀枠2)の最小構成。1県複数校(京都=鳥羽/龍谷大平安)を含む。
    """
    def entries_table(heading, rows):
        body = "".join(
            # region が None の行は地区セルを省く(rowspan で上の行から継承)
            (f"<tr><td rowspan='{rs}'>{reg}</td>" if reg else "<tr>")
            + f"<td>{sch}</td><td>{pref}</td><td>{app}</td></tr>"
            for reg, rs, sch, pref, app in rows
        )
        return (
            f"<h3>{heading}</h3>"
            "<table class='wikitable'>"
            "<tr><th>地区</th><th colspan='2'>選出校</th><th>出場回数</th></tr>"
            f"{body}</table>"
        )

    p = ["<div class='mw-parser-output'><h2>選出校</h2>"]
    p.append(entries_table("一般選考", [
        ("北海道", 1, "北照", "北海道", "2年ぶり2回目"),
        ("東北", 1, "秋田経法大付", "秋田", "7年ぶり4回目"),
    ]))
    p.append(entries_table("一般選考", [
        ("近畿", 2, "鳥羽", "京都", "53年ぶり2回目"),   # 地区が2校にまたがる
        (None, 1, "龍谷大平安", "京都", "4年ぶり42回目"),  # 地区セル省略
        ("東海", 1, "中京大中京", "愛知", "3年ぶり31回目"),
        ("九州", 1, "東福岡", "福岡", "初出場"),
    ]))
    p.append(entries_table("21世紀枠", [
        ("関東", 1, "石橋", "栃木", "初出場"),
        ("北信越", 1, "氷見", "富山", "30年ぶり2回目"),
    ]))

    # 試合結果は一覧表(8校=7試合、優勝=北照)。検証を通すための最小トーナメント。
    order = ["北照", "秋田経法大付", "鳥羽", "龍谷大平安",
             "中京大中京", "東福岡", "石橋", "氷見"]
    p.append("<h2>試合結果</h2>")
    rounds, cur = [], list(order)
    while len(cur) > 1:
        rnd, nxt, i = [], [], 0
        while i + 1 < len(cur):
            rnd.append((cur[i], cur[i + 1]))
            nxt.append(cur[i])
            i += 2
        rounds.append(rnd)
        cur = nxt
    for label, rnd in [("1回戦", rounds[0]), ("準決勝", rounds[1]),
                       ("決勝", rounds[2])]:
        rows = [(f"3月{25 + i}日", f"第{i + 1}試合", w, "2 - 1", lo, "")
                for i, (w, lo) in enumerate(rnd)]
        p.append(f"<h3>{label}</h3>" + game_table(rows))

    p.append("</div>")
    (OUT / "spring_entries_table.html").write_text("".join(p), encoding="utf-8")


def build_dupname_summer():
    """同名校が別県に存在するケース(1989/1990 夏を模写)。

    海星(三重) と 海星(長崎) が同じ大会に出場する。校名だけで名寄せすると
    片方が dedup で消え、敗戦も合算されて multi_loss になる。出場校は県で区別し、
    試合名は記事どおり括弧で県を明示する。16校の一覧表形式(=試合表が本線で拾われる
    件数)にして、実記事同様に表パスで解析されるようにする。
    """
    # 16校。海星は三重・長崎の同名別県。地方大会名=都道府県(名寄せの県はここから解決)。
    prefs = ["北北海道", "青森", "岩手", "宮城", "茨城", "群馬", "東東京", "神奈川",
             "新潟", "静岡", "愛知", "大阪", "兵庫", "広島", "三重", "長崎"]
    schools = ["旭川竜谷", "青森山田", "盛岡大付", "仙台育英", "常総学院", "前橋育英",
               "帝京", "横浜", "日本文理", "静岡", "中京", "PL学園", "報徳学園",
               "広陵", "海星", "海星"]
    ent_rows = "".join(
        f"<tr><td>{q}</td><td>{s}</td><td>初出場</td></tr>"
        for q, s in zip(prefs, schools, strict=True)
    )
    entries_tbl = (
        "<h2>出場校</h2><table class='wikitable'>"
        "<tr><th>地方大会</th><th>代表校</th><th>出場回数</th></tr>"
        + ent_rows + "</table>"
    )

    # 試合表示名: 同名の海星だけ括弧で県を明示(記事の慣習)。
    display = list(schools)
    display[14] = "海星(三重)"
    display[15] = "海星(長崎)"

    # 決定的な単純トーナメント(先頭 index が勝つ)。15試合、優勝=旭川竜谷。
    game_rows = []
    cur = list(display)
    day = 10
    while len(cur) > 1:
        nxt, i, gm = [], 0, 1
        while i + 1 < len(cur):
            w, lo = cur[i], cur[i + 1]
            game_rows.append((f"8月{day}日", f"第{gm}試合", w, "2 - 1", lo, ""))
            nxt.append(w)
            i += 2
            gm += 1
        if i < len(cur):          # 奇数なら不戦勝
            nxt.append(cur[i])
        cur, day = nxt, day + 1

    # ラウンド見出しを付けず(round_code=None)、構造から逆算させる
    games = "<h2>試合結果</h2>" + game_table(game_rows)
    html = f"<div class='mw-parser-output'>{entries_tbl}{games}</div>"
    (OUT / "summer_dupname.html").write_text(html, encoding="utf-8")


def build_mixed_format_summer():
    """試合結果の書式が混在する年(1991 夏を模写)。

    同じ大会で 1回戦=箇条書き / 後半=一覧表 / 決勝=イニングスコア のように
    書式が混ざる。表と箇条書きのどちらか一方だけを見ると試合を取りこぼす。
    加えて「概要」節の説明文(ラウンド見出しの外)が試合として誤検出されないこと。
    """
    prefs = ["北北海道", "青森", "岩手", "宮城", "茨城", "群馬", "東東京", "神奈川",
             "新潟", "静岡", "愛知", "大阪", "兵庫", "広島", "三重", "長崎"]
    schools = ["旭川竜谷", "青森山田", "盛岡大付", "仙台育英", "常総学院", "前橋育英",
               "帝京", "横浜", "日本文理", "静岡", "中京", "PL学園", "報徳学園",
               "広陵", "四日市工", "海星"]
    ent_rows = "".join(
        f"<tr><td>{q}</td><td>{s}</td><td>初出場</td></tr>"
        for q, s in zip(prefs, schools, strict=True)
    )
    entries_tbl = (
        "<h2>出場校</h2><table class='wikitable'>"
        "<tr><th>地方大会</th><th>代表校</th><th>出場回数</th></tr>"
        + ent_rows + "</table>"
    )

    # 決定的なトーナメント。先頭 index が勝つ。rounds[0]=8, [1]=4, [2]=2, [3]=1 試合。
    rounds, cur, day = [], list(schools), 10
    while len(cur) > 1:
        rnd, nxt, i = [], [], 0
        while i + 1 < len(cur):
            rnd.append((cur[i], cur[i + 1]))     # (勝者, 敗者)
            nxt.append(cur[i])
            i += 2
        rounds.append(rnd)
        cur, day = nxt, day + 1

    # 概要: 説明文の箇条書き(ラウンド見出し外=round_code None → 試合として拾わない)
    overview = ("<h2>概要</h2><ul><li>8月20日-決勝戦が行われ"
                f"{schools[0]}が{schools[5]}を 1-0 で下し初優勝。</li></ul>")

    games = "<h2>試合結果</h2>"
    # 1回戦(8)+準々決勝(4)を一覧表 → 表=12(≥10)
    for label, rnd in [("1回戦", rounds[0]), ("準々決勝", rounds[1])]:
        rows = [(f"8月{d}日", f"第{i+1}試合", w, "2 - 1", lo, "")
                for i, (w, lo) in enumerate(rnd) for d in [15]]
        games += f"<h3>{label}</h3>" + game_table(rows)
    # 準決勝(2)を箇条書き
    sf = rounds[2]
    games += "<h3>準決勝</h3><ul>" + "".join(
        f"<li>{w} 3 - 1 {lo}</li>" for w, lo in sf) + "</ul>"
    # 決勝(1)をイニングスコア
    fw, fl = rounds[3][0]
    innings = "".join(f"<td>{v}</td>" for v in [0, 0, 1, 0, 0, 1, 0, 0, 0])
    games += (
        "<h3>決勝</h3>"
        "<table class='wikitable'>"
        "<tr><th colspan='12'>スコアボード</th></tr>"
        "<tr><th></th><th>1</th><th>2</th><th>3</th><th>4</th><th>5</th>"
        "<th>6</th><th>7</th><th>8</th><th>9</th><th>R</th><th>H</th></tr>"
        f"<tr><td>{fl}</td>{innings}<td>2</td><td>6</td></tr>"
        f"<tr><td>{fw}</td>{innings}<td>3</td><td>8</td></tr>"
        "</table>"
    )

    html = f"<div class='mw-parser-output'>{entries_tbl}{overview}{games}</div>"
    (OUT / "summer_mixed.html").write_text(html, encoding="utf-8")


def build_bracket_table_mix_summer():
    """ブラケットと一覧表が混在する年(1995 夏を模写)。

    1回戦〜準々決勝=トーナメント表(ブラケット)、準決勝=一覧表、決勝=イニングスコア。
    片方だけ見ると試合を取りこぼす(ブラケットで上書きすると表の準決勝が消える)。
    """
    prefs = ["北北海道", "青森", "岩手", "宮城", "茨城", "群馬", "東東京", "神奈川",
             "新潟", "静岡", "愛知", "大阪", "兵庫", "広島", "三重", "長崎"]
    schools = ["旭川竜谷", "青森山田", "盛岡大付", "仙台育英", "常総学院", "前橋育英",
               "帝京", "横浜", "日本文理", "静岡", "中京", "PL学園", "報徳学園",
               "広陵", "四日市工", "海星"]
    ent_rows = "".join(
        f"<tr><td>{q}</td><td>{s}</td><td>初出場</td></tr>"
        for q, s in zip(prefs, schools, strict=True)
    )
    entries_tbl = (
        "<h2>代表校</h2><table class='wikitable'>"
        "<tr><th>地方大会</th><th>代表校</th><th>出場回数</th></tr>"
        + ent_rows + "</table>"
    )

    # 決定的トーナメント。先頭 index が勝つ。rounds[0]=8, [1]=4, [2]=2, [3]=1。
    rounds, cur = [], list(schools)
    while len(cur) > 1:
        rnd, nxt, i = [], [], 0
        while i + 1 < len(cur):
            rnd.append((cur[i], cur[i + 1]))     # (勝者, 敗者)
            nxt.append(cur[i])
            i += 2
        rounds.append(rnd)
        cur = nxt

    games = "<h2>組み合わせ・試合結果</h2>"
    # 1回戦(8)+準々決勝(4)をブラケット表(ラウンド見出し2種以上)
    br = [
        ("1回戦", [(w, 2, lo, 1, "8月10日") for w, lo in rounds[0]]),
        ("準々決勝", [(w, 3, lo, 1, "8月15日") for w, lo in rounds[1]]),
    ]
    games += _bracket_table(br)
    # 準決勝(2)を一覧表
    games += "<h3>準決勝</h3>" + game_table(
        [("8月18日", f"第{i+1}試合", w, "4 - 2", lo, "")
         for i, (w, lo) in enumerate(rounds[2])])
    # 決勝(1)をイニングスコア
    fw, fl = rounds[3][0]
    innings = "".join(f"<td>{v}</td>" for v in [0, 0, 1, 0, 0, 1, 0, 0, 0])
    games += (
        "<h3>決勝</h3>"
        "<table class='wikitable'>"
        "<tr><th colspan='12'>スコアボード</th></tr>"
        "<tr><th></th><th>1</th><th>2</th><th>3</th><th>4</th><th>5</th>"
        "<th>6</th><th>7</th><th>8</th><th>9</th><th>R</th><th>H</th></tr>"
        f"<tr><td>{fl}</td>{innings}<td>2</td><td>6</td></tr>"
        f"<tr><td>{fw}</td>{innings}<td>3</td><td>8</td></tr>"
        "</table>"
    )

    html = f"<div class='mw-parser-output'>{entries_tbl}{games}</div>"
    (OUT / "summer_bracket_table.html").write_text(html, encoding="utf-8")


def build_forfeit_summer():
    """不戦勝(出場辞退)を含む夏(2021夏=第103回を模写)。

    1校が出場を辞退し、対戦相手が不戦勝で進出する。ブラケットでは勝者セルが
    「〇〇(不戦勝)」でスコア列が空、直下に辞退校が並ぶ。スコアが無いため素朴な
    parse_bracket はこの2ノードを落とし、試合数不足(games=出場校-2)と
    無敗校過多(辞退校が敗戦を持たず無敗のまま)を招いていた。
    ここでは 1回戦の第1試合を不戦勝(辞退校=schools[1])として再現する。
    """
    prefs = ["北北海道", "青森", "岩手", "宮城", "茨城", "群馬", "東東京", "神奈川",
             "新潟", "静岡", "愛知", "大阪", "兵庫", "広島", "三重", "長崎"]
    schools = ["旭川竜谷", "青森山田", "盛岡大付", "仙台育英", "常総学院", "前橋育英",
               "帝京", "横浜", "日本文理", "静岡", "中京", "PL学園", "報徳学園",
               "広陵", "四日市工", "海星"]
    ent_rows = "".join(
        f"<tr><td>{q}</td><td>{s}</td><td>初出場</td></tr>"
        for q, s in zip(prefs, schools, strict=True)
    )
    entries_tbl = (
        "<h2>代表校</h2><table class='wikitable'>"
        "<tr><th>地方大会</th><th>代表校</th><th>出場回数</th></tr>"
        + ent_rows + "</table>"
    )

    # 決定的トーナメント(先頭 index が勝つ)。rounds[0]=8, [1]=4, [2]=2, [3]=1。
    rounds, cur = [], list(schools)
    while len(cur) > 1:
        rnd, nxt, i = [], [], 0
        while i + 1 < len(cur):
            rnd.append((cur[i], cur[i + 1]))     # (勝者, 敗者)
            nxt.append(cur[i])
            i += 2
        rounds.append(rnd)
        cur = nxt

    def matches(rnd, date, forfeit_first=False):
        out = []
        for idx, (w, lo) in enumerate(rnd):
            if forfeit_first and idx == 0:       # 辞退校 lo が不戦勝で w に敗退
                out.append((w, None, lo, None, date))
            else:
                out.append((w, 2, lo, 1, date))
        return out

    br = [
        ("1回戦", matches(rounds[0], "8月10日", forfeit_first=True)),
        ("準々決勝", matches(rounds[1], "8月15日")),
        ("準決勝", matches(rounds[2], "8月18日")),
        ("決勝", matches(rounds[3], "8月21日")),
    ]
    games = "<h2>組み合わせ・試合結果</h2>" + _bracket_table(br)
    html = f"<div class='mw-parser-output'>{entries_tbl}{games}</div>"
    (OUT / "summer_forfeit.html").write_text(html, encoding="utf-8")


def build_episode_prose_summer():
    """「エピソード」節の散文が試合として誤検出されない年(1997夏を模写)。

    試合結果の後ろに置かれた「エピソード」節の箇条書きに、逆転劇を語る散文
    (「…当初 校A 1-9 校B と8点の大差…17-10 で逆転」)が入っている。この <li> は
    埋め込みスコアが _SCORE_RE に誤マッチするうえ、直前の最後のラウンド見出しから
    cur_round を引き継ぐため、round=None を除外する既存フィルタもすり抜けて幽霊試合を
    1件生む。校名らしさのガード(勝者名/敗者名が散文なら不採用)でこれを止める。

    build_mixed_format_summer は概要節(round=None)の散文を突くのに対し、こちらは
    round が非None にリークした散文を突く別ケース。
    """
    prefs = ["北北海道", "青森", "岩手", "宮城", "茨城", "群馬", "東東京", "神奈川",
             "新潟", "静岡", "愛知", "大阪", "兵庫", "広島", "三重", "長崎"]
    schools = ["旭川竜谷", "青森山田", "盛岡大付", "仙台育英", "常総学院", "前橋育英",
               "帝京", "横浜", "日本文理", "静岡", "中京", "PL学園", "報徳学園",
               "広陵", "四日市工", "海星"]
    ent_rows = "".join(
        f"<tr><td>{q}</td><td>{s}</td><td>初出場</td></tr>"
        for q, s in zip(prefs, schools, strict=True)
    )
    entries_tbl = (
        "<h2>代表校</h2><table class='wikitable'>"
        "<tr><th>地方大会</th><th>代表校</th><th>出場回数</th></tr>"
        + ent_rows + "</table>"
    )

    # 決定的なトーナメント。先頭 index が勝つ。rounds[0]=8, [1]=4, [2]=2, [3]=1。
    rounds, cur = [], list(schools)
    while len(cur) > 1:
        rnd, nxt, i = [], [], 0
        while i + 1 < len(cur):
            rnd.append((cur[i], cur[i + 1]))     # (勝者, 敗者)
            nxt.append(cur[i])
            i += 2
        rounds.append(rnd)
        cur = nxt

    # 全試合を一覧表で掲載(errors=0 の完全なトーナメント)。ラウンド見出しがあるので
    # 最後(決勝)で cur_round が非None のまま「エピソード」節に持ち越される。
    games = "<h2>試合結果</h2>"
    for ri, (label, rnd) in enumerate([("1回戦", rounds[0]), ("準々決勝", rounds[1]),
                                       ("準決勝", rounds[2]), ("決勝", rounds[3])]):
        rows = [(f"8月{15 + ri}日", f"第{i + 1}試合", w, "2 - 1", lo, "")
                for i, (w, lo) in enumerate(rnd)]
        games += f"<h3>{label}</h3>" + game_table(rows)

    # エピソード: 逆転劇を語る散文の箇条書き。埋め込みスコア(校A 1-9 校B, 17-10)が
    # 試合として拾われてはいけない。勝者/敗者名が文章になり読点・句点を含む。
    a, b, pa, pb = schools[0], schools[1], prefs[0], prefs[1]
    episode = (
        "<h2>エピソード</h2><ul><li>"
        f"1回戦の{a}（{pa}）対{b}（{pb}）戦では、当初3回終了時に{a} 1-9 {b}と"
        f"8点の大差をつけられていた。だが{a}は6回裏に一挙10点を奪って逆転し、"
        f"最終的に 17-10 で勝利した。"
        "</li></ul>"
    )

    html = f"<div class='mw-parser-output'>{entries_tbl}{games}{episode}</div>"
    (OUT / "summer_episode.html").write_text(html, encoding="utf-8")


def build_replay_final_summer():
    """決勝が引き分け再試合になった年(2006年夏を模写)。

    決勝が延長で引き分けとなり、翌日に再試合が行われた年。記事では
    「決勝」と「決勝再試合」の2枚のスコアボードが同一カードで並ぶ。
    parse_linescores は両方を拾うが、parse_games のスコアボード補完が
    校名ペアだけで重複排除していると、後段の再試合を「既知の重複」として
    捨ててしまい、決勝が引き分け1試合だけ残る。すると is_draw のため敗戦が
    数えられず、両決勝校が無敗になって champion エラーになる。

    最小構成(4校/準決勝2 + 決勝引き分け + 決勝再試合 = 4試合)で固定する。
    正しく拾えれば games = 出場校 − 1 + 再試合1 = 4、無敗は再試合の勝者1校。
    """
    entries = [
        ("西東京", "早稲田実"),
        ("南北海道", "駒大苫小牧"),
        ("和歌山", "智弁和歌山"),
        ("鹿児島", "鹿児島工"),
    ]
    ent_rows = "".join(
        f"<tr><td>{q}</td><td>{s}</td><td>初出場</td></tr>" for q, s in entries
    )
    entries_tbl = (
        "<h2>出場校</h2><table class='wikitable'>"
        "<tr><th>地方大会</th><th>代表校</th><th>出場回数</th></tr>"
        + ent_rows + "</table>"
    )

    p = ["<div class='mw-parser-output'>", entries_tbl, "<h2>試合結果</h2>"]
    p.append("<h3>準決勝</h3><ul>"
             "<li>早稲田実 5 - 2 智弁和歌山</li>"
             "<li>駒大苫小牧 3 - 1 鹿児島工</li>"
             "</ul>")

    # 決勝(引き分け)と決勝再試合を、同一カードのスコアボード2枚で掲載する。
    # ヘッダは2行目・総得点列は R。上段=先攻。round_code はどちらも見出しから f。
    def scoreboard(top, bot, top_r, bot_r):
        head = ("<tr><th></th><th>1</th><th>2</th><th>3</th><th>4</th><th>5</th>"
                "<th>6</th><th>7</th><th>8</th><th>9</th><th>R</th><th>H</th></tr>")
        blank = "<td>0</td>" * 9
        return (
            "<table class='wikitable'>"
            "<tr><th colspan='12'>スコアボード</th></tr>"
            f"{head}"
            f"<tr><td>{top}</td>{blank}<td>{top_r}</td><td>5</td></tr>"
            f"<tr><td>{bot}</td>{blank}<td>{bot_r}</td><td>7</td></tr>"
            "</table>"
        )

    # 8/20 決勝: 駒大苫小牧 1 - 1 早稲田実(延長・引き分け)
    p.append("<h3>決勝</h3>" + scoreboard("駒大苫小牧", "早稲田実", 1, 1))
    # 8/21 決勝再試合: 早稲田実 4 - 3 駒大苫小牧(初優勝)
    p.append("<h3>決勝再試合</h3>" + scoreboard("駒大苫小牧", "早稲田実", 3, 4))

    p.append("</div>")
    (OUT / "summer_replay_final.html").write_text("".join(p), encoding="utf-8")


if __name__ == "__main__":
    build_2014()
    build_1978()
    build_1978_real()
    build_1978_spring()
    build_spring_entries_table()
    build_dupname_summer()
    build_mixed_format_summer()
    build_bracket_table_mix_summer()
    build_forfeit_summer()
    build_episode_prose_summer()
    build_replay_final_summer()
    print("fixtures written to", OUT)
