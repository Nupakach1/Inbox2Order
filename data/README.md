# Từ điển dữ liệu

Toàn bộ tệp trong `generated/` và `labels/` được tạo bởi `src/generate_data.py` với seed cố định (`SEED` trong `src/config.py`), nên chạy lại luôn cho cùng kết quả. Tệp CSV dùng mã hóa UTF-8 có BOM để mở thẳng bằng Excel.

## generated/products.csv – Danh mục SKU (120 dòng)

| Cột | Ý nghĩa |
| --- | --- |
| sku | Mã hàng, dạng nhóm + số thứ tự (BU001, GI002…) |
| name | Tên chuẩn của sản phẩm |
| group | Nhóm hàng: BU bút, GI giấy, VO vở sổ, BI bìa file, KE kẹp ghim, BK băng keo, DC dụng cụ, MU mực dấu, TH thẻ khay, PI pin máy tính, HS đồ dùng học sinh, BT bao thư nhãn |
| unit | Đơn vị bán (cây, ram, cuốn, hộp…) |
| pack_unit | Đơn vị đóng gói (hộp, thùng, lốc); để trống nếu chỉ bán lẻ |
| pack_size | Số đơn vị bán trong một đơn vị đóng gói, dùng quy đổi theo BR-06 |
| price_vnd | Giá bán theo đơn vị bán (đồng) |
| max_normal_qty | Ngưỡng số lượng bất thường tính theo đơn vị bán, dùng cho BR-07 |

## generated/product_aliases.csv – Bí danh sản phẩm (60 dòng)

| Cột | Ý nghĩa |
| --- | --- |
| alias_id | Mã bí danh (AL001…) |
| customer_id | Khách dùng tên gọi này; để trống nếu là bí danh chung |
| alias_text | Tên gọi quen, ví dụ "kẹp đen 25" |
| sku | Mã hàng tương ứng |

## generated/customers.csv – Khách hàng (30 dòng)

| Cột | Ý nghĩa |
| --- | --- |
| customer_id | Mã khách (KH001…) |
| name | Tên khách hàng |
| customer_type | office (văn phòng), school (trường học), shop (cửa hàng) |
| contact_name | Người liên hệ |
| email | Địa chỉ email đã đăng ký, dùng nhận diện người gửi (BR-02) |
| phone | Số điện thoại, bị che trước khi gửi AI (BR-14) |
| default_address | Địa chỉ giao mặc định (BR-13) |

## generated/emails_dev.json và emails_test.json – Email (30 + 30)

| Trường | Ý nghĩa |
| --- | --- |
| email_id | Mã email theo thứ tự thời gian nhận (E001…E060) |
| from_email, from_name | Người gửi |
| to_email | Hộp thư chung của phòng kinh doanh |
| subject, body | Tiêu đề và nội dung email |
| received_at | Thời điểm nhận, từ 02/11 đến 07/11/2026 |

`emails_dev.json` là **tập thử**, dùng để viết và chỉnh prompt; không có đáp án. `emails_test.json` là **tập kiểm tra**, chỉ chạy một lần với prompt đã chốt (mục 7.1 báo cáo).

Cơ cấu tập kiểm tra: 15 đơn viết rõ ràng, 7 đơn viết tắt hoặc không dấu, 3 đơn thiếu thông tin, 2 email sửa đơn, 2 email không phải đơn hàng (1 hỏi giá, 1 khiếu nại), 1 email từ địa chỉ lạ. Trong đó có 1 đơn có số lượng bất thường để kiểm thử BR-07 và 5 email nhận sau 17h00.

## labels/ground_truth_test.json – Đáp án tập kiểm tra (30 bản ghi)

| Trường | Ý nghĩa |
| --- | --- |
| email_id | Email tương ứng |
| category | new_order, modify_order, price_inquiry, other |
| customer_id | Khách gửi; null nếu địa chỉ lạ |
| lines | Danh sách dòng hàng: product_text (tên như khách viết), sku, qty, unit (như khách viết), qty_base (đã quy đổi ra đơn vị bán); với email sửa đơn có thêm action = update hoặc remove |
| delivery_date | Ngày giao khách yêu cầu (YYYY-MM-DD); null nếu email không nêu |
| delivery_address | Địa chỉ giao khác mặc định; null nếu email không nêu |
| modifies_email_id | Email gốc mà email sửa đơn tham chiếu |
| received_after_cutoff | true nếu nhận sau 17h00 |
| flags | missing (no_qty, vague_product, no_lines), unknown_sender, qty_anomaly_sku, complaint |

Đáp án lấy từ đơn hàng gốc mà script dùng để sinh email, không lấy từ AI. Người làm đọc lại từng email để xác nhận đáp án khớp với nội dung.
