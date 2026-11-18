"""Sinh database/postgres/01_schema.sql từ schema_def.py; in từ điển dữ liệu dạng markdown.

    python database/scripts/build_schema.py          # ghi 01_schema.sql
    python database/scripts/build_schema.py md       # in Bảng 5.15, 5.16 để dán vào báo cáo
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from schema_def import TABLES  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "database" / "postgres" / "01_schema.sql"

HEADER = """-- Inbox2Order – Lược đồ PostgreSQL (mục 5.8 báo cáo, Hình 5.10 ERD)
-- Tệp này được sinh từ database/scripts/schema_def.py; sửa ở đó rồi chạy build_schema.py.
-- Chạy: psql -d inbox2order -f 01_schema.sql   (PostgreSQL 14 trở lên)

SET client_min_messages = warning;
DROP SCHEMA IF EXISTS i2o CASCADE;
CREATE SCHEMA i2o;
SET search_path TO i2o;
"""

TRIGGERS = r"""
-- =====================================================================
-- Quy tắc nghiệp vụ được ràng buộc ngay trong CSDL
-- =====================================================================

-- BR-01: đơn chỉ được tạo ở Đơn nháp hoặc Cần kiểm tra; chỉ người dùng vai trò sales_admin
-- (đang hoạt động) mới chuyển được sang Đã xác nhận hoặc Đã từ chối.
CREATE FUNCTION fn_orders_br01() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'INSERT' AND NEW.status NOT IN ('draft', 'needs_review') THEN
        RAISE EXCEPTION 'BR-01: đơn mới chỉ được ở trạng thái draft hoặc needs_review (nhận %)', NEW.status;
    END IF;
    IF NEW.status IN ('confirmed', 'rejected')
       AND (TG_OP = 'INSERT' OR OLD.status IS DISTINCT FROM NEW.status) THEN
        IF NOT EXISTS (SELECT 1 FROM users u
                       WHERE u.user_id = NEW.decided_by AND u.role = 'sales_admin' AND u.is_active) THEN
            RAISE EXCEPTION 'BR-01: chỉ Sales Admin được xác nhận hoặc từ chối đơn';
        END IF;
    END IF;
    IF TG_OP = 'UPDATE' AND OLD.status IN ('confirmed', 'rejected') AND NEW.status <> OLD.status THEN
        RAISE EXCEPTION 'BR-09: đơn đã % không đổi trạng thái được; hãy tạo đơn điều chỉnh', OLD.status;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER trg_orders_br01 BEFORE INSERT OR UPDATE ON orders
    FOR EACH ROW EXECUTE FUNCTION fn_orders_br01();

-- BR-05: không xác nhận được đơn còn thiếu trường bắt buộc (khách hàng, ít nhất một dòng hàng,
-- mã hàng và số lượng của từng dòng).
CREATE FUNCTION fn_orders_br05() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.status = 'confirmed' AND OLD.status IS DISTINCT FROM 'confirmed' THEN
        IF NEW.customer_id IS NULL
           OR NOT EXISTS (SELECT 1 FROM order_items i WHERE i.order_id = NEW.order_id)
           OR EXISTS (SELECT 1 FROM order_items i WHERE i.order_id = NEW.order_id
                      AND (i.sku IS NULL OR i.qty_base IS NULL)) THEN
            RAISE EXCEPTION 'BR-05: đơn còn thiếu khách hàng, dòng hàng, mã hàng hoặc số lượng';
        END IF;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER trg_orders_br05 BEFORE UPDATE OF status ON orders
    FOR EACH ROW EXECUTE FUNCTION fn_orders_br05();

-- BR-09: đơn điều chỉnh chỉ liên kết tới đơn gốc đã xác nhận.
CREATE FUNCTION fn_orders_br09() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.adjusts_order_id IS NOT NULL AND NOT EXISTS
       (SELECT 1 FROM orders o WHERE o.order_id = NEW.adjusts_order_id AND o.status = 'confirmed') THEN
        RAISE EXCEPTION 'BR-09: đơn điều chỉnh phải liên kết với đơn gốc đã xác nhận';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER trg_orders_br09 BEFORE INSERT OR UPDATE OF adjusts_order_id ON orders
    FOR EACH ROW EXECUTE FUNCTION fn_orders_br09();

-- BR-01, NFR-07: Sales Order SAP chỉ được ghi cho đơn đã xác nhận (mỗi đơn tối đa một Sales Order).
CREATE FUNCTION fn_sap_confirmed_only() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM orders o WHERE o.order_id = NEW.order_id AND o.status = 'confirmed') THEN
        RAISE EXCEPTION 'BR-01: chỉ tạo Sales Order cho đơn đã xác nhận';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER trg_sap_confirmed_only BEFORE INSERT ON sap_sales_orders
    FOR EACH ROW EXECUTE FUNCTION fn_sap_confirmed_only();

-- NFR-05: nhật ký chỉnh sửa chỉ được thêm. Ngoại lệ duy nhất: khi một dòng hàng bị xóa,
-- khóa ngoại item_id được đặt về NULL, mọi cột khác giữ nguyên.
CREATE FUNCTION fn_edit_logs_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'UPDATE' AND NEW.item_id IS NULL AND OLD.item_id IS NOT NULL
       AND (NEW.log_id, NEW.order_id, NEW.field_name, NEW.old_value, NEW.new_value, NEW.edited_by,
            NEW.source_email_id, NEW.edited_at)
           IS NOT DISTINCT FROM
           (OLD.log_id, OLD.order_id, OLD.field_name, OLD.old_value, OLD.new_value, OLD.edited_by,
            OLD.source_email_id, OLD.edited_at) THEN
        RETURN NEW;
    END IF;
    RAISE EXCEPTION 'NFR-05: nhật ký chỉnh sửa không được sửa hoặc xóa';
END $$;
CREATE TRIGGER trg_edit_logs_append_only BEFORE UPDATE OR DELETE ON order_edit_logs
    FOR EACH ROW EXECUTE FUNCTION fn_edit_logs_append_only();

-- =====================================================================
-- View dùng cho giao diện (MH-01, MH-02)
-- =====================================================================

-- Dòng hàng cần kiểm tra (tô vàng): chưa khớp chắc chắn (BR-04), thiếu số lượng (BR-05),
-- vượt ngưỡng bất thường (BR-07) hoặc mã hàng đã ngừng kinh doanh (EX-07).
CREATE VIEW v_order_items_review AS
SELECT i.*,
       p.name  AS sku_name,
       p.unit  AS sku_unit,
       (i.match_status IN ('suggested', 'unmatched')) AS sku_needs_review,
       (i.qty_base IS NULL)                            AS qty_missing,
       (i.qty_base > p.max_normal_qty)                 AS qty_anomaly,
       (p.is_active IS FALSE)                          AS sku_inactive,
       (i.match_status IN ('suggested', 'unmatched') OR i.qty_base IS NULL
        OR i.qty_base > p.max_normal_qty OR p.is_active IS FALSE) AS needs_review
FROM order_items i
LEFT JOIN products p ON p.sku = i.sku;

-- Hàng duyệt (MH-01): đơn chưa có quyết định, đã đến giờ duyệt, sắp theo hạn xác nhận (BR-12).
CREATE VIEW v_review_queue AS
SELECT o.order_id, o.status, o.email_id, e.received_at, o.ready_at,
       c.customer_id, c.name AS customer_name, e.subject,
       (e.received_at AT TIME ZONE 'Asia/Ho_Chi_Minh')::time < TIME '17:00' AS before_cutoff,
       CASE WHEN (e.received_at AT TIME ZONE 'Asia/Ho_Chi_Minh')::time < TIME '17:00'
            THEN ((e.received_at AT TIME ZONE 'Asia/Ho_Chi_Minh')::date + TIME '17:00') AT TIME ZONE 'Asia/Ho_Chi_Minh'
            ELSE ((o.ready_at AT TIME ZONE 'Asia/Ho_Chi_Minh')::date + TIME '17:00') AT TIME ZONE 'Asia/Ho_Chi_Minh'
       END AS confirm_deadline,
       (SELECT count(*) FROM v_order_items_review r WHERE r.order_id = o.order_id AND r.needs_review)
           + o.address_needs_review::int + o.date_needs_review::int AS review_field_count,
       u.full_name AS locked_by_name
FROM orders o
JOIN emails e ON e.email_id = o.email_id
LEFT JOIN customers c ON c.customer_id = o.customer_id
LEFT JOIN users u ON u.user_id = o.locked_by
WHERE o.status IN ('draft', 'needs_review', 'waiting_customer');
"""


def parse_key(key):
    parts = [p for p in key.split(",") if p]
    return {"pk": "PK" in parts, "uq": "UQ" in parts,
            "fk": next((p[3:] for p in parts if p.startswith("FK:")), None)}


def table_sql(name, spec):
    lines, pks = [], []
    for col, typ, key, notnull, default, *_ in spec["cols"]:
        k = parse_key(key)
        s = f"    {col:<24} {typ}"
        if default:
            s += f" DEFAULT {default}" if "IDENTITY" not in typ else ""
        if notnull and not k["pk"]:
            s += " NOT NULL"
        if k["uq"]:
            s += " UNIQUE"
        if k["fk"]:
            t, c = k["fk"].split(".")
            s += f" REFERENCES {t} ({c})"
            od = spec.get("on_delete", {}).get(col)
            if od:
                s += f" ON DELETE {od}"
        if k["pk"]:
            pks.append(col)
        lines.append(s)
    lines.append(f"    CONSTRAINT pk_{name} PRIMARY KEY ({', '.join(pks)})")
    lines += [f"    {x}" for x in spec.get("extra", [])]
    out = [f"{p};" for p in spec.get("pre", [])]
    out.append(f"-- {spec['desc']}\nCREATE TABLE {name} (\n" + ",\n".join(lines) + "\n);")
    out += [f"{i};" for i in spec.get("indexes", [])]
    for col, *_rest in spec["cols"]:
        out.append(f"COMMENT ON COLUMN {name}.{col} IS '{_rest[4].replace(chr(39), chr(39) * 2)}';")
    out.append(f"COMMENT ON TABLE {name} IS '{spec['desc']}';")
    return "\n".join(out)


def build_sql():
    body = "\n\n".join(table_sql(n, s) for n, s in TABLES.items())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(HEADER + "\n" + body + "\n" + TRIGGERS, encoding="utf-8")
    print("Ghi", OUT.relative_to(ROOT))


def key_label(key):
    k = parse_key(key)
    out = []
    if k["pk"]:
        out.append("PK")
    if k["fk"]:
        out.append("FK → " + k["fk"].split(".")[0])
    if k["uq"]:
        out.append("UQ")
    return ", ".join(out)


def short_type(t):
    return t.replace(" GENERATED ALWAYS AS IDENTITY", " (tự tăng)")


def md(tables):
    rows = ["| Bảng | Cột | Kiểu | Khóa | Bắt buộc | Ý nghĩa | Quy tắc |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for t in tables:
        for i, (col, typ, key, nn, _d, desc, _sap, rule) in enumerate(TABLES[t]["cols"]):
            rows.append(f"| {t if i == 0 else ''} | {col} | {short_type(typ)} | {key_label(key)} | {'Có' if nn else ''} | {desc} | {rule} |")
    return "\n".join(rows)


if __name__ == "__main__":
    if sys.argv[1:] == ["md"]:
        print(md(["emails", "orders", "order_items", "order_item_suggestions", "order_edit_logs", "sap_sales_orders"]))
    else:
        build_sql()
