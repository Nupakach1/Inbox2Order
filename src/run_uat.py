"""Chạy 24 test case chấp nhận (mục 7.6) trên dữ liệu thật của tuần 02–07/11/2026 và ghi kết quả vào
evaluation/results/uat_results.json (nếu có bảng tính analysis/I2O_UAT_v1.xlsx thì ghi thêm vào cột Kết quả, Ghi chú).

Phạm vi chạy: luồng xử lý email (pipeline.py), kết quả AI đã lưu và CSDL PostgreSQL với đầy đủ ràng buộc.
Thao tác của người dùng (sửa, xác nhận, từ chối, lưu bí danh) được thực hiện bằng đúng câu lệnh mà giao diện
sẽ gửi xuống CSDL, dưới tài khoản của từng vai trò. Những test case cần SAP, máy chủ email hoặc giao diện có
đăng nhập thật được ghi Chưa chạy và chuyển sang pilot.

    python src/run_uat.py          # cần psql, createdb (PostgreSQL 14+)
"""
import json
import subprocess
from datetime import datetime

import openpyxl

from config import EVAL_DIR, ROOT
from mask_pii import has_pii
from pipeline import Week, load_inputs

DB = "i2o_uat"
UAT = ROOT / "analysis" / "I2O_UAT_v1.xlsx"
RESULTS = EVAL_DIR / "results"


def sql(q, check=True):
    r = subprocess.run(["psql", "-X", "-q", "-t", "-A", "-F", "|", "-v", "ON_ERROR_STOP=1", "-d", DB, "-c",
                        "SET search_path TO i2o; " + q], capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(r.stderr)
    return r


def val(q):
    return sql(q).stdout.strip()


def blocked(q, code):
    r = sql(q, check=False)
    return r.returncode != 0 and code in r.stderr


def uid(u):
    return f"(SELECT user_id FROM users WHERE username = '{u}')"


def oid(e):
    return f"(SELECT order_id FROM orders WHERE email_id = '{e}')"


def setup():
    subprocess.run(["dropdb", "--if-exists", DB], capture_output=True)
    subprocess.run(["createdb", DB], check=True)
    for f in (ROOT / "database/postgres/01_schema.sql", ROOT / "database/postgres/02_seed.sql",
              RESULTS / "pipeline_week.sql"):
        subprocess.run(["psql", "-X", "-q", "-v", "ON_ERROR_STOP=1", "-d", DB, "-f", str(f)], check=True,
                       capture_output=True)


def run():
    setup()
    ai = {r["email_id"]: r for n in ("dev", "test")
          for r in json.loads((RESULTS / f"ai_output_{n}.json").read_text(encoding="utf-8"))}
    emails, customers = load_inputs()
    R = {}

    def res(tc, ok, note):
        R[tc] = ("Đạt" if ok is True else "Không đạt" if ok is False else "Chưa chạy", note)

    e = val("SELECT status, category FROM emails WHERE email_id = 'E005'")
    res("TC-01", e == "drafted|new_order", f"E005: phân loại new_order, email chuyển qua Đã tạo đơn nháp ({e})")

    e = val("SELECT e.status, e.label, u.role, (SELECT count(*) FROM orders o WHERE o.email_id = 'E025') "
            "FROM emails e JOIN users u ON u.user_id = e.forwarded_to WHERE e.email_id = 'E025'")
    res("TC-02", e == "forwarded|new_customer|sales_manager|0", f"E025: {e} (trạng thái|nhãn|người nhận|số đơn)")

    e = val("SELECT string_agg(e.email_id || ':' || e.label || ':' || u.role, ', ' ORDER BY e.email_id) "
            "FROM emails e JOIN users u ON u.user_id = e.forwarded_to WHERE e.email_id IN ('E030', 'E057')")
    n = val("SELECT count(*) FROM orders WHERE email_id IN ('E030', 'E057')")
    res("TC-03", e == "E030:price_inquiry:sales_manager, E057:complaint:sales_manager" and n == "0", f"{e}; số đơn {n}")

    src = next(x for x in emails if x["email_id"] == "E009")
    masked = ai["E009"]["masked_input"]
    res("TC-04", not has_pii(masked, src) and "0123 800 829" in src["body"] and "[CHỮ KÝ]" in masked,
        f"Email gốc có số điện thoại trong chữ ký; nội dung gửi AI đã che: {ai['E009']['mask_counts']}")

    e = val(f"SELECT customer_id, requested_delivery_date, status, (SELECT count(*) FROM order_items WHERE order_id = {oid('E005')}) "
            "FROM orders WHERE email_id = 'E005'")
    res("TC-05", e == "KH010|2026-11-06|draft|3",
        f"Đơn nháp {e} (khách|ngày giao|trạng thái|số dòng). Thời gian 90 giây (NFR-01) đo khi chạy qua API ở pilot")

    e = val(f"SELECT string_agg(product_text || '→' || coalesce(sku, '-') || '(' || match_status || ')', '; ' ORDER BY line_no) "
            f"FROM order_items WHERE order_id = {oid('E009')}")
    gt = {l["product_text"]: l["sku"] for l in next(g for g in json.loads(
        (ROOT / "data/labels/ground_truth_test.json").read_text(encoding="utf-8")) if g["email_id"] == "E009")["lines"]}
    ok = all(f"{k}→{v}(" in e for k, v in gt.items())
    res("TC-06", ok, f"E009: {e}. Cả 4 dòng khớp đúng mã theo đáp án, không dòng nào phải gợi ý")

    e = val(f"SELECT i.qty_base, o.address_needs_review, o.date_needs_review, o.requested_delivery_date, "
            f"a.is_default FROM orders o JOIN order_items i USING (order_id) JOIN customer_addresses a "
            f"ON a.address_id = o.ship_address_id WHERE o.email_id = 'E004' AND i.line_no = 1")
    res("TC-07", e == "20.00|t|t|2026-11-03|t",
        f"E004: 2 lốc tập 200 ô ly = {e.split('|')[0]} cuốn; địa chỉ mặc định và ngày 03/11 được đánh dấu cần kiểm tra")

    e = val(f"SELECT o.status, string_agg(r.line_no || ':' || r.qty_missing, ',' ORDER BY r.line_no) FROM orders o "
            f"JOIN v_order_items_review r USING (order_id) WHERE o.email_id = 'E023' GROUP BY o.status")
    blk = blocked(f"UPDATE orders SET status = 'confirmed', decided_by = {uid('huong.nt')}, decided_at = now() "
                  "WHERE email_id = 'E023'", "BR-05")
    res("TC-08", e.startswith("needs_review") and "3:t" in e and blk,
        f"E023: {e} (dòng 3 thiếu số lượng); lệnh xác nhận bị CSDL chặn theo BR-05")

    e = val(f"SELECT sku, qty_base, qty_anomaly FROM v_order_items_review WHERE order_id = {oid('E026')} AND line_no = 1")
    res("TC-09", e == "BU004|720.00|t", f"E026: {e} (36 hộp = 720 cây > ngưỡng 180)")

    e = val("SELECT status, label, (SELECT count(*) FROM orders WHERE email_id = 'E050') FROM emails WHERE email_id = 'E050'")
    res("TC-10", e == "forwarded|possible_duplicate|0", f"E050 (gửi lại E047): {e}")

    e = val(f"SELECT string_agg(field_name || ':' || coalesce(old_value, '') || '→' || coalesce(new_value, ''), '; ' ORDER BY log_id) "
            f"FROM order_edit_logs WHERE source_email_id = 'E010' AND order_id = {oid('E002')}")
    n = val("SELECT count(*) FROM orders WHERE email_id = 'E010'")
    m = val("SELECT modifies_email_id FROM emails WHERE email_id = 'E010'")
    res("TC-11", "qty_raw:1→4" in e and "line_removed:dạ quang vàng" in e and n == "0" and m == "E002",
        f"E010 sửa đơn E002: {e}; không tạo đơn mới")

    e = val("SELECT to_char(ready_at AT TIME ZONE 'Asia/Ho_Chi_Minh', 'DD/MM HH24:MI') FROM orders WHERE email_id = 'E024'")
    res("TC-12", e == "04/11 08:00", f"E024 nhận 20h18 ngày 03/11, vào danh sách duyệt lúc {e}")

    rows = sql("SELECT email_id, to_char(confirm_deadline AT TIME ZONE 'Asia/Ho_Chi_Minh', 'DD/MM HH24:MI'), status "
               "FROM v_review_queue WHERE (received_at AT TIME ZONE 'Asia/Ho_Chi_Minh')::date = '2026-11-03' "
               "AND status = 'needs_review' ORDER BY confirm_deadline, received_at").stdout.strip().splitlines()
    dl = [r.split("|")[1] for r in rows]
    res("TC-13", rows and dl == sorted(dl, key=lambda s: (s[3:5], s[:2], s[6:])) and all(r.endswith("needs_review") for r in rows),
        f"Lọc Cần kiểm tra ngày 03/11: {', '.join(r.split('|')[0] + ' hạn ' + r.split('|')[1] for r in rows)}")

    sql(f"UPDATE orders SET opened_at = '2026-11-02 10:00+07', locked_by = {uid('huong.nt')} WHERE email_id = 'E005'")
    sql(f"INSERT INTO order_edit_logs (order_id, item_id, field_name, old_value, new_value, edited_by) "
        f"SELECT order_id, item_id, 'qty_base', qty_base::text, '12', {uid('huong.nt')} FROM order_items "
        f"WHERE order_id = {oid('E005')} AND line_no = 1; "
        f"UPDATE order_items SET qty_base = 12 WHERE order_id = {oid('E005')} AND line_no = 1")
    e = val(f"SELECT field_name, old_value, new_value, u.full_name, edited_at IS NOT NULL FROM order_edit_logs l "
            f"JOIN users u ON u.user_id = l.edited_by WHERE l.order_id = {oid('E005')}")
    res("TC-14", e.startswith("qty_base|10.00|12|Nguyễn Thị Hương|t"),
        f"Nhật ký: {e} (trường|cũ|mới|người sửa|có thời điểm); sửa lại bị chặn theo NFR-05: "
        f"{blocked('UPDATE order_edit_logs SET new_value = ' + chr(39) + '13' + chr(39), 'NFR-05')}")

    ok = not blocked(f"UPDATE orders SET status = 'confirmed', decided_by = {uid('huong.nt')}, decided_at = '2026-11-02 10:01+07' "
                     "WHERE email_id = 'E005'", "BR-")
    sql(f"INSERT INTO sap_sales_orders (order_id) VALUES ({oid('E005')})")
    res("TC-15", None, f"Phần trong Inbox2Order đạt: Sales Admin xác nhận được ({ok}), bản ghi Sales Order chờ gửi SAP được tạo. "
                       "Tạo Sales Order thật và gửi email xác nhận cần SAP sandbox và hộp thư, chạy ở tuần 1 pilot")

    blk = blocked(f"UPDATE orders SET status = 'confirmed', decided_by = {uid('trang.lt')}, decided_at = now() "
                  "WHERE email_id = 'E023'", "BR-05")
    res("TC-16", blk, "Xác nhận đơn E023 bị chặn: còn dòng 'bút xanh 0.5' thiếu số lượng (BR-05)")

    b1 = blocked(f"UPDATE orders SET status = 'rejected', decided_by = {uid('thu.pm')}, decided_at = now(), reject_reason = '' "
                 "WHERE email_id = 'E016'", "ck_orders_reject_reason")
    sql("UPDATE orders SET status = 'waiting_customer' WHERE email_id = 'E016'")
    e = val("SELECT status, (SELECT count(*) FROM order_items WHERE order_id = o.order_id) FROM orders o WHERE email_id = 'E016'")
    res("TC-17", b1 and e == "waiting_customer|0",
        f"E016 (không có dòng hàng): từ chối không lý do bị chặn; đề nghị bổ sung → {e.split('|')[0]}. "
        "Việc gửi email đề nghị cần hộp thư, chạy ở pilot")

    sql(f"UPDATE sap_sales_orders SET request_status = 'error', attempt_count = 1, last_error = 'mất kết nối' WHERE order_id = {oid('E005')}")
    dup = blocked(f"INSERT INTO sap_sales_orders (order_id) VALUES ({oid('E005')})", "duplicate key")
    res("TC-18", None, f"CSDL giữ đúng một bản ghi Sales Order cho mỗi đơn và lưu trạng thái lỗi để thử lại (chặn bản thứ hai: {dup}); "
                       "lời gọi API SAP thật chạy ở pilot")

    line = val(f"SELECT line_no || '|' || product_text FROM order_items WHERE order_id = {oid('E004')} AND match_status = 'suggested' LIMIT 1")
    ln, text = line.split("|")
    sql(f"UPDATE order_items SET sku = 'VO004', match_status = 'manual' WHERE order_id = {oid('E004')} AND line_no = {ln}; "
        f"INSERT INTO order_edit_logs (order_id, item_id, field_name, old_value, new_value, edited_by) SELECT order_id, item_id, "
        f"'sku', 'VO004 (gợi ý)', 'VO004', {uid('huong.nt')} FROM order_items WHERE order_id = {oid('E004')} AND line_no = {ln}; "
        f"INSERT INTO product_aliases (customer_id, alias_text, sku, created_by) VALUES ('KH011', '{text}', 'VO004', {uid('huong.nt')})")
    e = val(f"SELECT alias_id || '|' || customer_id || '|' || alias_text || '|' || sku FROM product_aliases WHERE alias_text = '{text}'")
    res("TC-19", e.endswith(f"|KH011|{text}|VO004"),
        f"Chọn lại VO004 cho dòng gợi ý của E004 và lưu bí danh {e} (mã|khách|tên gọi|SKU)")

    sql(f"INSERT INTO product_aliases (customer_id, alias_text, sku, created_by) VALUES ('KH010', 'bút xóa 12', 'BU029', {uid('trang.lt')})")
    e = val("SELECT alias_id || '|' || sku || '|' || u.full_name FROM product_aliases a JOIN users u ON u.user_id = a.created_by "
            "WHERE customer_id = 'KH010' AND alias_text = 'bút xóa 12'")
    res("TC-20", bool(e), f"Bí danh mới {e} (mã|SKU|người tạo)")

    blk = blocked("INSERT INTO product_aliases (customer_id, alias_text, sku) VALUES ('KH010', 'TẬP 200 KẺ NGANG', 'VO004')",
                  "ux_product_aliases_active")
    res("TC-21", blk, "Thêm 'TẬP 200 KẺ NGANG' cho KH010 trỏ VO004 bị chặn vì đã có bí danh này trỏ VO003; "
                      "giao diện hỏi có ngừng bí danh cũ để thay không (ngừng = status inactive rồi thêm mới)")

    k = val("SELECT count(*) FROM v_review_queue WHERE before_cutoff AND (received_at AT TIME ZONE 'Asia/Ho_Chi_Minh')::date = '2026-11-06'")
    res("TC-22", None, f"Truy vấn KPI đã kiểm thử đúng Bảng 4.1 trên bộ đơn tính tay (tests/test_db_schema.py); truy vấn cảnh báo "
                       f"16h30 ngày 06/11 trả {k} đơn chưa duyệt. Gửi cảnh báo qua email và dashboard có dữ liệu duyệt thật chạy ở pilot")

    blk = blocked(f"UPDATE orders SET status = 'confirmed', decided_by = {uid('vinh.tq')}, decided_at = now() WHERE email_id = 'E009'",
                  "BR-01")
    res("TC-23", None, f"Trưởng phòng xác nhận đơn bị CSDL chặn ({blk}). Đăng nhập theo vai trò cần bản pilot có tài khoản")

    w = Week()
    fake = dict(next(x for x in emails if x["email_id"] == "E005"))
    fake["ai"] = {"status": "timeout", "output": None, "masked_input": ai["E005"]["masked_input"]}
    w.process(fake, customers)
    o = w.orders[0]
    res("TC-24", o["status"] == "needs_review" and not o["items"] and w.emails[0]["status"] == "drafted",
        f"Khi AI không trả kết quả sau 3 lần: email E005 vẫn có đơn trống ở {o['status']} kèm ghi chú '{o['customer_note']}'")

    write_xlsx(R)
    (RESULTS / "uat_results.json").write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8")
    subprocess.run(["dropdb", DB], capture_output=True)
    for k, (r, n) in R.items():
        print(k, r, "-", n[:110])
    print({v: sum(r == v for r, _ in R.values()) for v in ("Đạt", "Không đạt", "Chưa chạy")})


def write_xlsx(R):
    if not UAT.exists():  # bảng tính UAT là tài liệu BA, không nằm trong repo mã nguồn
        return
    wb = openpyxl.load_workbook(UAT)
    ws = wb["Test case"]
    for row in range(2, ws.max_row + 1):
        tc = ws.cell(row, 1).value
        if tc in R:
            ws.cell(row, 9).value, ws.cell(row, 10).value = R[tc]
    ws2 = wb["Hướng dẫn"]
    ws2.cell(5, 1).value = f"Lần chạy: {datetime.now():%d/%m/%Y %H:%M} bằng src/run_uat.py trên dữ liệu tuần 02–07/11/2026."
    wb.save(UAT)


if __name__ == "__main__":
    run()
