"""Sinh bộ dữ liệu mẫu cho Inbox2Order (Ngày 1).

Đầu ra trong data/:
  generated/products.csv         120 SKU, có quy cách đóng gói và max_normal_qty (BR-06, BR-07)
  generated/product_aliases.csv  60 bí danh sản phẩm (BR-11)
  generated/customers.csv        30 khách hàng
  generated/emails_dev.json      30 email tập thử (dùng để viết prompt, không có đáp án)
  generated/emails_test.json     30 email tập kiểm tra
  labels/ground_truth_test.json  đáp án của tập kiểm tra, lấy từ đơn gốc dùng để sinh email

Chạy:  python src/generate_data.py
Seed cố định trong config.py nên chạy lại luôn ra cùng kết quả.
"""
import csv
import json
import random
from datetime import date, datetime, timedelta

from unidecode import unidecode

import config

# ---------------------------------------------------------------------------
# 1. Danh mục sản phẩm
# ---------------------------------------------------------------------------
# (nhóm, tên, đơn vị bán, đơn vị đóng gói, quy cách, giá, [tên gọi quen của khách])

def _catalog():
    items = []
    add = lambda *a: items.append(a)

    for tip in ("0.5mm", "0.7mm"):
        for c in ("xanh", "đỏ", "đen"):
            add("BU", f"Bút bi {c} {tip}", "cây", "hộp", 20, 4500 if tip == "0.5mm" else 5000,
                [f"bút bi {c}", f"bút {c} {tip[:3]}", f"bút bi {c} {tip[:3]}"])
    for c in ("xanh", "đen", "đỏ"):
        add("BU", f"Bút gel {c} 0.5mm", "cây", "hộp", 12, 7000, [f"bút gel {c}", f"bút nước {c}"])
    for x in ("2B", "HB"):
        add("BU", f"Bút chì gỗ {x}", "cây", "hộp", 12, 3500, [f"bút chì {x}", f"chì {x}"])
    for x in ("0.5mm", "0.7mm"):
        add("BU", f"Bút chì kim {x}", "cây", "hộp", 12, 12000, [f"chì bấm {x[:3]}", f"bút chì kim {x[:3]}"])
    for x in ("0.5mm", "0.7mm"):
        add("BU", f"Ruột chì kim {x}", "tuýp", "hộp", 12, 6000, [f"ruột chì {x[:3]}", f"ngòi chì {x[:3]}"])
    for c in ("vàng", "xanh lá", "hồng", "cam"):
        add("BU", f"Bút dạ quang {c}", "cây", "hộp", 10, 8000, [f"dạ quang {c}", f"bút highlight {c}"])
    for c in ("xanh", "đen", "đỏ"):
        add("BU", f"Bút lông bảng {c}", "cây", "hộp", 10, 9000, [f"bút bảng {c}", f"lông bảng {c}"])
    for c in ("xanh", "đen", "đỏ"):
        add("BU", f"Bút lông dầu {c}", "cây", "hộp", 10, 10000, [f"bút dầu {c}", f"lông dầu {c}"])
    for c in ("xanh", "đen"):
        add("BU", f"Bút ký {c}", "cây", "hộp", 12, 15000, [f"bút ký {c}"])
    add("BU", "Bút lông kim đen 0.3mm", "cây", "hộp", 12, 12000, ["bút line đen", "lông kim đen"])
    add("BU", "Bút xóa nước 12ml", "cây", "hộp", 12, 15000, ["bút xóa", "bút xóa nước"])
    add("BU", "Băng xóa 5mm x 6m", "cái", "hộp", 12, 18000, ["băng xóa", "xóa kéo"])

    add("GI", "Giấy A4 70gsm", "ram", "thùng", 5, 72000, ["giấy A4 70", "A4 mỏng", "giấy in A4 70"])
    add("GI", "Giấy A4 80gsm", "ram", "thùng", 5, 85000, ["giấy A4 80", "A4 dày", "giấy 80"])
    add("GI", "Giấy A3 80gsm", "ram", "thùng", 5, 170000, ["giấy A3", "A3 80"])
    add("GI", "Giấy A5 70gsm", "ram", "thùng", 10, 38000, ["giấy A5", "A5 70"])
    for c in ("xanh", "hồng", "vàng"):
        add("GI", f"Giấy màu A4 {c}", "ram", "thùng", 5, 95000, [f"giấy màu {c}", f"A4 màu {c}"])
    for c in ("xanh", "vàng", "hồng"):
        add("GI", f"Giấy bìa màu A4 {c}", "xấp", "thùng", 5, 65000, [f"bìa màu {c}", f"giấy bìa {c}"])
    add("GI", "Giấy note vàng 3x3", "xấp", "lốc", 12, 9000, ["note vàng 3x3", "giấy nhớ vàng"])
    add("GI", "Giấy note vàng 3x4", "xấp", "lốc", 12, 11000, ["note 3x4", "giấy note to"])
    add("GI", "Giấy note 5 màu 3x3", "xấp", "lốc", 12, 14000, ["note 5 màu", "giấy nhớ 5 màu"])
    add("GI", "Giấy in nhiệt K80", "cuộn", "lốc", 10, 12000, ["giấy in bill K80", "giấy nhiệt K80"])
    add("GI", "Giấy than A4", "hộp", None, 1, 95000, ["giấy than"])

    for p in ("96", "200"):
        for k in ("kẻ ngang", "ô ly"):
            add("VO", f"Vở {p} trang {k}", "cuốn", "lốc", 10, 9000 if p == "96" else 16000,
                [f"vở {p}tr {k}", f"vở {p} trang", f"tập {p} {k}"])
    add("VO", "Sổ lò xo A5", "cuốn", "lốc", 5, 22000, ["sổ lò xo A5", "sổ xoắn A5"])
    add("VO", "Sổ lò xo A4", "cuốn", "lốc", 5, 32000, ["sổ lò xo A4", "sổ xoắn A4"])
    add("VO", "Sổ bìa da A5", "cuốn", None, 1, 55000, ["sổ da", "sổ bìa da"])
    add("VO", "Sổ danh thiếp 240 lá", "cuốn", None, 1, 45000, ["sổ name card", "sổ danh thiếp"])

    for s in ("5cm", "7cm"):
        for c in ("xanh", "đen"):
            add("BI", f"Bìa còng {s} {c}", "cái", "thùng", 20, 42000 if s == "5cm" else 48000,
                [f"bìa còng {s[0]} phân {c}", f"còng {s} {c}", f"bìa còng {s}"])
    add("BI", "Bìa lá A4", "cái", "lốc", 10, 2500, ["bìa lá", "bìa lá A4"])
    add("BI", "Bìa nút A4 trong", "cái", "lốc", 12, 4000, ["bìa nút trong", "túi nút trong"])
    add("BI", "Bìa nút A4 xanh", "cái", "lốc", 12, 4000, ["bìa nút xanh", "túi nút xanh"])
    add("BI", "Bìa trình ký A4", "cái", None, 1, 28000, ["bìa trình ký", "trình ký"])
    add("BI", "File nhựa 20 lá", "cuốn", None, 1, 25000, ["file 20 lá", "bìa 20 lá"])
    add("BI", "File nhựa 40 lá", "cuốn", None, 1, 38000, ["file 40 lá", "bìa 40 lá"])
    add("BI", "Túi khóa zip A4", "cái", "lốc", 10, 5000, ["túi zip", "túi zip A4"])
    add("BI", "Hộp đựng hồ sơ 10cm", "cái", None, 1, 35000, ["hộp hồ sơ 10 phân", "hộp đựng hồ sơ"])

    for s in ("15", "19", "25", "32", "41", "51"):
        add("KE", f"Kẹp bướm {s}mm", "hộp", "lốc", 10, {"15": 9000, "19": 11000, "25": 15000,
            "32": 22000, "41": 32000, "51": 45000}[s], [f"kẹp bướm {s}", f"kẹp đen {s}", f"kẹp bướm số {s}"])
    add("KE", "Kẹp giấy tam giác", "hộp", "lốc", 10, 6000, ["kẹp tam giác", "kẹp giấy"])
    add("KE", "Ghim bấm số 10", "hộp", "lốc", 20, 3500, ["kim bấm số 10", "ghim 10", "kim bấm nhỏ"])
    add("KE", "Ghim bấm số 3", "hộp", "lốc", 20, 9000, ["kim bấm số 3", "ghim 3", "kim bấm to"])
    add("KE", "Dập ghim số 10", "cái", None, 1, 35000, ["bấm kim nhỏ", "dập ghim 10"])
    add("KE", "Dập ghim số 3", "cái", None, 1, 85000, ["bấm kim to", "dập ghim số 3"])
    add("KE", "Gỡ ghim", "cái", None, 1, 12000, ["gỡ kim", "nhổ ghim"])
    add("KE", "Ghim cài", "hộp", "lốc", 10, 5000, ["ghim cài", "kim cài"])
    add("KE", "Thun vòng", "bịch", None, 1, 25000, ["thun", "dây thun"])

    add("BK", "Băng keo trong 5cm", "cuộn", "lốc", 6, 18000, ["băng keo trong to", "băng dính trong 5 phân"])
    add("BK", "Băng keo trong 2.5cm", "cuộn", "lốc", 6, 8000, ["băng keo trong nhỏ", "băng dính nhỏ"])
    add("BK", "Băng keo đục 5cm", "cuộn", "lốc", 6, 18000, ["băng keo đục", "keo đục"])
    add("BK", "Băng keo giấy 2.4cm", "cuộn", "lốc", 6, 9000, ["băng keo giấy", "keo giấy"])
    add("BK", "Băng keo hai mặt 1cm", "cuộn", "lốc", 6, 7000, ["keo 2 mặt", "băng dính 2 mặt"])
    add("BK", "Cắt băng keo", "cái", None, 1, 65000, ["đồ cắt băng keo", "cắt keo"])

    add("DC", "Kéo văn phòng 18cm", "cái", None, 1, 22000, ["kéo", "kéo văn phòng"])
    add("DC", "Kéo học sinh", "cái", "hộp", 12, 9000, ["kéo học sinh", "kéo nhỏ"])
    add("DC", "Dao rọc giấy lớn", "cái", None, 1, 18000, ["dao rọc to", "dao rọc giấy lớn"])
    add("DC", "Dao rọc giấy nhỏ", "cái", None, 1, 9000, ["dao rọc nhỏ"])
    add("DC", "Lưỡi dao rọc giấy lớn", "hộp", None, 1, 15000, ["lưỡi dao", "lưỡi dao rọc"])
    add("DC", "Thước kẻ 20cm", "cái", "hộp", 20, 4000, ["thước 20", "thước 2 tấc"])
    add("DC", "Thước kẻ 30cm", "cái", "hộp", 20, 6000, ["thước 30", "thước 3 tấc"])
    add("DC", "Gôm trắng", "cục", "hộp", 20, 3000, ["gôm", "tẩy trắng"])
    add("DC", "Hồ dán nước 30ml", "chai", "hộp", 12, 5000, ["hồ nước", "hồ dán"])
    add("DC", "Keo khô 8g", "cây", "hộp", 12, 9000, ["keo khô", "keo dán khô"])
    add("DC", "Bấm lỗ", "cái", None, 1, 75000, ["bấm lỗ", "đục lỗ"])

    for c in ("xanh", "đen"):
        add("MU", f"Mực bút lông bảng {c}", "lọ", None, 1, 22000, [f"mực bút bảng {c}", f"mực lông bảng {c}"])
    for c in ("xanh", "đỏ"):
        add("MU", f"Mực dấu {c}", "lọ", None, 1, 20000, [f"mực dấu {c}"])
    add("MU", "Hộp dấu", "cái", None, 1, 45000, ["tampon", "hộp mực dấu"])

    add("TH", "Dây đeo thẻ", "cái", "lốc", 10, 6000, ["dây đeo thẻ", "dây thẻ"])
    add("TH", "Bao đựng thẻ nhựa", "cái", "lốc", 10, 4000, ["bao thẻ", "vỏ thẻ"])
    add("TH", "Kệ hồ sơ 3 tầng", "cái", None, 1, 120000, ["kệ 3 tầng", "khay hồ sơ 3 tầng"])
    add("TH", "Khay cắm bút", "cái", None, 1, 35000, ["ống cắm bút", "khay bút"])
    add("TH", "Bảng từ trắng 60x80cm", "cái", None, 1, 280000, ["bảng trắng", "bảng từ"])
    add("TH", "Nam châm bảng", "vỉ", None, 1, 18000, ["nam châm", "nút nam châm"])

    add("PI", "Pin AA", "vỉ", "hộp", 10, 12000, ["pin tiểu", "pin 2A"])
    add("PI", "Pin AAA", "vỉ", "hộp", 10, 12000, ["pin đũa", "pin 3A"])
    add("PI", "Máy tính bỏ túi 12 số", "cái", None, 1, 180000, ["máy tính", "máy tính 12 số"])

    add("HS", "Phấn trắng", "hộp", "thùng", 20, 12000, ["phấn", "phấn trắng"])
    add("HS", "Phấn màu", "hộp", "thùng", 20, 15000, ["phấn màu"])
    add("HS", "Sáp màu 12 màu", "hộp", "thùng", 20, 18000, ["sáp màu", "bút sáp"])
    add("HS", "Bút màu 12 màu", "hộp", "thùng", 20, 25000, ["bút màu", "bút lông màu"])
    add("HS", "Màu nước 12 màu", "hộp", "thùng", 20, 30000, ["màu nước"])

    for s in ("A4", "A5", "A6"):
        add("BT", f"Bao thư trắng {s}", "xấp", "lốc", 10, {"A4": 45000, "A5": 30000, "A6": 20000}[s],
            [f"bao thư {s}", f"phong bì {s}"])
    add("BT", "Giấy decal A4", "xấp", None, 1, 55000, ["decal A4", "giấy dán nhãn"])
    add("BT", "Khăn giấy hộp", "hộp", "thùng", 30, 18000, ["khăn giấy", "giấy ăn hộp"])
    return items


def build_products(rng):
    rows, counters = [], {}
    for group, name, unit, pack_unit, pack_size, price, aliases in _catalog():
        counters[group] = counters.get(group, 0) + 1
        sku = f"{group}{counters[group]:03d}"
        if pack_unit:
            max_normal = pack_size * rng.randint(8, 15)
        else:
            max_normal = rng.choice([20, 30, 50])
        rows.append(dict(sku=sku, name=name, group=group, unit=unit, pack_unit=pack_unit or "",
                         pack_size=pack_size, price_vnd=price, max_normal_qty=max_normal,
                         _aliases=aliases))
    assert len(rows) == 120, len(rows)
    return rows


# ---------------------------------------------------------------------------
# 2. Khách hàng
# ---------------------------------------------------------------------------
CUSTOMERS = [
    # (loại, tên, tên miền, người liên hệ)
    ("office", "Công ty TNHH Kiến trúc Lam Viên Studio", "lamvienstudio", "Nguyễn Thu Hà"),
    ("office", "Công ty CP Giao nhận Bến Nghé Xanh", "bennghexanh", "Trần Minh Khoa"),
    ("office", "Công ty TNHH Kế toán Sổ Vàng", "sovang", "Lê Ngọc Trâm"),
    ("office", "Công ty TNHH Dược phẩm Thảo Mộc Việt An", "thaomocvietan", "Phạm Quốc Bảo"),
    ("office", "Công ty CP Phần mềm Mây Bạc", "maybac", "Võ Thanh Tâm"),
    ("office", "Văn phòng Luật Minh Chính Tín", "minhchinhtin", "Đặng Hoài Nam"),
    ("office", "Công ty TNHH Nội thất Gỗ Mộc Lan", "gomoclan", "Bùi Kim Oanh"),
    ("office", "Công ty CP Đào tạo Kỹ năng Hướng Sáng", "huongsang", "Huỳnh Gia Hân"),
    ("office", "Công ty TNHH Thực phẩm Bếp Quê Nhà", "bepquenha", "Ngô Văn Lực"),
    ("office", "Phòng khám Nha khoa Nụ Cười Hạnh Phúc", "nucuoihp", "Trịnh Mai Anh"),
    ("office", "Công ty TNHH Quảng cáo Sóng Đỏ Media", "songdomedia", "Đỗ Tuấn Kiệt"),
    ("office", "Công ty CP Xây dựng Nền Vững", "nenvung", "Lý Thị Hồng"),
    ("office", "Công ty TNHH Du lịch Cánh Diều Đỏ", "canhdieudo", "Mai Đức Thịnh"),
    ("office", "Trung tâm Ngoại ngữ Cầu Vồng Sáu Sắc", "cauvong6sac", "Phan Thảo Vy"),
    ("school", "Trường Mầm non Chồi Non Phú Mỹ", "choinonphumy", "Cô Lan"),
    ("school", "Trường Tiểu học Ánh Dương Quận 7", "anhduongq7", "Thầy Hưng"),
    ("school", "Trường THCS Hướng Dương Thủ Đức", "huongduongtd", "Cô Thủy"),
    ("school", "Trường Mầm non Thỏ Ngọc Bình Thạnh", "thongocbt", "Cô Ngân"),
    ("school", "Trung tâm Luyện thi Bút Thép", "butthep", "Thầy Phong"),
    ("school", "Trường Tiểu học Hạt Giống Nhỏ", "hatgiongnho", "Cô Diễm"),
    ("school", "Trường Mầm non Sóc Nâu Gò Vấp", "socnaugv", "Cô Hạnh"),
    ("school", "Trung tâm Năng khiếu Họa Mi Xanh", "hoamixanh", "Thầy Sang"),
    ("shop", "Cửa hàng Văn phòng phẩm Cô Ba Hiền", "cobahien", "Chị Hiền"),
    ("shop", "Nhà sách nhỏ Trang Giấy Thơm", "tranggiaythom", "Anh Toàn"),
    ("shop", "Tạp hóa Văn phòng phẩm Bảy Mập", "baymap", "Anh Bảy"),
    ("shop", "Cửa hàng Photocopy Siêu Tốc 24h", "sieutoc24h", "Chị Duyên"),
    ("shop", "Cửa hàng Văn phòng phẩm Út Nhỏ", "utnho", "Chị Út"),
    ("shop", "Nhà sách Gia Đình Vui", "giadinhvui", "Anh Lộc"),
    ("shop", "Cửa hàng Photo In ấn Lá Me", "lame", "Anh Tài"),
    ("shop", "Văn phòng phẩm Đồng Xu Vàng", "dongxuvang", "Chị Mến"),
]
DISTRICTS = ["Quận 1", "Quận 3", "Quận 7", "Quận 10", "Quận 12", "Bình Thạnh", "Gò Vấp", "Phú Nhuận",
             "Tân Bình", "Tân Phú", "Thủ Đức", "Bình Tân"]
STREETS = ["Hoa Sứ", "Cây Me", "Đường số 9", "Đường số 18", "Hẻm Bàng Lăng", "Lộ Trúc Xanh", "Phố Mai Vàng",
           "Đường Cầu Tre", "Đường Bến Cũ", "Hẻm Hoa Giấy"]

GROUP_PREFS = {
    "office": ["GI", "BU", "BI", "KE", "BK", "VO", "TH", "MU", "BT", "PI"],
    "school": ["VO", "BU", "HS", "GI", "DC", "BK", "KE"],
    "shop": ["BU", "VO", "GI", "DC", "KE", "BK", "BI", "HS", "BT"],
}


def build_customers(rng, products):
    rows = []
    for i, (kind, name, domain, contact) in enumerate(CUSTOMERS, 1):
        local = unidecode(contact.split()[-1]).lower() if kind != "school" else "vanphong"
        groups = GROUP_PREFS[kind]
        pool = [p for p in products if p["group"] in groups]
        favorites = rng.sample(pool, 9)
        rows.append(dict(
            customer_id=f"KH{i:03d}", name=name, customer_type=kind, contact_name=contact,
            email=f"{local}@{domain}.example.vn",
            phone=f"0123 {rng.randint(100, 999)} {rng.randint(100, 999)}",
            default_address=f"{rng.randint(5, 199)} {rng.choice(STREETS)}, {rng.choice(DISTRICTS)}, TP.HCM",
            _favorites=[p["sku"] for p in favorites],
            _messy=rng.random() < {"office": 0.15, "school": 0.4, "shop": 0.75}[kind],
        ))
    return rows


# ---------------------------------------------------------------------------
# 3. Bí danh sản phẩm (BR-11)
# ---------------------------------------------------------------------------
def build_aliases(rng, products, customers):
    by_sku = {p["sku"]: p for p in products}
    rows, seen = [], set()
    # 40 bí danh riêng của khách, lấy từ sản phẩm khách hay đặt
    for c in customers:
        for sku in c["_favorites"][:3]:
            if len([r for r in rows if r["customer_id"]]) >= 40:
                break
            text = rng.choice(by_sku[sku]["_aliases"])
            if (c["customer_id"], text) in seen:
                continue
            seen.add((c["customer_id"], text))
            rows.append(dict(customer_id=c["customer_id"], alias_text=text, sku=sku))
    # 20 bí danh chung, dùng cho mọi khách
    general = rng.sample(products, 20)
    for p in general:
        rows.append(dict(customer_id="", alias_text=p["_aliases"][0], sku=p["sku"]))
    for i, r in enumerate(rows, 1):
        r["alias_id"] = f"AL{i:03d}"
    return [dict(alias_id=r["alias_id"], customer_id=r["customer_id"], alias_text=r["alias_text"], sku=r["sku"])
            for r in rows]


# ---------------------------------------------------------------------------
# 4. Email
# ---------------------------------------------------------------------------
WEEKDAY_VI = ["thứ 2", "thứ 3", "thứ 4", "thứ 5", "thứ 6", "thứ 7", "chủ nhật"]
UNIT_ABBR = {"hộp": "h", "thùng": "th", "cây": "c", "ram": "r", "cuốn": "cuốn", "lốc": "lốc", "cuộn": "cuộn",
             "cái": "cái", "xấp": "xấp"}


def next_workday(d, n=1):
    while n:
        d += timedelta(days=1)
        if d.weekday() != 6:
            n -= 1
    return d


def render_delivery(rng, received: datetime):
    """Trả về (câu chữ trong email, ngày giao đáp án ISO hoặc None)."""
    if rng.random() < 0.3:
        return "", None
    k = rng.choice([1, 1, 2, 2, 3, 4])
    target = next_workday(received.date(), k)
    options = [("abs", f"giao ngày {target.day:02d}/{target.month:02d}")]
    if k == 1:
        options.append(("tomorrow", "giao ngày mai"))
    if target.isocalendar()[1] == received.isocalendar()[1]:
        options.append(("weekday", f"giao {WEEKDAY_VI[target.weekday()]} tuần này"))
    else:
        options.append(("weekday", f"giao {WEEKDAY_VI[target.weekday()]} tuần sau"))
    _, text = rng.choice(options)
    return text, target.isoformat()


def pick_qty(rng, product, messy):
    """Chọn số lượng như khách hay ghi: theo đơn vị đóng gói hoặc đơn vị bán."""
    if product["pack_unit"] and rng.random() < 0.6:
        q = rng.choice([1, 2, 2, 3, 4, 5])
        unit = product["pack_unit"]
        base = q * product["pack_size"]
    else:
        q = rng.choice([2, 3, 5, 5, 10, 10, 20]) if product["pack_unit"] else rng.choice([1, 2, 2, 3, 5])
        unit = product["unit"]
        base = q
    return q, unit, base


class EmailFactory:
    def __init__(self, rng, products, customers, aliases):
        self.rng, self.products, self.customers = rng, products, customers
        self.by_sku = {p["sku"]: p for p in products}
        self.alias_by_cust = {}
        for a in aliases:
            self.alias_by_cust.setdefault(a["customer_id"], []).append(a)

    # ---- product mention ----
    def mention(self, c, product, messy):
        rng = self.rng
        own = [a for a in self.alias_by_cust.get(c["customer_id"], []) if a["sku"] == product["sku"]]
        if own and rng.random() < 0.7:
            return own[0]["alias_text"]
        if messy:
            return rng.choice(product["_aliases"])
        return product["name"] if rng.random() < 0.8 else rng.choice(product["_aliases"])

    def order_lines(self, c, messy, n=None):
        rng = self.rng
        n = n or rng.choice([2, 3, 3, 4, 5])
        skus = rng.sample(c["_favorites"], n)
        lines = []
        for sku in skus:
            p = self.by_sku[sku]
            q, unit, base = pick_qty(rng, p, messy)
            lines.append(dict(product_text=self.mention(c, p, messy), sku=sku, qty=q, unit=unit, qty_base=base))
        return lines

    # ---- text styles ----
    def fmt_line_clear(self, i, ln, style):
        if style == "dash":
            return f"- {ln['product_text']}: {ln['qty']} {ln['unit']}"
        if style == "num":
            return f"{i}. {ln['product_text']} – SL: {ln['qty']} {ln['unit']}"
        return f"+ {ln['qty']} {ln['unit']} {ln['product_text']}"

    def fmt_line_messy(self, ln):
        u = UNIT_ABBR.get(ln["unit"], ln["unit"])
        if self.rng.random() < 0.5:
            gap = "" if u != ln["unit"] else " "
            return f"{ln['qty']}{gap}{u} {ln['product_text']}"
        return f"{ln['product_text']} {ln['qty']} {ln['unit']}"

    def signature(self, c):
        return f"{c['contact_name']}\n{c['name']}\nĐT: {c['phone']}"

    def clear_body(self, c, lines, delivery, address_text, extra=""):
        rng = self.rng
        greet = rng.choice(["Chào anh/chị phòng kinh doanh An Phát,", "Kính gửi Công ty An Phát,",
                            "Chào chị Hương,", "Dear An Phát,", "Chào em,"])
        who = {"office": ["Công ty chúng tôi đặt các mặt hàng sau:", "Bên em gửi đơn đặt hàng văn phòng phẩm như sau:"],
               "school": ["Bên trường đặt các mặt hàng sau:", "Nhà trường gửi đơn văn phòng phẩm như sau:"],
               "shop": ["Cửa hàng em lấy các món sau:", "Bên em lấy hàng như sau:"]}.get(c.get("customer_type"), ["Bên em đặt các mặt hàng sau:"])
        intro = rng.choice(who + ["Nhờ chị lên đơn giúp em các món dưới đây:", "Em gửi đơn hàng tuần này gồm:"])
        body = [greet, "", intro]
        style = rng.choice(["dash", "num", "plus"])
        body += [self.fmt_line_clear(i, ln, style) for i, ln in enumerate(lines, 1)]
        tail = [extra] if extra else []
        if delivery:
            tail.append(f"Nhờ bên mình {delivery}" + (f", {address_text}." if address_text else "."))
        elif address_text:
            tail.append(f"Nhờ bên mình {address_text}.")
        thanks = ["Cảm ơn em.", "Trân trọng."] if greet == "Chào em," else ["Cảm ơn chị.", "Trân trọng.", "Cảm ơn bên mình nhiều.", "Thanks chị."]
        tail.append(rng.choice(thanks))
        return "\n".join(body + [""] + tail + ["", self.signature(c)])

    def messy_body(self, c, lines, delivery, address_text, extra=""):
        rng = self.rng
        opener = rng.choice(["chị ơi em lấy", "e gửi đơn nhé:", "lên đơn giúp em", "anh ơi bên em lấy", "đơn tuần này nha c:"])
        sep = rng.choice([", ", "\n", " + "])
        text = opener + " " + sep.join(self.fmt_line_messy(ln) for ln in lines)
        if delivery:
            text += f". {delivery} giúp em" + (f", {address_text}" if address_text else "")
        elif address_text:
            text += f". {address_text}"
        if extra:
            text += ". " + extra
        text += rng.choice([" nhé", ". tks", " nha c", ". cảm ơn", ""])
        if rng.random() < 0.7:
            text = unidecode(text)
        sig = c["contact_name"] if rng.random() < 0.5 else self.signature(c)
        return text + "\n" + sig

    def subject(self, messy):
        if messy:
            return self.rng.choice(["don hang", "dat hang", "Đơn", "lấy hàng", "Re: đơn hàng", ""])
        return self.rng.choice(["Đơn đặt hàng văn phòng phẩm", "Đặt hàng tuần 45", "Đơn hàng tháng 11",
                                "Đặt VPP", "Re: Đơn hàng"])

    def address(self, c):
        if self.rng.random() < 0.2:
            addr = f"{self.rng.randint(5, 199)} {self.rng.choice(STREETS)}, {self.rng.choice(DISTRICTS)}, TP.HCM"
            return f"giao về chi nhánh {addr}", addr
        return "", None

    # ---- scenarios ----
    def new_order(self, c, received, kind):
        rng = self.rng
        messy = kind == "messy"
        lines = self.order_lines(c, messy)
        delivery, ddate = render_delivery(rng, received)
        addr_text, addr = self.address(c)
        flags = {}
        if kind == "missing":
            variant = rng.choice(["no_qty", "vague_product", "no_lines"])
            flags["missing"] = variant
            if variant == "no_qty":
                ln = lines[-1]
                ln["qty"] = ln["qty_base"] = None
                ln["unit"] = None
            elif variant == "vague_product":
                ln = lines[-1]
                ln["product_text"] = rng.choice(["món như lần trước", "loại hôm bữa chị gửi", "hàng giống đơn trước"])
                ln["sku"] = None
                ln["qty"], ln["unit"], ln["qty_base"] = rng.choice([2, 3, 5]), "hộp", None
            else:
                lines = []
        if kind == "missing" and flags["missing"] == "no_lines":
            body = (f"{rng.choice(['Chào chị,', 'Chị ơi,'])}\nBên em lấy hàng giống đơn tuần trước nhé"
                    f"{', ' + delivery if delivery else ''}.\n{self.signature(c)}")
        elif kind == "missing" and flags["missing"] == "no_qty":
            ln = lines[-1]
            shown = [l for l in lines[:-1]]
            extra = f"Thêm ít {ln['product_text']} nữa nhé."
            if messy or c["_messy"]:
                body = self.messy_body(c, shown, delivery, addr_text, extra=f"Thêm ít {ln['product_text']} nữa")
            else:
                body = self.clear_body(c, shown, delivery, addr_text, extra=extra)
        else:
            body = (self.messy_body if messy else self.clear_body)(c, lines, delivery, addr_text)
        if kind == "anomaly":
            flags["qty_anomaly_sku"] = lines[0]["sku"]
        return dict(body=body, subject=self.subject(messy), category="new_order", lines=lines,
                    delivery_date=ddate, delivery_address=addr, flags=flags)

    def modify(self, c, original):
        rng = self.rng
        olines = [l for l in original["gt"]["lines"] if l["sku"] and l["qty"]]
        changes = []
        up = olines[0]
        newq = up["qty"] + rng.choice([1, 2, 3])
        p = self.by_sku[up["sku"]]
        base = newq * (p["pack_size"] if up["unit"] == p["pack_unit"] else 1)
        changes.append(dict(action="update", product_text=up["product_text"], sku=up["sku"], qty=newq,
                            unit=up["unit"], qty_base=base))
        text = [f"sửa {up['product_text']} thành {newq} {up['unit']}"]
        if len(olines) > 1 and rng.random() < 0.6:
            rm = olines[1]
            changes.append(dict(action="remove", product_text=rm["product_text"], sku=rm["sku"], qty=None,
                                unit=None, qty_base=None))
            text.append(f"bỏ {rm['product_text']}")
        day_ref = "sáng nay" if original["received_at"].hour < 12 else "chiều nay"
        body = (f"{rng.choice(['Chị ơi', 'Chào chị', 'Em chào chị'])}, sửa giúp em đơn gửi {day_ref}: "
                + ", ".join(text) + ". Các món khác giữ nguyên ạ.\n" + self.signature(c))
        return dict(body=body, subject="Re: " + (original["subject"] or "đơn hàng"), category="modify_order",
                    lines=changes, delivery_date=None, delivery_address=None,
                    flags={}, modifies=original["_key"])

    def non_order(self, c, kind):
        rng = self.rng
        p = self.by_sku[rng.choice(c["_favorites"])]
        if kind == "inquiry":
            body = (f"Chào chị,\nCho em hỏi giá {p['name'].lower()} khi lấy từ 10 {p['pack_unit'] or p['unit']} "
                    f"trở lên thì có chiết khấu không ạ? Bên em đang so sánh để chốt đơn tháng sau.\n"
                    f"{self.signature(c)}")
            return dict(body=body, subject="Hỏi giá", category="price_inquiry", lines=[], delivery_date=None,
                        delivery_address=None, flags={})
        body = (f"Chào chị,\nĐơn giao hôm {rng.choice(['thứ 3', 'thứ 4', 'trước'])} bên em kiểm thì thiếu "
                f"{rng.choice([1, 2])} {p['pack_unit'] or p['unit']} {p['name'].lower()}, nhờ chị kiểm tra "
                f"và giao bù giúp em.\n{self.signature(c)}")
        return dict(body=body, subject="Giao thiếu hàng", category="other", lines=[], delivery_date=None,
                    delivery_address=None, flags={"complaint": True})


def random_time(rng, d, after_cutoff):
    if after_cutoff:
        h = rng.randint(17, 20)
    else:
        h = rng.choice([8, 8, 9, 9, 10, 10, 11, 13, 14, 14, 15, 15, 16])
    return datetime(d.year, d.month, d.day, h, rng.randint(0, 59))


def build_emails(rng, products, customers, aliases):
    f = EmailFactory(rng, products, customers, aliases)
    week = [date.fromisoformat(config.WEEK_START) + timedelta(days=i) for i in range(6)]
    known = [c for c in customers]

    plan = (["clear"] * 30 + ["messy"] * 14 + ["missing"] * 6)
    specs = []
    for kind in plan:
        pool = [c for c in known if c["_messy"]] if kind == "messy" else known
        specs.append(dict(kind=kind, cust=rng.choice(pool)))
    # một email rõ ràng ở mỗi tập có số lượng bất thường để kiểm thử BR-07
    anomaly_idx = [i for i, s in enumerate(specs) if s["kind"] == "clear"][:2]

    # thời điểm nhận: 9 email sau 17h00 trên tổng 60
    after = set(rng.sample(range(60), 9))
    emails = []
    for i, s in enumerate(specs):
        d = rng.choice(week)
        received = random_time(rng, d, i in after)
        kind = "anomaly" if i in anomaly_idx else s["kind"]
        e = f.new_order(s["cust"], received, kind if kind != "anomaly" else "clear")
        if kind == "anomaly":
            ln = e["lines"][0]
            p = f.by_sku[ln["sku"]]
            big = (p["max_normal_qty"] // (p["pack_size"] if ln["unit"] == p["pack_unit"] else 1)) * 4
            e["body"] = e["body"].replace(f"{ln['qty']} {ln['unit']}", f"{big} {ln['unit']}", 1)
            ln["qty"] = big
            ln["qty_base"] = big * (p["pack_size"] if ln["unit"] == p["pack_unit"] else 1)
            e["flags"]["qty_anomaly_sku"] = ln["sku"]
        emails.append(dict(_key=len(emails), _scenario=s["kind"], cust=s["cust"], received_at=received, **e,
                           gt=dict(lines=e["lines"])))

    # 4 email sửa đơn: sửa một đơn rõ ràng trước đó của cùng khách, gửi sau 1-5 giờ
    originals = [e for e in emails if e["_scenario"] in ("clear", "messy") and e["received_at"].weekday() < 5
                 and e["received_at"].hour < 15 and len([l for l in e["lines"] if l["sku"] and l["qty"]]) >= 2]
    for idx, o in enumerate(rng.sample(originals, 4)):
        m = f.modify(o["cust"], o)
        rec = o["received_at"] + timedelta(hours=rng.randint(1, 3), minutes=rng.randint(0, 50))
        emails.append(dict(_key=len(emails), _scenario="modify", cust=o["cust"], received_at=rec, **m,
                           gt=dict(lines=m["lines"])))

    # 4 email không phải đơn hàng: 2 hỏi giá, 2 khiếu nại
    for kind in ("inquiry", "complaint", "inquiry", "complaint"):
        c = rng.choice(known)
        e = f.non_order(c, kind)
        emails.append(dict(_key=len(emails), _scenario="non_order", cust=c,
                           received_at=random_time(rng, rng.choice(week), False), **e, gt=dict(lines=[])))

    # 1 email từ địa chỉ lạ (BR-02)
    stranger = dict(customer_id=None, name="Công ty TNHH Thiết bị Ánh Trăng Non", contact_name="Hồ Văn Trí",
                    phone="0123 555 018", _favorites=rng.sample([p["sku"] for p in products if p["group"] in
                                                                 GROUP_PREFS["office"]], 9),
                    _messy=False, email="tri.ho@anhtrangnon.example.vn")
    e = f.new_order(stranger, datetime(2026, 11, 4, 10, 12), "clear")
    e["flags"]["unknown_sender"] = True
    emails.append(dict(_key=len(emails), _scenario="unknown_sender", cust=stranger,
                       received_at=datetime(2026, 11, 4, 10, 12), **e, gt=dict(lines=e["lines"])))

    # 1 email gửi trùng (BR-08): khách gửi lại đúng đơn sau 1-2 giờ
    o = rng.choice([e for e in emails if e["_scenario"] == "clear" and e["received_at"].hour < 15])
    dup = dict(o)
    dup.update(_key=len(emails), _scenario="duplicate",
               received_at=o["received_at"] + timedelta(hours=rng.randint(1, 2), minutes=rng.randint(1, 40)),
               body="Em gửi lại đơn lúc nãy, sợ chị chưa nhận được ạ.\n\n" + o["body"],
               subject="Fw: " + (o["subject"] or "đơn hàng"), flags={"duplicate_of": o["_key"]})
    emails.append(dup)

    assert len(emails) == 60, len(emails)
    return emails


def assign_split(rng, emails):
    """Chia 30/30 theo đúng cơ cấu ở mục 7.1 báo cáo."""
    want_test = {"clear": 15, "messy": 7, "missing": 3, "modify": 2, "non_order": 2, "unknown_sender": 1}
    by = {}
    for e in emails:
        by.setdefault(e["_scenario"], []).append(e)
    for scen, items in by.items():
        k = want_test.get(scen, 0)
        if scen == "non_order":
            inq = [e for e in items if e["category"] == "price_inquiry"]
            oth = [e for e in items if e["category"] == "other"]
            test = [rng.choice(inq), rng.choice(oth)]
        else:
            # giữ email số lượng bất thường: mỗi tập một email
            anomalies = [e for e in items if e["flags"].get("qty_anomaly_sku")]
            rest = [e for e in items if not e["flags"].get("qty_anomaly_sku")]
            test = rng.sample(rest, k - (1 if anomalies else 0)) + anomalies[:1] if k else []
        for e in items:
            e["split"] = "test" if e in test else "dev"


def finalize(emails):
    emails.sort(key=lambda e: e["received_at"])
    key_to_id = {}
    for i, e in enumerate(emails, 1):
        e["email_id"] = f"E{i:03d}"
        key_to_id[e["_key"]] = e["email_id"]
    out_dev, out_test, labels = [], [], []
    for e in emails:
        c = e["cust"]
        rec = dict(email_id=e["email_id"], from_email=c["email"], from_name=c["contact_name"],
                   to_email=config.COMPANY_INBOX, subject=e["subject"], body=e["body"],
                   received_at=e["received_at"].isoformat(timespec="minutes"))
        (out_test if e["split"] == "test" else out_dev).append(rec)
        if e["split"] == "test":
            flags = dict(e["flags"])
            if "duplicate_of" in flags:
                flags["duplicate_of"] = key_to_id[flags["duplicate_of"]]
            after = e["received_at"].hour >= config.CUTOFF_HOUR
            labels.append(dict(
                email_id=e["email_id"], category=e["category"], customer_id=c.get("customer_id"),
                lines=[{k: v for k, v in l.items()} for l in e["gt"]["lines"]],
                delivery_date=e["delivery_date"], delivery_address=e["delivery_address"],
                modifies_email_id=key_to_id.get(e.get("modifies")) if e.get("modifies") is not None else None,
                received_after_cutoff=after, flags=flags))
    return out_dev, out_test, labels


def write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in fields})


def main():
    rng = random.Random(config.SEED)
    products = build_products(rng)
    customers = build_customers(rng, products)
    aliases = build_aliases(rng, products, customers)
    emails = build_emails(rng, products, customers, aliases)
    assign_split(rng, emails)
    dev, test, labels = finalize(emails)

    g, l = config.GENERATED_DIR, config.LABELS_DIR
    g.mkdir(parents=True, exist_ok=True)
    l.mkdir(parents=True, exist_ok=True)
    write_csv(g / "products.csv", products,
              ["sku", "name", "group", "unit", "pack_unit", "pack_size", "price_vnd", "max_normal_qty"])
    write_csv(g / "product_aliases.csv", aliases, ["alias_id", "customer_id", "alias_text", "sku"])
    write_csv(g / "customers.csv", customers,
              ["customer_id", "name", "customer_type", "contact_name", "email", "phone", "default_address"])
    for name, data in (("emails_dev.json", dev), ("emails_test.json", test)):
        (g / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    (l / "ground_truth_test.json").write_text(json.dumps(labels, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"products={len(products)} aliases={len(aliases)} customers={len(customers)} "
          f"emails_dev={len(dev)} emails_test={len(test)} labels={len(labels)}")


if __name__ == "__main__":
    main()
