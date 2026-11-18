"""Luồng xử lý email thành đơn nháp (UC-01, UC-02), chạy trên kết quả AI đã lưu.

Đây là phần logic mà n8n gọi trong bước Hiểu (Bảng 4.2); viết bằng Python để kiểm chứng quy tắc.
Thứ tự xử lý theo thời điểm nhận của cả tuần (60 email), vì email sửa đơn và email trùng
phải được đối chiếu với các email đến trước nó.

    python src/pipeline.py
        → evaluation/results/pipeline_week.json (email, đơn nháp, dòng hàng, gợi ý, nhật ký)
        → evaluation/results/pipeline_week.sql  (nạp vào PostgreSQL sau 01_schema.sql, 02_seed.sql)

Quy tắc áp dụng: BR-02, BR-03 (chuyển người phụ trách), BR-04 (đối chiếu SKU), BR-05 (Cần kiểm tra),
BR-06 (quy đổi), BR-07 (số lượng bất thường), BR-08 (trùng trong 24 giờ), BR-09 (email sửa đơn),
BR-12 (giờ đưa vào danh sách duyệt), BR-13 (địa chỉ và ngày giao mặc định), EX-03/EX-04 (AI lỗi).
"""
import csv
import json
import re
from datetime import datetime, timedelta

from rapidfuzz import fuzz

from config import (CUTOFF_HOUR, DUPLICATE_SIMILARITY, DUPLICATE_WINDOW_HOURS, EVAL_DIR, GENERATED_DIR,
                    WORK_START_HOUR)
from sku_matcher import Catalog, normalize

RESULTS = EVAL_DIR / "results"
MANAGER, FIRST_SALES_ADMIN = "vinh.tq", "huong.nt"   # người nhận email được chuyển (FR-04, BR-08)
LABEL_BY_CATEGORY = {"price_inquiry": "price_inquiry", "complaint": "complaint", "other": "other"}


def next_workday(d):
    """Ngày làm việc kế tiếp; An Phát làm thứ Hai đến thứ Bảy (26 ngày/tháng)."""
    d = d + timedelta(days=1)
    while d.weekday() == 6:
        d += timedelta(days=1)
    return d


def ready_at(received):
    """BR-12: trước 17h00 vào danh sách ngay; sau 17h00 (hoặc Chủ nhật) sẵn sàng 8h00 ngày làm việc kế tiếp."""
    if received.hour < CUTOFF_HOUR and received.weekday() != 6:
        return received
    return datetime.combine(next_workday(received.date()), datetime.min.time()).replace(hour=WORK_START_HOUR)


def body_only(masked):
    return masked.split("\n\n", 1)[1] if "\n\n" in masked else masked


def load_inputs():
    emails = {}
    for name in ("dev", "test"):
        res = RESULTS / f"ai_output_{name}.json"
        if not res.exists():          # chưa chạy tập này
            continue
        for e in json.loads((GENERATED_DIR / f"emails_{name}.json").read_text(encoding="utf-8")):
            emails[e["email_id"]] = e
        for r in json.loads(res.read_text(encoding="utf-8")):
            emails[r["email_id"]]["ai"] = r
    with open(GENERATED_DIR / "customers.csv", encoding="utf-8-sig", newline="") as f:
        customers = {c["email"].lower(): c for c in csv.DictReader(f)}
    return sorted(emails.values(), key=lambda e: e["received_at"]), customers


class Week:
    def __init__(self):
        self.cat = Catalog()
        self.emails, self.orders, self.logs = [], [], []
        self.addresses = {}          # customer_id -> [địa chỉ], phần tử đầu là mặc định
        self.by_email = {}

    def build_lines(self, ai_lines, customer_id):
        lines = []
        for i, l in enumerate(ai_lines, 1):
            m = self.cat.match(l.get("product_text", ""), customer_id)
            qty = l.get("qty")
            qty_base = self.cat.to_base_qty(m.sku, qty, l.get("unit")) if m.status == "matched" else None
            if m.status == "suggested" and qty is not None:          # tạm quy đổi theo mã gợi ý số 1
                qty_base = self.cat.to_base_qty(m.sku, qty, l.get("unit"))
            lines.append({
                "line_no": i, "product_text": l.get("product_text", ""), "qty_raw": qty, "unit_raw": l.get("unit"),
                "sku": m.sku if m.status in ("matched", "suggested") else None, "match_score": m.score,
                "match_status": m.status, "qty_base": qty_base, "top3": m.suggestions,
                "suggestions": m.suggestions if m.status != "matched" else [],
                "qty_anomaly": self.cat.qty_anomaly(m.sku, qty_base) if m.status != "unmatched" else False,
                "unit_unknown": qty is not None and m.sku is not None and qty_base is None,
            })
        return lines

    @staticmethod
    def needs_review(order):
        if not order["customer_id"] or not order["items"] or order.get("force_review"):
            return True
        return any(it["match_status"] != "matched" or it["qty_base"] is None or it["qty_anomaly"]
                   for it in order["items"])

    def process(self, e, customers):
        rec = {"email_id": e["email_id"], "received_at": e["received_at"], "from_email": e["from_email"],
               "subject": e["subject"], "status": "classified", "category": None, "label": None,
               "customer_id": None, "forwarded_to": None, "modifies_email_id": None, "note": None}
        self.emails.append(rec)
        ai = e.get("ai") or {}
        out = ai.get("output")
        cust = customers.get(e["from_email"].lower())
        rec["customer_id"] = cust["customer_id"] if cust else None
        received = datetime.fromisoformat(e["received_at"])
        if out is None:                                    # EX-03, EX-04: AI lỗi → đơn trống Cần kiểm tra
            rec["category"] = "other"
            if cust:
                self.new_order(rec, cust, {"lines": []}, received, note="Mô hình AI lỗi, cần nhập tay (EX-03)")
            else:
                rec.update(status="forwarded", label="new_customer", forwarded_to=MANAGER)
            return
        rec["category"] = out["category"]
        if not cust:                                       # BR-02
            rec.update(status="forwarded", label="new_customer", forwarded_to=MANAGER)
            return
        if out["category"] in LABEL_BY_CATEGORY:           # BR-03
            rec.update(status="forwarded", label=LABEL_BY_CATEGORY[out["category"]], forwarded_to=MANAGER)
            return
        if out["category"] == "modify_order":              # BR-09
            self.modify(rec, cust, out, received)
            return
        dup = self.find_duplicate(rec, e, received)        # BR-08
        if dup:
            rec.update(status="forwarded", label="possible_duplicate", forwarded_to=FIRST_SALES_ADMIN,
                       note=f"Nội dung trùng email {dup}")
            return
        self.new_order(rec, cust, out, received)

    def find_duplicate(self, rec, e, received):
        text = normalize(body_only(e["ai"]["masked_input"]))
        for prev in reversed(self.emails[:-1]):
            if prev["customer_id"] != rec["customer_id"] or prev["email_id"] not in self.by_email:
                continue
            if received - datetime.fromisoformat(prev["received_at"]) > timedelta(hours=DUPLICATE_WINDOW_HOURS):
                continue
            if fuzz.token_set_ratio(text, normalize(body_only(prev["masked"]))) >= DUPLICATE_SIMILARITY:
                return prev["email_id"]
        return None

    def new_order(self, rec, cust, out, received, note=None, adjusts=None):
        cid = cust["customer_id"]
        addrs = self.addresses.setdefault(cid, [cust["default_address"]])
        addr, addr_review = out.get("delivery_address"), False
        if addr:
            if addr not in addrs:
                addrs.append(addr)
        else:
            addr, addr_review = addrs[0], True             # BR-13
        date, date_review = out.get("delivery_date"), False
        if not date:
            date, date_review = next_workday(received.date()).isoformat(), True   # BR-13
        order = {"order_id": len(self.orders) + 1, "email_id": rec["email_id"], "customer_id": cid,
                 "ship_address": addr, "address_needs_review": addr_review,
                 "requested_delivery_date": date, "date_needs_review": date_review,
                 "customer_note": "; ".join(x for x in (out.get("note"), note) if x) or None,
                 "ready_at": ready_at(received).isoformat(timespec="minutes"), "adjusts_order_id": adjusts,
                 "items": self.build_lines(out.get("lines", []), cid)}
        order["status"] = "needs_review" if self.needs_review(order) else "draft"   # BR-05
        order["initial"] = {"status": order["status"], "items": json.loads(json.dumps(order["items"]))}
        self.orders.append(order)
        self.by_email[rec["email_id"]] = order
        rec["status"] = "drafted"
        return order

    def modify(self, rec, cust, out, received):
        # Đơn gốc: trong các đơn của cùng khách nhận trong 24 giờ trước, chọn đơn có dòng hàng giống
        # các dòng được nhắc trong email sửa nhất; hòa điểm thì lấy đơn gần nhất.
        target, best = None, -1
        texts = [normalize(l.get("product_text", "")) for l in out.get("lines", [])]
        for prev in reversed(self.emails[:-1]):
            if prev["customer_id"] != cust["customer_id"] or prev["email_id"] not in self.by_email:
                continue
            if received - datetime.fromisoformat(prev["received_at"]) > timedelta(hours=DUPLICATE_WINDOW_HOURS):
                continue
            cand = self.by_email[prev["email_id"]]
            score = sum(max((fuzz.token_set_ratio(t, normalize(it["product_text"])) for it in cand["items"]), default=0)
                        for t in texts)
            if score > best:
                target, best = cand, score
                rec["modifies_email_id"] = prev["email_id"]
        if target is None:                                 # không tìm thấy đơn gốc → đơn mới, Cần kiểm tra
            o = self.new_order(rec, cust, out, received, note="Email sửa đơn nhưng không tìm thấy đơn gốc")
            o["status"] = "needs_review"
            return
        if target.get("status") == "confirmed":            # đơn đã xác nhận → đơn điều chỉnh
            self.new_order(rec, cust, out, received, adjusts=target["order_id"])
            return
        for l in out.get("lines", []):
            action = l.get("action") or "update"
            m = self.cat.match(l.get("product_text", ""), cust["customer_id"])
            hit = next((it for it in target["items"] if it["sku"] and it["sku"] == m.sku), None) \
                or max(target["items"], key=lambda it: fuzz.token_set_ratio(normalize(it["product_text"]),
                                                                          normalize(l.get("product_text", ""))),
                       default=None)
            same = hit and (hit["sku"] == m.sku or fuzz.token_set_ratio(
                normalize(hit["product_text"]), normalize(l.get("product_text", ""))) >= 90)
            if action == "remove":
                if same:
                    target["items"].remove(hit)
                    self.log(target, hit, "line_removed", hit["product_text"], None, rec["email_id"])
                else:                                      # không tìm thấy dòng cần bỏ → để người kiểm tra
                    target["customer_note"] = "; ".join(x for x in (target["customer_note"],
                                                        f"{rec['email_id']}: bỏ '{l.get('product_text')}' nhưng không thấy dòng này") if x)
                    target["force_review"] = True
            elif action == "update" and same and l.get("qty") is not None:
                new_base = self.cat.to_base_qty(hit["sku"], l["qty"], l.get("unit") or hit["unit_raw"])
                self.log(target, hit, "qty_raw", hit["qty_raw"], l["qty"], rec["email_id"])
                if new_base != hit["qty_base"]:
                    self.log(target, hit, "qty_base", hit["qty_base"], new_base, rec["email_id"])
                hit.update(qty_raw=l["qty"], unit_raw=l.get("unit") or hit["unit_raw"], qty_base=new_base,
                           qty_anomaly=self.cat.qty_anomaly(hit["sku"], new_base))
            else:                                          # thêm dòng mới hoặc không xác định được dòng cũ
                new = self.build_lines([l], cust["customer_id"])[0]
                new["line_no"] = max([it["line_no"] for it in target["items"]], default=0) + 1
                target["items"].append(new)
                self.log(target, new, "line_added", None, new["product_text"], rec["email_id"])
        target["status"] = "needs_review" if self.needs_review(target) else "draft"
        rec["status"] = "drafted"

    def log(self, order, item, field, old, new, email_id):
        self.logs.append({"order_id": order["order_id"], "line_no": item["line_no"] if item else None,
                          "field_name": field, "old_value": None if old is None else str(old),
                          "new_value": None if new is None else str(new), "source_email_id": email_id})


def run():
    emails, customers = load_inputs()
    w = Week()
    for e in emails:
        w.process(e, customers)
        w.emails[-1]["masked"] = (e.get("ai") or {}).get("masked_input", "")
    for r in w.emails:
        r.pop("masked", None)
    data = {"emails": w.emails, "orders": w.orders, "logs": w.logs, "addresses": w.addresses}
    (RESULTS / "pipeline_week.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    (RESULTS / "pipeline_week.sql").write_text(to_sql(data), encoding="utf-8")
    n_rev = sum(o["status"] == "needs_review" for o in w.orders)
    print(f"{len(w.emails)} email → {len(w.orders)} đơn nháp ({n_rev} Cần kiểm tra), "
          f"{sum(r['status'] == 'forwarded' for r in w.emails)} email chuyển người phụ trách, {len(w.logs)} dòng nhật ký")
    return data


def q(v):
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return repr(v)
    return "'" + str(v).replace("'", "''") + "'"


def to_sql(d):
    TZ = "+07:00"
    out = ["-- Kết quả luồng xử lý 60 email tuần 02–07/11/2026, sinh bởi src/pipeline.py",
           "SET search_path TO i2o;", "BEGIN;"]
    for cid, addrs in d["addresses"].items():
        for a in addrs[1:]:
            out.append(f"INSERT INTO customer_addresses (customer_id, address_text) VALUES ({q(cid)}, {q(a)});")
    uid = lambda u: f"(SELECT user_id FROM users WHERE username = {q(u)})"  # noqa: E731
    for r in d["emails"]:
        out.append(f"UPDATE emails SET status = {q(r['status'])}, category = {q(r['category'])}, label = {q(r['label'])}, "
                   f"modifies_email_id = {q(r['modifies_email_id'])}, "
                   f"forwarded_to = {uid(r['forwarded_to']) if r['forwarded_to'] else 'NULL'} WHERE email_id = {q(r['email_id'])};")
    for o in d["orders"]:
        addr = (f"(SELECT address_id FROM customer_addresses WHERE customer_id = {q(o['customer_id'])} "
                f"AND address_text = {q(o['ship_address'])} LIMIT 1)")
        out.append("INSERT INTO orders (email_id, customer_id, ship_address_id, requested_delivery_date, customer_note, "
                   "status, address_needs_review, date_needs_review, ready_at, created_at) OVERRIDING SYSTEM VALUE "
                   f"SELECT {q(o['email_id'])}, {q(o['customer_id'])}, {addr}, {q(o['requested_delivery_date'])}, "
                   f"{q(o['customer_note'])}, {q(o['status'])}, {q(o['address_needs_review'])}, {q(o['date_needs_review'])}, "
                   f"{q(o['ready_at'] + TZ)}, e.received_at FROM emails e WHERE e.email_id = {q(o['email_id'])};")
        oid = f"(SELECT order_id FROM orders WHERE email_id = {q(o['email_id'])})"
        for it in o["items"]:
            out.append("INSERT INTO order_items (order_id, line_no, product_text, qty_raw, unit_raw, sku, qty_base, "
                       f"match_score, match_status) VALUES ({oid}, {it['line_no']}, {q(it['product_text'])}, "
                       f"{q(it['qty_raw'])}, {q(it['unit_raw'])}, {q(it['sku'])}, {q(it['qty_base'])}, "
                       f"{it['match_score']}, {q(it['match_status'])});")
            iid = f"(SELECT item_id FROM order_items WHERE order_id = {oid} AND line_no = {it['line_no']})"
            for rank, (sku, sc) in enumerate(it["suggestions"], 1):
                out.append(f"INSERT INTO order_item_suggestions (item_id, rank, sku, score) VALUES ({iid}, {rank}, {q(sku)}, {sc});")
    for lg in d["logs"]:
        oid = f"(SELECT order_id FROM orders ORDER BY order_id OFFSET {lg['order_id'] - 1} LIMIT 1)"
        item = ("NULL" if lg["field_name"] == "line_removed" or lg["line_no"] is None else
                f"(SELECT item_id FROM order_items WHERE order_id = {oid} AND line_no = {lg['line_no']})")
        out.append("INSERT INTO order_edit_logs (order_id, item_id, field_name, old_value, new_value, source_email_id, edited_at) "
                   f"SELECT {oid}, {item}, {q(lg['field_name'])}, {q(lg['old_value'])}, {q(lg['new_value'])}, "
                   f"{q(lg['source_email_id'])}, received_at FROM emails WHERE email_id = {q(lg['source_email_id'])};")
    out += ["COMMIT;", ""]
    return "\n".join(out)


if __name__ == "__main__":
    run()
