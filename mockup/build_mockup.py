"""Sinh dữ liệu cho giao diện demo và chụp ảnh bốn màn hình.

    python mockup/build_mockup.py            # ghi mockup/app/data.js (+ tailwind.css nếu có npx), chụp mockup/screens/*.png nếu có Chrome

Dữ liệu lấy từ data/generated (danh mục, khách hàng, email gốc) và evaluation/results
(pipeline_week.json: đơn nháp hệ thống tạo ra từ kết quả AI thật; summary.json: kết quả chấm điểm).
Màn hình chỉ hiển thị dữ liệu có trong bộ mẫu, không dùng chữ giữ chỗ.
"""
import csv
import json
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from config import CUTOFF_HOUR, GENERATED_DIR  # noqa: E402
from load_db import USERS  # noqa: E402

MOCK = ROOT / "mockup" / "app"
SCREENS = ROOT / "mockup" / "screens"
RESULTS = ROOT / "evaluation" / "results"
SHOTS = [  # (tệp, địa chỉ trong mockup, chiều cao)
    ("MH-01_HopThu", "#hop-thu", 1020),
    ("MH-02_ChiTietDonNhap", "#don/E004", 800),
    ("MH-02b_ThieuSoLuong", "#don/E023", 760),
    ("MH-02c_SoLuongBatThuong", "#don/E026", 760),
    ("MH-03_DanhMucSKU", "#danh-muc", 1000),
    ("MH-04_Dashboard", "#bao-cao", 1300),
]


def read_csv(name):
    with open(GENERATED_DIR / name, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def deadline(received, ready):
    r = datetime.fromisoformat(received)
    base = r if r.hour < CUTOFF_HOUR else datetime.fromisoformat(ready)
    return datetime.combine(base.date(), datetime.min.time()).replace(hour=CUTOFF_HOUR).isoformat(timespec="minutes")


def build_data():
    week = json.loads((RESULTS / "pipeline_week.json").read_text(encoding="utf-8"))
    summary = json.loads((RESULTS / "summary.json").read_text(encoding="utf-8"))
    ai = {r["email_id"]: r for n in ("dev", "test")
          for r in json.loads((RESULTS / f"ai_output_{n}.json").read_text(encoding="utf-8"))}
    raw = {e["email_id"]: e for n in ("dev", "test")
           for e in json.loads((GENERATED_DIR / f"emails_{n}.json").read_text(encoding="utf-8"))}
    emails = []
    for e in week["emails"]:
        r = raw[e["email_id"]]
        emails.append({**e, "from_name": r["from_name"], "body": r["body"], "to_email": r["to_email"],
                       "mask_counts": ai[e["email_id"]]["mask_counts"], "masked_input": ai[e["email_id"]]["masked_input"]})
    orders = []
    for o in week["orders"]:
        e = raw[o["email_id"]]
        o = {k: v for k, v in o.items() if k != "initial"}
        o["deadline"] = deadline(e["received_at"], o["ready_at"])
        orders.append(o)
    lines = [it for o in week["orders"] for it in o["initial"]["items"]]
    stats = {
        "emails": len(emails), "orders": len(orders),
        "needs_review": sum(o["status"] == "needs_review" for o in orders),
        "forwarded": sum(e["status"] == "forwarded" for e in emails),
        "lines": len(lines), "matched": sum(it["match_status"] == "matched" for it in lines),
        "suggested": sum(it["match_status"] == "suggested" for it in lines),
        "unmatched": sum(it["match_status"] == "unmatched" for it in lines),
        "eval": summary,
        "by_day": {},
    }
    for e in emails:
        d = e["received_at"][:10]
        b = stats["by_day"].setdefault(d, {"emails": 0, "orders": 0, "after_cutoff": 0})
        b["emails"] += 1
        b["orders"] += e["status"] == "drafted" and e["category"] == "new_order"
        b["after_cutoff"] += int(e["received_at"][11:13]) >= CUTOFF_HOUR
    data = {
        "users": [{"username": u, "full_name": n, "role": r} for u, n, _m, r in USERS],
        "customers": {c["customer_id"]: c for c in read_csv("customers.csv")},
        "products": {p["sku"]: p for p in read_csv("products.csv")},
        "aliases": [{**a, "status": "active", "created_by": None} for a in read_csv("product_aliases.csv")],
        "emails": emails, "orders": orders, "logs": week["logs"], "stats": stats,
    }
    MOCK.mkdir(parents=True, exist_ok=True)
    (MOCK / "data.js").write_text("window.I2O = " + json.dumps(data, ensure_ascii=False) + ";\n", encoding="utf-8")
    print("Ghi mockup/app/data.js:", len(emails), "email,", len(orders), "đơn")


def build_css():
    """Biên dịch Tailwind ra tệp tĩnh để mockup mở được khi không có mạng; không có npx thì dùng CDN."""
    tw = shutil.which("npx")
    if not tw:
        return
    cfg = MOCK / "tailwind.config.js"
    cfg.write_text("module.exports = { content: ['./mockup/app/*.html', './mockup/app/*.js'], theme: { extend: {} } };\n")
    src = MOCK / "tailwind.src.css"
    src.write_text("@tailwind base;\n@tailwind components;\n@tailwind utilities;\n")
    r = subprocess.run(["npx", "--yes", "tailwindcss@3", "-c", str(cfg), "-i", str(src), "-o",
                        str(MOCK / "tailwind.css"), "--minify"], cwd=ROOT, capture_output=True, text=True)
    print("Tailwind:", "đã biên dịch tailwind.css" if r.returncode == 0 else r.stderr[-300:])


def shoot():
    chrome = shutil.which("google-chrome") or shutil.which("chromium")
    if not chrome:
        print("Không có Chrome: mở mockup/index.html và chụp tay")
        return
    SCREENS.mkdir(parents=True, exist_ok=True)
    for name, hash_, h in SHOTS:
        out = SCREENS / f"{name}.png"
        url = (MOCK / "index.html").as_uri() + hash_
        subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
                        "--force-device-scale-factor=1.5", f"--window-size=1440,{h}", "--virtual-time-budget=3000",
                        f"--screenshot={out}", url], capture_output=True)
        print("Chụp", out.name, out.exists())


if __name__ == "__main__":
    build_data()
    build_css()
    if "--no-shots" not in sys.argv:
        shoot()
