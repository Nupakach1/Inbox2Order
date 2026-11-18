"""Kiểm thử cách chấm điểm (mục 7.1) và các quy tắc của luồng xử lý (BR-08, BR-09, BR-12, BR-13)."""
import json
from datetime import datetime

from config import EVAL_DIR
from evaluate import align, map_category, norm
from pipeline import next_workday, ready_at


def test_normalization_rule_4_8():
    assert norm("  Bút  Gel ĐEN ") == "but gel den"
    assert norm(None) is None
    assert map_category("complaint") == "other"


def test_align_by_name_and_extra_lines():
    gt = [{"product_text": "bút gel đen"}, {"product_text": "decal A4"}]
    ai = [{"product_text": "decal A4"}, {"product_text": "but gel den"}, {"product_text": "kéo"}]
    pairs, extra = align(gt, ai)
    assert pairs == {0: 1, 1: 0} and extra == [2]


def test_br12_ready_time():
    assert ready_at(datetime(2026, 11, 2, 16, 59)) == datetime(2026, 11, 2, 16, 59)
    assert ready_at(datetime(2026, 11, 3, 20, 18)) == datetime(2026, 11, 4, 8, 0)      # TC-12
    assert ready_at(datetime(2026, 11, 7, 18, 0)) == datetime(2026, 11, 9, 8, 0)       # thứ Bảy → thứ Hai
    assert next_workday(datetime(2026, 11, 6).date()).isoformat() == "2026-11-07"     # làm cả thứ Bảy


def test_week_results_consistent():
    w = json.loads((EVAL_DIR / "results" / "pipeline_week.json").read_text(encoding="utf-8"))
    em = {e["email_id"]: e for e in w["emails"]}
    assert len(em) == 60 and all(e["status"] in ("drafted", "forwarded") for e in em.values())   # không mất email (NFR-06)
    assert em["E050"]["label"] == "possible_duplicate"                                         # BR-08
    assert {em[k]["modifies_email_id"] for k in ("E010", "E011", "E042", "E043")} == {"E002", "E007", "E037", "E038"}
    assert all(o["status"] in ("draft", "needs_review") for o in w["orders"])                  # BR-01: AI không xác nhận
    s = json.loads((EVAL_DIR / "results" / "summary.json").read_text(encoding="utf-8"))
    assert s["sku_top1"] <= s["sku_top3"] <= s["sku_dong"] and s["kpi02_uoc_tinh"] == round(1 - s["ty_le_dat_ngay"], 4)
