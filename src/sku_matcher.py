"""Đối chiếu tên gọi của khách với danh mục SKU và bí danh (BR-04, FR-06) và quy đổi đơn vị (BR-06, FR-07).

Cách tính (mục 2.5 và 7.3 báo cáo): chuẩn hóa bằng unidecode + chữ thường, so bằng
rapidfuzz.fuzz.token_set_ratio với cả tên SKU lẫn bí danh (bí danh riêng của khách và bí danh chung).
Ngưỡng lấy từ config.py: ≥ 90 khớp; 75–89 gợi ý 3 mã; < 75 không khớp.
Khi hai mã cùng đạt điểm cao nhất, hệ thống không tự chọn mà coi như chưa chắc (suggested),
theo nguyên tắc mọi chỗ không chắc phải hiện cho người thấy.
"""
import csv
import re
from dataclasses import dataclass, field

from rapidfuzz import fuzz
from unidecode import unidecode

from config import GENERATED_DIR, SKU_MATCH_THRESHOLD, SKU_SUGGEST_THRESHOLD, SKU_SUGGEST_TOP_K

UNIT_ABBR = {"h": "hop", "hp": "hop", "th": "thung", "t": "thung", "c": "cai", "l": "loc"}


def normalize(text):
    """Chữ thường, bỏ dấu, tách số khỏi chữ (200tr → 200 tr, 0.7mm → 0.7 mm), bỏ ký tự thừa."""
    s = unidecode(text or "").lower()
    s = re.sub(r"(\d)\s*x\s*(\d)", r"\1X\2", s)          # giữ kích thước 3x3, 60x80 thành một từ
    s = re.sub(r"(\d)([a-z])", r"\1 \2", s)
    s = re.sub(r"([a-z])(\d)", r"\1 \2", s)
    s = re.sub(r"[^a-zX0-9. ]+", " ", s)
    s = re.sub(r"(?<!\d)\.|\.(?!\d)", " ", s)
    return re.sub(r"\s+", " ", s).strip().replace("X", "x")


def norm_unit(u):
    u = normalize(u).replace(" ", "")
    return UNIT_ABBR.get(u, u)


@dataclass
class Match:
    sku: str | None
    score: int
    status: str                      # matched, suggested, unmatched
    suggestions: list = field(default_factory=list)   # [(sku, score)] 3 mã điểm cao nhất (luôn có, để đo top-3)


class Catalog:
    def __init__(self, products=None, aliases=None):
        if products is None:
            with open(GENERATED_DIR / "products.csv", encoding="utf-8-sig", newline="") as f:
                products = list(csv.DictReader(f))
        if aliases is None:
            with open(GENERATED_DIR / "product_aliases.csv", encoding="utf-8-sig", newline="") as f:
                aliases = list(csv.DictReader(f))
        self.products = {p["sku"]: p for p in products}
        self.active = {s for s, p in self.products.items() if str(p.get("is_active", "1")).lower() not in ("0", "false")}
        self.names = [(normalize(p["name"]), p["sku"]) for p in products]
        self.aliases = [(a.get("customer_id") or None, normalize(a["alias_text"]), a["sku"]) for a in aliases]

    def candidates(self, customer_id):
        yield from self.names
        for cid, text, sku in self.aliases:
            if cid is None or cid == customer_id:
                yield text, sku

    def match(self, product_text, customer_id=None):
        q = normalize(product_text)
        best = {}
        for text, sku in self.candidates(customer_id):
            if sku not in self.active:          # EX-07: mã ngừng kinh doanh không được đề xuất
                continue
            sc = fuzz.token_set_ratio(q, text)
            tie = fuzz.ratio(q, text)
            if sku not in best or (sc, tie) > best[sku]:
                best[sku] = (sc, tie)
        ranked = sorted(best.items(), key=lambda kv: (-kv[1][0], -kv[1][1], kv[0]))
        top = [(sku, int(round(s[0]))) for sku, s in ranked[:SKU_SUGGEST_TOP_K]]
        if not top:
            return Match(None, 0, "unmatched")
        sku, score = top[0]
        tied = len(top) > 1 and top[1][1] == score
        if score >= SKU_MATCH_THRESHOLD and not tied:
            return Match(sku, score, "matched", top)
        if score >= SKU_SUGGEST_THRESHOLD:
            return Match(sku, score, "suggested", top)
        return Match(None, score, "unmatched", top)

    def to_base_qty(self, sku, qty, unit):
        """Quy đổi ra đơn vị bán (BR-06). Trả None nếu thiếu số lượng hoặc không nhận ra đơn vị."""
        if qty is None or sku is None:
            return None
        p = self.products[sku]
        if not unit:
            return float(qty)
        u = norm_unit(unit)
        if u == norm_unit(p["unit"]):
            return float(qty)
        if p.get("pack_unit") and u == norm_unit(p["pack_unit"]):
            return float(qty) * int(p["pack_size"])
        return None

    def qty_anomaly(self, sku, qty_base):
        """BR-07: số lượng vượt ngưỡng bất thường của mã hàng."""
        return sku is not None and qty_base is not None and qty_base > int(self.products[sku]["max_normal_qty"])
