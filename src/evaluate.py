"""Chấm kết quả AI trên tập kiểm tra theo đúng cách chấm ở mục 7.1 báo cáo.

    python src/evaluate.py
        → evaluation/results/scores_by_field.csv, sku_topk.csv, error_log.csv, summary.json

Chỉ đọc ai_output_test.json (kết quả AI lưu nguyên) và pipeline_week.json (đơn nháp hệ thống tạo ra);
đáp án lấy từ data/labels/ground_truth_test.json. Không sửa kết quả AI trước khi chấm.
"""
import csv
import json

from rapidfuzz import fuzz
from unidecode import unidecode

from config import EVAL_DIR, LABELS_DIR
from sku_matcher import Catalog

RESULTS = EVAL_DIR / "results"
ORDER_CATS = ("new_order", "modify_order")
FIELDS = ["Khách hàng", "Tên sản phẩm", "Số lượng", "Đơn vị", "Ngày giao", "Địa chỉ giao"]


def norm(s):
    """Chuẩn hóa để so: chữ thường, bỏ dấu, bỏ khoảng trắng thừa (mục 7.1)."""
    return " ".join(unidecode(str(s)).lower().split()) if s is not None else None


def num(x):
    return None if x is None else float(x)


def map_category(c):
    return "other" if c == "complaint" else c          # đáp án gộp khiếu nại vào nhóm khác


def align(gt_lines, ai_lines):
    """Ghép dòng AI với dòng đáp án theo độ giống tên (tham lam); trả cặp chỉ số và dòng AI thừa."""
    pairs, used = {}, set()
    scores = sorted(((fuzz.token_set_ratio(norm(g["product_text"]), norm(a.get("product_text"))), gi, ai)
                     for gi, g in enumerate(gt_lines) for ai, a in enumerate(ai_lines)), reverse=True)
    for sc, gi, ai in scores:
        if sc >= 60 and gi not in pairs and ai not in used:
            pairs[gi] = ai
            used.add(ai)
    extra = [ai for ai in range(len(ai_lines)) if ai not in used]
    return pairs, extra


def evaluate():
    gt = {g["email_id"]: g for g in json.loads((LABELS_DIR / "ground_truth_test.json").read_text(encoding="utf-8"))}
    ai = {r["email_id"]: r for r in json.loads((RESULTS / "ai_output_test.json").read_text(encoding="utf-8"))}
    week = json.loads((RESULTS / "pipeline_week.json").read_text(encoding="utf-8"))
    sys_email = {e["email_id"]: e for e in week["emails"]}
    sys_order = {o["email_id"]: o for o in week["orders"]}
    cat = Catalog()

    cls_ok = sum(map_category((ai[k]["output"] or {}).get("category")) == gt[k]["category"] for k in gt)
    tally = {f: [0, 0] for f in FIELDS}
    errors, sku_rows, order_rows = [], [], []

    def check(eid, field, ok, group, detail):
        tally[field][0] += ok
        tally[field][1] += 1
        if not ok:
            errors.append({"email_id": eid, "truong": field, "nhom_loi": group, "chi_tiet": detail})
        return ok

    for eid, g in sorted(gt.items()):
        if g["category"] not in ORDER_CATS:
            continue
        out = ai[eid]["output"] or {"lines": []}
        cust = sys_email[eid]["customer_id"]
        good = check(eid, "Khách hàng", cust == g["customer_id"], "Sai khách hàng", f"{cust} ≠ {g['customer_id']}")
        good &= check(eid, "Ngày giao", out.get("delivery_date") == g["delivery_date"], "Sai ngày giao",
                      f"{out.get('delivery_date')} ≠ {g['delivery_date']}")
        a_addr, g_addr = norm(out.get("delivery_address")), norm(g["delivery_address"])
        good &= check(eid, "Địa chỉ giao", a_addr == g_addr,
                      "Bịa thông tin không có trong email" if a_addr and not g_addr else "Sai địa chỉ giao",
                      f"{out.get('delivery_address')} ≠ {g['delivery_address']}")
        pairs, extra = align(g["lines"], out["lines"])
        draft = sys_order.get(eid)
        for gi, gl in enumerate(g["lines"]):
            al = out["lines"][pairs[gi]] if gi in pairs else None
            if al is None:
                for f in ("Tên sản phẩm", "Số lượng", "Đơn vị"):
                    check(eid, f, False, "Sai hoặc thiếu SKU" if f == "Tên sản phẩm" else "Sai số lượng hoặc đơn vị",
                          f"Thiếu dòng '{gl['product_text']}'")
                good = False
            else:
                good &= check(eid, "Tên sản phẩm", norm(al["product_text"]) == norm(gl["product_text"]),
                              "Tên ghi khác email", f"'{al['product_text']}' ≠ '{gl['product_text']}'")
                good &= check(eid, "Số lượng", num(al.get("qty")) == num(gl["qty"]), "Sai số lượng hoặc đơn vị",
                              f"{al.get('qty')} ≠ {gl['qty']} ({gl['product_text']})")
                good &= check(eid, "Đơn vị", norm(al.get("unit")) == norm(gl["unit"]), "Sai số lượng hoặc đơn vị",
                              f"{al.get('unit')} ≠ {gl['unit']} ({gl['product_text']})")
            # Đối chiếu SKU trên tên AI trích xuất (top-1, top-3) và trên tên trong đáp án (để tách lỗi AI và lỗi đối chiếu)
            m = cat.match(al["product_text"], cust) if al else None
            m_gt = cat.match(gl["product_text"], g["customer_id"])
            top = [s for s, _ in (m.suggestions if m else [])]
            sku_rows.append({"email_id": eid, "ten_dap_an": gl["product_text"], "sku_dap_an": gl["sku"],
                             "ten_ai": al["product_text"] if al else "", "top1": top[0] if top else "",
                             "diem": m.score if m else "", "trang_thai": m.status if m else "thiếu dòng",
                             "top3": " ".join(top), "dung_top1": bool(top) and top[0] == gl["sku"],
                             "dung_top3": gl["sku"] in top,
                             "top1_tren_ten_dap_an": (m_gt.suggestions or [("", 0)])[0][0] == gl["sku"]})
            if eid in sys_order and draft is not None and g["category"] == "new_order":
                it = next((x for x in draft["initial"]["items"] if al and x["product_text"] == al["product_text"]), None)
                sku_ok = it is not None and it["sku"] == gl["sku"]
                base_ok = it is not None and num(it["qty_base"]) == num(gl["qty_base"])
                if not sku_ok:
                    good = False
                    errors.append({"email_id": eid, "truong": "SKU trên đơn nháp", "nhom_loi": "Sai hoặc thiếu SKU",
                                   "chi_tiet": f"'{gl['product_text']}': điền {it['sku'] if it else None}, đúng {gl['sku']}"
                                               f" ({it['match_status'] if it else 'thiếu'})"})
                elif not base_ok and gl["qty_base"] is not None:
                    good = False
                    errors.append({"email_id": eid, "truong": "Số lượng quy đổi", "nhom_loi": "Sai số lượng hoặc đơn vị",
                                   "chi_tiet": f"'{gl['product_text']}': {it['qty_base']} ≠ {gl['qty_base']}"})
        for ai_i in extra:
            good = False
            errors.append({"email_id": eid, "truong": "Dòng thừa", "nhom_loi": "Bịa thông tin không có trong email",
                           "chi_tiet": out["lines"][ai_i].get("product_text")})
        if g["category"] == "new_order" and g["customer_id"]:
            order_rows.append({"email_id": eid, "dat_ngay": bool(good),
                               "trang_thai_don": draft["initial"]["status"] if draft else ""})

    n_ok = sum(r["dat_ngay"] for r in order_rows)
    top1 = sum(r["dung_top1"] for r in sku_rows)
    top3 = sum(r["dung_top3"] for r in sku_rows)
    summary = {
        "so_email": len(gt), "phan_loai_dung": cls_ok, "ty_le_phan_loai": round(cls_ok / len(gt), 4),
        "truong": {f: {"dung": c, "tong": t, "ty_le": round(c / t, 4)} for f, (c, t) in tally.items()},
        "sku_dong": len(sku_rows), "sku_top1": top1, "sku_top3": top3,
        "sku_top1_tren_ten_dap_an": sum(r["top1_tren_ten_dap_an"] for r in sku_rows),
        "don_cham": len(order_rows), "don_dat_ngay": n_ok, "ty_le_dat_ngay": round(n_ok / len(order_rows), 4),
        "kpi02_uoc_tinh": round(1 - n_ok / len(order_rows), 4),
        "nhom_loi": {}, "bia_thong_tin": sum(e["nhom_loi"].startswith("Bịa") for e in errors),
    }
    for e in errors:
        summary["nhom_loi"][e["nhom_loi"]] = summary["nhom_loi"].get(e["nhom_loi"], 0) + 1
    write_csv("scores_by_field.csv", [{"truong": f, "dung": c, "tong": t, "ty_le": f"{c / t:.4f}"} for f, (c, t) in tally.items()]
              + [{"truong": "Phân loại email", "dung": cls_ok, "tong": len(gt), "ty_le": f"{cls_ok / len(gt):.4f}"}])
    write_csv("sku_topk.csv", sku_rows)
    write_csv("error_log.csv", errors or [{"email_id": "", "truong": "", "nhom_loi": "", "chi_tiet": ""}])
    write_csv("orders_first_pass.csv", order_rows)
    (RESULTS / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def write_csv(name, rows):
    with open(RESULTS / name, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    evaluate()
