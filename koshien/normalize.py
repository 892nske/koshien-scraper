"""文字列正規化と、地方大会・都道府県・地区のマスタ対応表。"""
from __future__ import annotations

import re
import unicodedata

# --------------------------------------------------------------------------
# 校名の正規化
# --------------------------------------------------------------------------

_SUFFIXES = ("高等学校", "高校", "高", "中学校・高等学校")

# 旧字体・異体字の最低限のゆらぎ吸収
_CHAR_MAP = str.maketrans({
    "學": "学", "校": "校", "實": "実", "澤": "沢", "齋": "斎", "齊": "斉",
    "德": "徳", "髙": "高", "﨑": "崎", "邊": "辺", "邉": "辺", "濱": "浜",
    "ヶ": "ケ", "ヵ": "カ", "ノ": "ノ",
    # 記事側の誤記。カタカナのニ(2025春「ニ松学舎大付」)は漢数字の二と紛れる
    "ニ": "二",
})


def normalize_text(s: str) -> str:
    """全角/半角・空白・注釈記号を落とした比較用の文字列を返す。"""
    if s is None:
        return ""
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"\[\d+\]|\[注\s*\d*\]", "", s)      # 脚注マーク
    s = re.sub(r"[\s\u3000]+", "", s)
    return s.strip()


# 旧校名 → 現校名。同一校が別表記になる改称を名寄せする(必要に応じて追記)。
_SCHOOL_RENAMES = {"明徳": "明徳義塾"}


def normalize_school(name: str) -> str:
    """校名の名寄せキー。「大阪桐蔭高等学校」「大阪桐蔭高」→「大阪桐蔭」"""
    s = normalize_text(name)
    s = s.translate(_CHAR_MAP)
    s = re.sub(r"[（(].*?[)）]", "", s)              # 括弧内(都道府県など)を除去
    s = re.sub(r"[\[［].*?[\]］]", "", s)            # 脚注 [注釈N] などを除去
    for suf in sorted(_SUFFIXES, key=len, reverse=True):
        if s.endswith(suf):
            s = s[: -len(suf)]
            break
    return _SCHOOL_RENAMES.get(s, s)                # 旧校名 → 現校名


_NAME_PREF_RE = re.compile(r"[（(]\s*([^)）]+?)\s*[)）]")


def split_school_pref(name: str) -> tuple[str, str | None]:
    """同名校の県付き表記を分解する。'海星(長崎)' → (名寄せキー'海星', '長崎')。

    括弧内が都道府県でなければ pref は None(名寄せキーは括弧を落として得る)。
    同名校が別県に存在する場合の照合に使う(校名だけで名寄せしないため)。
    """
    m = _NAME_PREF_RE.search(name or "")
    pref = canonical_prefecture(m.group(1)) if m else None
    return normalize_school(name), pref


def parse_appearance(text: str) -> dict:
    """「8年連続11回目」「3年ぶり23回目」「初出場」を構造化する。"""
    t = normalize_text(text)
    out = {"appearance_no": None, "consecutive_no": None, "raw": text}
    if "初出場" in t:
        out["appearance_no"] = 1
        return out
    m = re.search(r"(\d+)回目", t)
    if m:
        out["appearance_no"] = int(m.group(1))
    m = re.search(r"(\d+)年連続", t)
    if m:
        out["consecutive_no"] = int(m.group(1))
    return out


# --------------------------------------------------------------------------
# 都道府県 → 地区
# --------------------------------------------------------------------------

PREF_TO_REGION = {
    "北海道": "北海道",
    "青森": "東北", "岩手": "東北", "宮城": "東北",
    "秋田": "東北", "山形": "東北", "福島": "東北",
    "茨城": "関東", "栃木": "関東", "群馬": "関東", "埼玉": "関東",
    "千葉": "関東", "神奈川": "関東", "山梨": "関東",
    "東京": "東京",
    "新潟": "北信越", "富山": "北信越", "石川": "北信越",
    "福井": "北信越", "長野": "北信越",
    "岐阜": "東海", "静岡": "東海", "愛知": "東海", "三重": "東海",
    "滋賀": "近畿", "京都": "近畿", "大阪": "近畿",
    "兵庫": "近畿", "奈良": "近畿", "和歌山": "近畿",
    "鳥取": "中国", "島根": "中国", "岡山": "中国", "広島": "中国", "山口": "中国",
    "徳島": "四国", "香川": "四国", "愛媛": "四国", "高知": "四国",
    "福岡": "九州", "佐賀": "九州", "長崎": "九州", "熊本": "九州",
    "大分": "九州", "宮崎": "九州", "鹿児島": "九州", "沖縄": "九州",
}

# --------------------------------------------------------------------------
# 夏の地方大会 → 都道府県
#   通常年の49枠 + 記念大会の分割枠
# --------------------------------------------------------------------------

QUALIFIER_TO_PREF = {
    "北北海道": "北海道", "南北海道": "北海道",
    "東東京": "東京", "西東京": "東京",
    # 記念大会の分割枠
    "北埼玉": "埼玉", "南埼玉": "埼玉",
    "東埼玉": "埼玉", "西埼玉": "埼玉",       # 1998(第80回)の分割名
    "東千葉": "千葉", "西千葉": "千葉",
    "北神奈川": "神奈川", "南神奈川": "神奈川",
    "東神奈川": "神奈川", "西神奈川": "神奈川",  # 1998(第80回)の分割名
    "東愛知": "愛知", "西愛知": "愛知",
    "北大阪": "大阪", "南大阪": "大阪",
    "東兵庫": "兵庫", "西兵庫": "兵庫",
    "北福岡": "福岡", "南福岡": "福岡",
}
# 分割されない県は同名
for _p in PREF_TO_REGION:
    if _p not in ("北海道", "東京"):
        QUALIFIER_TO_PREF.setdefault(_p, _p)


def qualifier_to_prefecture(qualifier: str) -> str | None:
    q = normalize_text(qualifier).replace("大会", "")
    return QUALIFIER_TO_PREF.get(q)


def prefecture_to_region(pref: str) -> str | None:
    p = normalize_text(pref)
    for suf in ("都", "府", "県"):
        if p.endswith(suf) and p != "京都":
            p = p[:-1]
    return PREF_TO_REGION.get(p)


def canonical_prefecture(pref: str) -> str | None:
    p = normalize_text(pref)
    if p in PREF_TO_REGION:
        return p
    for suf in ("都", "府", "県"):
        if p.endswith(suf) and p[:-1] in PREF_TO_REGION:
            return p[:-1]
    return None


# --------------------------------------------------------------------------
# ラウンド
# --------------------------------------------------------------------------

ROUND_CODES = ["r1", "r2", "r3", "qf", "sf", "f"]
ROUND_LABELS = {
    "r1": "1回戦", "r2": "2回戦", "r3": "3回戦",
    "qf": "準々決勝", "sf": "準決勝", "f": "決勝",
}
LABEL_TO_CODE = {v: k for k, v in ROUND_LABELS.items()}
LABEL_TO_CODE.update({"一回戦": "r1", "二回戦": "r2", "三回戦": "r3"})


def round_code_from_label(label: str) -> str | None:
    t = normalize_text(label)
    for lbl, code in LABEL_TO_CODE.items():
        if lbl in t:
            return code
    return None
