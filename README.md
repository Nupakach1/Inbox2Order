# Inbox2Order – Từ email đến đơn hàng trong 90 giây

**Phân tích và thiết kế hệ thống Inbox2Order ứng dụng AI tự động hóa tiếp nhận đơn hàng qua email theo mô hình human-in-the-loop, tích hợp SAP S/4HANA.**

## Bài toán

Công ty TNHH Phân phối Văn phòng phẩm An Phát nhận khoảng 60 email đặt hàng mỗi ngày. Ba sales admin phải đọc từng email, tra mã hàng trong Excel rồi gõ lại vào SAP, mất khoảng 6 phút mỗi đơn. Tên sản phẩm do khách tự đặt nên 4% đơn bị sai mã hoặc số lượng, và 20% đơn nhận trước 17h00 bị xác nhận sang hôm sau.

## Giải pháp

Inbox2Order đọc và phân loại email, trích xuất thông tin đơn bằng mô hình AI, đối chiếu tên sản phẩm với danh mục SKU, rồi tạo đơn nháp và tô vàng những trường chưa chắc chắn. **AI không bao giờ tự xác nhận đơn**: Sales Admin luôn là người kiểm tra và xác nhận cuối cùng.

| Chỉ số | Hiện trạng | Mục tiêu |
| --- | --- | --- |
| KPI-01 Thời gian xử lý mỗi đơn | 6 phút | ≤ 1,5 phút |
| KPI-02 Tỷ lệ đơn nháp phải sửa | Chưa có | < 20% |
| KPI-03 Tỷ lệ đơn sai lọt qua sau duyệt | 4% | < 1% |
| KPI-04 Đơn trước 17h00 được xác nhận trong ngày | 80% | ≥ 95% |

## Kết quả chính (Chương 7)

Thử nghiệm một lần trên 30 email tập kiểm tra với prompt `extract_v1` đã chốt trên tập thử (mô hình Claude Opus 5.5, chạy trên giao diện chat, không qua API):

| Chỉ số | Kết quả |
| --- | --- |
| Phân loại email đúng | 30/30 |
| Trích xuất đúng 6 trường (khách, tên hàng, số lượng, đơn vị, ngày giao, địa chỉ) | 100% (84 dòng hàng, 28 email) |
| Đối chiếu SKU top-1 / top-3 | 78/84 (92,9%) / 79/84 (94,0%) |
| Dòng hệ thống tự khớp mà sai | 0/67 |
| Đơn nháp đạt ngay | 19/25 (76%) → KPI-02 ước tính 24%, chưa đạt < 20% |
| Lỗi bịa thông tin | 0 |
| Kiểm thử chấp nhận | 20 đạt, 0 không đạt, 4 chưa chạy (cần SAP, hộp thư, đăng nhập) |
| Lợi ích ròng ở mức 1,5 phút/đơn | 4.566.100 đồng/tháng; hòa vốn đến 5,6 phút/đơn |

Kết quả trích xuất cao hơn mức nên kỳ vọng khi vận hành thật (30 email, viết theo mẫu, chạy cùng phiên với lúc viết prompt); pilot tuần 1 đo lại bằng API. KPI-01 chưa đo trong phạm vi đồ án; mockup tự ghi thời gian duyệt mỗi đơn để đo ở tuần 1 pilot.

## Cấu trúc thư mục

```text
inbox2order/
├── README.md                    Tổng quan: bài toán, giải pháp, kết quả chính, cấu trúc, cách chạy
├── requirements.txt             Thư viện Python
├── .env.example                 Mẫu biến môi trường (khóa API, PostgreSQL); giá trị thật để trong .env, không commit
├── .gitignore
│
├── mockup/                      Giao diện demo
│   ├── build_mockup.py          Sinh app/data.js, biên dịch Tailwind (chụp ảnh màn hình vào screens/ nếu có Chrome)
│   └── app/                     index.html, app.js, data.js, tailwind.css: mở index.html bằng trình duyệt
│
├── data/                        Dữ liệu mẫu (README.md là từ điển dữ liệu)
│   ├── generated/               products.csv, product_aliases.csv, customers.csv, emails_dev.json, emails_test.json
│   └── labels/                  ground_truth_test.json (đáp án tập kiểm tra)
│
├── database/                    Thiết kế dữ liệu (mục 5.8)
│   ├── scripts/                 schema_def.py (nguồn duy nhất của lược đồ), build_schema.py
│   ├── postgres/                01_schema.sql, 02_seed.sql, 03_kpi_queries.sql
│   └── mongodb/                 raw_emails.schema.json, ai_extractions.schema.json, sample_documents.json
│
├── src/                         Mã nguồn Python (Phụ lục D)
│   ├── config.py                Đường dẫn, seed, ngưỡng quy tắc
│   ├── generate_data.py         Sinh dữ liệu mẫu
│   ├── mask_pii.py              Che thông tin cá nhân (BR-14)
│   ├── extract.py               Gọi mô hình AI, lưu kết quả nguyên văn
│   ├── sku_matcher.py           Đối chiếu SKU, quy đổi đơn vị (BR-04, BR-06, BR-07)
│   ├── pipeline.py              Email → đơn nháp (UC-01, UC-02)
│   ├── evaluate.py              Chấm điểm (mục 7.1 báo cáo)
│   ├── load_db.py               Sinh 02_seed.sql, nạp PostgreSQL
│   ├── run_uat.py               Chạy 24 test case trên PostgreSQL
│   └── prompts/extract_v1.txt   Prompt đã chốt (Phụ lục C)
│
├── tests/                       34 kiểm thử pytest
│
└── evaluation/                  Thử nghiệm (Chương 7)
    ├── results/                 Đầu vào đã che, kết quả AI (không sửa tay), đơn nháp cả tuần, điểm, UAT
    └── runs/                    Câu trả lời gốc của mô hình (đầu vào của extract.py import)
```

## Cách chạy

Yêu cầu Python 3.10 trở lên.

```bash
pip install -r requirements.txt
cp .env.example .env                         # điền khóa API, PG_* nếu cần

# 1. Dữ liệu và CSDL
python src/generate_data.py                  # dữ liệu mẫu (seed cố định, chạy lại ra giống hệt)
python database/scripts/build_schema.py      # database/postgres/01_schema.sql từ schema_def.py
python src/load_db.py sql                    # 02_seed.sql và mongodb/sample_documents.json
python src/load_db.py load                   # (tùy chọn) nạp vào PostgreSQL theo PG_* trong .env

# 2. AI và thử nghiệm (Chương 7)
python src/extract.py prepare test           # nội dung đã che PII sẽ gửi cho AI
python src/extract.py api test               # (cần khóa API) gọi AI; tập kiểm tra chỉ chạy một lần
python src/pipeline.py                       # 60 email → đơn nháp cả tuần
python src/evaluate.py                       # chấm điểm theo mục 7.1 báo cáo
python src/run_uat.py                        # 24 test case trên PostgreSQL → evaluation/results/uat_results.json

# 3. Giao diện
python mockup/build_mockup.py                # dữ liệu mockup, Tailwind (ảnh màn hình nếu có Chrome)

# 4. Kiểm thử
python -m pytest tests                       # 34 kiểm thử (phần CSDL cần psql; không có thì bỏ qua)
```

Mở giao diện demo: `mockup/app/index.html` bằng trình duyệt (không cần mạng). Các màn hình: `#hop-thu` (Hộp thư), `#don/E004` (chi tiết đơn), `#danh-muc` (Danh mục SKU), `#bao-cao` (Dashboard KPI). Đổi người dùng ở ô "Đang dùng" góc phải; tải lại trang để về dữ liệu ban đầu.
