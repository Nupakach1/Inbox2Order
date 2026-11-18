"""Nạp dữ liệu mẫu vào CSDL Inbox2Order (mục 5.8).

    python src/load_db.py sql      # sinh database/postgres/02_seed.sql và mongodb/sample_documents.json
    python src/load_db.py load     # chạy 01_schema.sql + 02_seed.sql vào PostgreSQL theo PG_* trong .env

Chỉ nạp dữ liệu danh mục (người dùng, khách hàng, địa chỉ, SKU, bí danh) và thông tin quản lý của 60 email
ở trạng thái Mới nhận (received). Đơn nháp được tạo khi chạy luồng xử lý ở Ngày 6, không nạp sẵn.
"""
import csv
import json
import sys
from pathlib import Path

from config import GENERATED_DIR, ROOT, env

PG_DIR = ROOT / "database" / "postgres"
MONGO_DIR = ROOT / "database" / "mongodb"
TZ = "+07:00"  # giờ Việt Nam

# Nhân sự phòng kinh doanh và IT của An Phát (Bảng 1.1 và Phụ lục G báo cáo) và vai trò trong hệ thống
USERS = [
    ("vinh.tq", "Trần Quốc Vinh", "vinh.tq@anphat.example.vn", "sales_manager"),
    ("huong.nt", "Nguyễn Thị Hương", "huong.nt@anphat.example.vn", "sales_admin"),
    ("trang.lt", "Lê Thu Trang", "trang.lt@anphat.example.vn", "sales_admin"),
    ("thu.pm", "Phạm Minh Thư", "thu.pm@anphat.example.vn", "sales_admin"),
    ("khai.dm", "Đặng Minh Khải", "khai.dm@anphat.example.vn", "system_admin"),
]


def read_csv(name):
    with open(GENERATED_DIR / name, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_emails():
    out = []
    for name in ("emails_dev.json", "emails_test.json"):
        out += json.loads((GENERATED_DIR / name).read_text(encoding="utf-8"))
    return sorted(out, key=lambda e: e["email_id"])


def q(v):
    """Giá trị SQL: NULL cho rỗng, chuỗi có nháy đơn."""
    if v is None or v == "":
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def insert(table, cols, rows):
    vals = ",\n".join("    (" + ", ".join(q(v) for v in r) + ")" for r in rows)
    return f"INSERT INTO {table} ({', '.join(cols)}) VALUES\n{vals};\n"


def build_seed():
    customers = read_csv("customers.csv")
    products = read_csv("products.csv")
    aliases = read_csv("product_aliases.csv")
    emails = read_emails()
    parts = ["-- Inbox2Order – Dữ liệu mẫu, sinh bởi src/load_db.py từ data/generated/",
             "-- Chạy sau 01_schema.sql: psql -d inbox2order -f 02_seed.sql",
             "SET search_path TO i2o;", "BEGIN;", ""]
    parts.append(insert("users", ["username", "full_name", "email", "role"], USERS))
    parts.append(insert("customers", ["customer_id", "name", "customer_type", "contact_name", "email", "phone"],
                        [(c["customer_id"], c["name"], c["customer_type"], c["contact_name"], c["email"], c["phone"])
                         for c in customers]))
    parts.append(insert("customer_addresses", ["customer_id", "address_text", "is_default"],
                        [(c["customer_id"], c["default_address"], True) for c in customers]))
    parts.append(insert("products", ["sku", "name", "product_group", "unit", "pack_unit", "pack_size", "price_vnd",
                                     "max_normal_qty"],
                        [(p["sku"], p["name"], p["group"], p["unit"], p["pack_unit"] or None, int(p["pack_size"]),
                          int(p["price_vnd"]), int(p["max_normal_qty"])) for p in products]))
    parts.append(insert("product_aliases", ["alias_id", "customer_id", "alias_text", "sku"],
                        [(a["alias_id"], a["customer_id"] or None, a["alias_text"], a["sku"]) for a in aliases]))
    parts.append(f"SELECT setval('product_aliases_seq', {len(aliases)});\n")
    parts.append(insert("emails", ["email_id", "from_email", "from_name", "subject", "received_at"],
                        [(e["email_id"], e["from_email"], e["from_name"], e["subject"], e["received_at"] + ":00" + TZ)
                         for e in emails]))
    parts += ["COMMIT;", ""]
    (PG_DIR / "02_seed.sql").write_text("\n".join(parts), encoding="utf-8")
    print("Ghi", (PG_DIR / "02_seed.sql").relative_to(ROOT),
          f"({len(USERS)} người dùng, {len(customers)} khách, {len(products)} SKU, {len(aliases)} bí danh, {len(emails)} email)")


def build_mongo_samples():
    """raw_emails: 60 email gốc theo đúng cấu trúc raw_emails.schema.json, nạp bằng
    mongoimport --db inbox2order --collection raw_emails --jsonArray --file sample_documents.json"""
    docs = [{
        "_id": e["email_id"],
        "from_email": e["from_email"],
        "from_name": e["from_name"],
        "to_email": e["to_email"],
        "subject": e["subject"],
        "body": e["body"],
        "received_at": {"$date": e["received_at"] + ":00" + TZ},
        "attachments": [],
    } for e in read_emails()]
    out = MONGO_DIR / "sample_documents.json"
    out.write_text(json.dumps(docs, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Ghi", out.relative_to(ROOT), f"({len(docs)} tài liệu raw_emails)")


def load():
    import psycopg2  # chỉ cần khi nạp thật
    conn = psycopg2.connect(host=env("PG_HOST", "localhost"), port=env("PG_PORT", "5432"), dbname=env("PG_DB", "inbox2order"),
                            user=env("PG_USER", "postgres"), password=env("PG_PASSWORD", ""))
    conn.autocommit = True
    with conn.cursor() as cur:
        for f in ("01_schema.sql", "02_seed.sql"):
            cur.execute((PG_DIR / f).read_text(encoding="utf-8"))
            print("Đã chạy", f)
        cur.execute("SET search_path TO i2o")
        for t in ("users", "customers", "customer_addresses", "products", "product_aliases", "emails"):
            cur.execute(f"SELECT count(*) FROM {t}")
            print(f"  {t}: {cur.fetchone()[0]} dòng")
    conn.close()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "sql"
    if cmd == "sql":
        build_seed()
        build_mongo_samples()
    elif cmd == "load":
        load()
    else:
        sys.exit(__doc__)
