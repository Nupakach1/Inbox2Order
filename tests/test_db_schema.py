"""Kiểm thử thiết kế dữ liệu (mục 5.8): lược đồ chạy được trên PostgreSQL, ràng buộc giữ đúng quy tắc
nghiệp vụ, truy vấn KPI tính đúng theo Bảng 4.1, tài liệu MongoDB mẫu đúng cấu trúc.

Phần PostgreSQL cần lệnh psql và createdb trên máy (PostgreSQL 14+); không có thì được bỏ qua.
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PG = ROOT / "database" / "postgres"
MONGO = ROOT / "database" / "mongodb"
DB = f"i2o_test_{os.getpid()}"

need_pg = pytest.mark.skipif(not (shutil.which("psql") and shutil.which("createdb")), reason="không có PostgreSQL")


def psql(sql, check=True):
    r = subprocess.run(["psql", "-X", "-q", "-t", "-A", "-v", "ON_ERROR_STOP=1", "-d", DB, "-c",
                        "SET search_path TO i2o; " + sql], capture_output=True, text=True)
    if check and r.returncode:
        raise AssertionError(r.stderr)
    return r


def fails(sql, msg):
    r = psql(sql, check=False)
    assert r.returncode != 0 and msg in r.stderr, r.stderr or "lệnh lẽ ra phải bị chặn"


@pytest.fixture(scope="module")
def db():
    if subprocess.run(["createdb", DB], capture_output=True).returncode:
        pytest.skip("không tạo được CSDL thử")
    for f in ("01_schema.sql", "02_seed.sql"):
        subprocess.run(["psql", "-X", "-q", "-v", "ON_ERROR_STOP=1", "-d", DB, "-f", str(PG / f)],
                       check=True, capture_output=True)
    yield
    subprocess.run(["dropdb", DB], capture_output=True)


def add_item(email_id):
    psql("INSERT INTO order_items (order_id, line_no, product_text, qty_raw, sku, qty_base, match_score, match_status) "
         f"SELECT order_id, 1, 'bút bi xanh', 1, 'BU001', 20, 100, 'matched' FROM orders WHERE email_id = '{email_id}'")


def uid(username):
    return f"(SELECT user_id FROM users WHERE username = '{username}')"


@need_pg
def test_seed_counts(db):
    out = psql("SELECT (SELECT count(*) FROM products), (SELECT count(*) FROM product_aliases), "
               "(SELECT count(*) FROM customers), (SELECT count(*) FROM customer_addresses WHERE is_default), "
               "(SELECT count(*) FROM emails WHERE status = 'received'), (SELECT count(*) FROM users)").stdout.strip()
    assert out == "120|60|30|30|60|5"


@need_pg
def test_br01_only_sales_admin_decides(db):
    fails("INSERT INTO orders (email_id, customer_id, status, ready_at) VALUES ('E001', 'KH001', 'confirmed', now())",
          "BR-01")
    psql("INSERT INTO orders (email_id, customer_id, status, ready_at) VALUES ('E002', 'KH001', 'draft', now())")
    add_item("E002")
    fails(f"UPDATE orders SET status = 'confirmed', decided_by = {uid('vinh.tq')}, decided_at = now() "
          "WHERE email_id = 'E002'", "BR-01")
    fails("UPDATE orders SET status = 'confirmed', decided_at = now() WHERE email_id = 'E002'", "BR-01")  # thiếu người quyết định
    fails(f"UPDATE orders SET status = 'rejected', decided_by = {uid('huong.nt')}, decided_at = now(), "
          "reject_reason = ' ' WHERE email_id = 'E002'", "ck_orders_reject_reason")
    psql(f"UPDATE orders SET status = 'confirmed', decided_by = {uid('huong.nt')}, decided_at = now() "
         "WHERE email_id = 'E002'")
    fails("UPDATE orders SET status = 'draft' WHERE email_id = 'E002'", "BR-09")


@need_pg
def test_sap_only_for_confirmed_and_unique(db):
    psql("INSERT INTO orders (email_id, customer_id, status, ready_at) VALUES ('E003', 'KH002', 'draft', now())")
    fails("INSERT INTO sap_sales_orders (order_id) SELECT order_id FROM orders WHERE email_id = 'E003'", "BR-01")
    fails("INSERT INTO orders (email_id, customer_id, status, ready_at) VALUES ('E003', 'KH002', 'draft', now())",
          "duplicate key")


@need_pg
def test_edit_log_append_only_and_alias_unique(db):
    psql("INSERT INTO orders (email_id, customer_id, status, ready_at) VALUES ('E004', 'KH011', 'needs_review', now())")
    psql("INSERT INTO order_items (order_id, line_no, product_text, qty_raw, unit_raw, sku, qty_base, match_score, "
         "match_status) SELECT order_id, 1, 'tập 200 ô ly', 2, 'lốc', 'VO004', 20, 80, 'suggested' "
         "FROM orders WHERE email_id = 'E004'")
    psql(f"INSERT INTO order_edit_logs (order_id, item_id, field_name, old_value, new_value, edited_by) "
         f"SELECT o.order_id, i.item_id, 'sku', 'VO004', 'VO005', {uid('trang.lt')} FROM orders o "
         "JOIN order_items i USING (order_id) WHERE o.email_id = 'E004'")
    fails("UPDATE order_edit_logs SET new_value = 'VO006'", "NFR-05")
    fails("DELETE FROM order_edit_logs", "NFR-05")
    psql("DELETE FROM order_items WHERE product_text = 'tập 200 ô ly'")  # xóa dòng: nhật ký vẫn còn
    assert psql("SELECT count(*) FROM order_edit_logs WHERE item_id IS NULL").stdout.strip() == "1"
    alias = psql("SELECT customer_id, alias_text FROM product_aliases WHERE customer_id IS NOT NULL LIMIT 1").stdout.strip()
    cid, text = alias.split("|")
    fails(f"INSERT INTO product_aliases (customer_id, alias_text, sku) VALUES ('{cid}', upper('{text}'), 'BU001')",
          "ux_product_aliases_active")
    new_id = psql(f"INSERT INTO product_aliases (customer_id, alias_text, sku, created_by) VALUES "
                  f"('{cid}', 'tên gọi mới', 'BU001', {uid('trang.lt')}) RETURNING alias_id").stdout.split()[0]
    assert new_id.startswith("AL06")  # mã nối tiếp AL060 của danh mục ban đầu


@need_pg
def test_br05_confirm_blocked_when_required_field_missing(db):
    psql("INSERT INTO orders (email_id, customer_id, status, ready_at) VALUES ('E006', 'KH024', 'needs_review', now())")
    psql("INSERT INTO order_items (order_id, line_no, product_text, qty_raw, sku, qty_base, match_score, match_status) "
         "SELECT order_id, 1, 'bút xanh 0.5', NULL, 'BU001', NULL, 100, 'matched' FROM orders WHERE email_id = 'E006'")
    fails(f"UPDATE orders SET status = 'confirmed', decided_by = {uid('huong.nt')}, decided_at = now() "
          "WHERE email_id = 'E006'", "BR-05")
    psql(f"UPDATE orders SET status = 'waiting_customer' WHERE email_id = 'E006'")   # đề nghị bổ sung vẫn được


@need_pg
def test_review_view_flags(db):
    psql("INSERT INTO orders (email_id, customer_id, status, ready_at) VALUES ('E005', 'KH003', 'draft', now())")
    psql("INSERT INTO order_items (order_id, line_no, product_text, qty_raw, sku, qty_base, match_score, match_status) "
         "SELECT order_id, n, 'x', 1, 'BU001', q, 95, 'matched' FROM orders, "
         "(VALUES (1, 10), (2, 500)) v(n, q) WHERE email_id = 'E005'")  # BU001 có max_normal_qty = 180
    out = psql("SELECT line_no, qty_anomaly, needs_review FROM v_order_items_review r JOIN orders o USING (order_id) "
               "WHERE o.email_id = 'E005' ORDER BY line_no").stdout.split()
    assert out == ["1|f|f", "2|t|t"]


@need_pg
def test_kpi_queries_follow_table_4_1(db):
    """Bộ đơn nhỏ có đáp án tính tay; chạy trên CSDL riêng để không lẫn với các kiểm thử khác."""
    psql("TRUNCATE orders RESTART IDENTITY CASCADE")
    sa = uid("thu.pm")
    # E010 nhận 02/11 lúc trước 17h; E020, E030, E040: các ngày khác. Đặt lại thời điểm nhận để tính tay.
    psql("UPDATE emails SET received_at = CASE email_id "
         "WHEN 'E010' THEN '2026-11-09 09:00+07' WHEN 'E020' THEN '2026-11-09 10:00+07' "
         "WHEN 'E030' THEN '2026-11-09 16:00+07' WHEN 'E040' THEN '2026-11-09 18:00+07' "
         "WHEN 'E050' THEN '2026-11-10 09:00+07' END::timestamptz WHERE email_id IN ('E010','E020','E030','E040','E050')")
    for e, opened, decided in [("E010", "09:05", "09:06"), ("E020", "10:05", "10:07"), ("E030", "16:50", None),
                               ("E040", None, None)]:
        psql(f"INSERT INTO orders (email_id, customer_id, status, ready_at) VALUES ('{e}', 'KH001', 'draft', now())")
        add_item(e)
        if decided:
            psql(f"UPDATE orders SET opened_at = '2026-11-09 {opened}+07', status = 'confirmed', decided_by = {sa}, "
                 f"decided_at = '2026-11-09 {decided}+07' WHERE email_id = '{e}'")
    # E030 xác nhận sáng hôm sau: trễ hạn theo KPI-04
    psql(f"UPDATE orders SET opened_at = '2026-11-10 08:00+07', status = 'confirmed', decided_by = {sa}, "
         "decided_at = '2026-11-10 08:03+07' WHERE email_id = 'E030'")
    psql(f"INSERT INTO order_edit_logs (order_id, field_name, old_value, new_value, edited_by) "
         f"SELECT order_id, 'qty_base', '10', '12', {sa} FROM orders WHERE email_id = 'E020'")
    # E050: đơn điều chỉnh vì sai mã hàng của đơn E010
    psql("INSERT INTO orders (email_id, customer_id, status, ready_at, adjusts_order_id, adjustment_reason) "
         "SELECT 'E050', 'KH001', 'draft', now(), order_id, 'wrong_sku' FROM orders WHERE email_id = 'E010'")
    sql = (PG / "03_kpi_queries.sql").read_text(encoding="utf-8")
    sql = "\n".join(l for l in sql.splitlines() if not l.lstrip().startswith("--"))
    blocks = [b for b in sql.split(";") if "SELECT" in b]
    res = [psql(b).stdout.strip().splitlines() for b in blocks[:4]]
    # KPI-01: ngày 09/11: (1 + 2) / 2 = 1,5 phút; ngày 10/11: 3 phút
    assert res[0] == ["2026-11-09|Phạm Minh Thư|2|1.50", "2026-11-10|Phạm Minh Thư|1|3.00"]
    # KPI-02: ngày 09/11 có 1/2 đơn phải sửa
    assert res[1][0] == "2026-11-09|2|1|50.0"
    # KPI-03: ngày 09/11 có 1/2 đơn đã xác nhận phải điều chỉnh vì sai mã
    assert res[2][0] == "2026-11-09|2|1|50.0"
    # KPI-04: ngày 09/11 có 3 đơn nhận trước 17h (E010, E020, E030), 2 đơn xác nhận trong ngày
    assert res[3][0] == "2026-11-09|3|2|66.7"


def bson_ok(value, schema):
    """Kiểm tra tối giản theo $jsonSchema của MongoDB: kiểu, trường bắt buộc, enum."""
    types = schema.get("bsonType")
    if types:
        types = types if isinstance(types, list) else [types]
        pyt = {"string": str, "object": dict, "array": list, "int": int, "double": (int, float), "null": type(None),
               "date": dict, "objectId": str}
        if not any(isinstance(value, pyt[t]) for t in types):
            return False
    if "enum" in schema and value not in schema["enum"]:
        return False
    if isinstance(value, dict) and "properties" in schema:
        if any(k not in value for k in schema.get("required", [])):
            return False
        return all(bson_ok(value[k], s) for k, s in schema["properties"].items() if k in value)
    if isinstance(value, list) and "items" in schema:
        return all(bson_ok(v, schema["items"]) for v in value)
    return True


def test_mongo_sample_documents_match_schema():
    schema = json.loads((MONGO / "raw_emails.schema.json").read_text(encoding="utf-8"))["$jsonSchema"]
    docs = json.loads((MONGO / "sample_documents.json").read_text(encoding="utf-8"))
    assert len(docs) == 60 and all(bson_ok(d, schema) for d in docs)
    ai = json.loads((MONGO / "ai_extractions.schema.json").read_text(encoding="utf-8"))["$jsonSchema"]
    assert {"masked_input", "model", "prompt_version"} <= set(ai["required"])
