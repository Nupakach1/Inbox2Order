"""Kiểm thử đối chiếu SKU (BR-04, EX-07) và quy đổi đơn vị (BR-06), cảnh báo số lượng (BR-07)."""
import pytest

from sku_matcher import Catalog, normalize

PRODUCTS = [
    {"sku": "BU001", "name": "Bút bi xanh 0.5mm", "unit": "cây", "pack_unit": "hộp", "pack_size": "20", "max_normal_qty": "180"},
    {"sku": "BU004", "name": "Bút bi xanh 0.7mm", "unit": "cây", "pack_unit": "hộp", "pack_size": "20", "max_normal_qty": "180"},
    {"sku": "KE004", "name": "Kẹp bướm 32mm", "unit": "hộp", "pack_unit": "lốc", "pack_size": "10", "max_normal_qty": "100"},
    {"sku": "TH003", "name": "Kệ hồ sơ 3 tầng", "unit": "cái", "pack_unit": "", "pack_size": "1", "max_normal_qty": "30"},
    {"sku": "OLD01", "name": "Kệ hồ sơ 3 tầng gỗ", "unit": "cái", "pack_unit": "", "pack_size": "1", "max_normal_qty": "30",
     "is_active": "0"},
]
ALIASES = [{"customer_id": "KH006", "alias_text": "kệ 3 tầng", "sku": "TH003"},
           {"customer_id": "", "alias_text": "kẹp bướm số 32", "sku": "KE004"}]


@pytest.fixture
def cat():
    return Catalog(PRODUCTS, ALIASES)


def test_normalize():
    assert normalize("Vở 200tr Ô LY") == "vo 200 tr o ly"
    assert normalize("Bút bi 0.7mm.") == "but bi 0.7 mm"


def test_exact_name_matches(cat):
    m = cat.match("bút bi xanh 0.7mm")
    assert (m.sku, m.status) == ("BU004", "matched") and m.score >= 90


def test_tie_is_not_auto_matched(cat):
    m = cat.match("bút bi xanh")          # khớp cả BU001 và BU004
    assert m.status == "suggested" and {s for s, _ in m.suggestions[:2]} == {"BU001", "BU004"}


def test_customer_alias_only_for_that_customer(cat):
    assert cat.match("ke 3 tang", "KH006").sku == "TH003"
    assert cat.match("ke 3 tang", "KH006").status == "matched"


def test_unmatched_below_75(cat):
    m = cat.match("máy hủy tài liệu")
    assert m.status == "unmatched" and m.sku is None and m.score < 75


def test_inactive_sku_never_proposed(cat):
    m = cat.match("kệ hồ sơ 3 tầng gỗ")
    assert "OLD01" not in [m.sku] + [s for s, _ in m.suggestions]


def test_unit_conversion_and_anomaly(cat):
    assert cat.to_base_qty("BU001", 3, "hộp") == 60
    assert cat.to_base_qty("BU001", 3, "h") == 60
    assert cat.to_base_qty("BU001", 15, "cây") == 15
    assert cat.to_base_qty("KE004", 3, "lốc") == 30
    assert cat.to_base_qty("KE004", 3, "hop") == 3
    assert cat.to_base_qty("BU001", 2, "thùng") is None      # đơn vị không có trong quy cách → cần kiểm tra
    assert cat.to_base_qty("BU001", None, "hộp") is None
    assert cat.qty_anomaly("BU001", 200) and not cat.qty_anomaly("BU001", 180)


def test_real_catalog_loads():
    c = Catalog()
    assert len(c.products) == 120 and len(c.aliases) == 60


def test_size_tokens_kept_together():
    assert normalize("Giấy note vàng 3x3") == "giay note vang 3x3"
    c = Catalog()
    m = c.match("Giấy note vàng 3x3")
    assert (m.sku, m.status) == ("GI011", "matched")
