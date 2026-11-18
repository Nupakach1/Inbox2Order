"""Nguồn duy nhất của lược đồ dữ liệu PostgreSQL Inbox2Order (mục 5.8).

Từ tệp này sinh ra database/postgres/01_schema.sql và từ điển dữ liệu
(python database/scripts/build_schema.py md).
Tên bảng theo mục 5.8 báo cáo; trạng thái và vai trò dùng đúng tên tiếng Anh chuẩn.
"""

EMAIL_STATUSES = ("received", "classified", "drafted", "forwarded")
ORDER_STATUSES = ("draft", "needs_review", "waiting_customer", "confirmed", "rejected")
ROLES = ("sales_admin", "sales_manager", "system_admin")
CATEGORIES = ("new_order", "modify_order", "price_inquiry", "complaint", "other")
LABELS = ("new_customer", "price_inquiry", "complaint", "other", "possible_duplicate", "has_attachment")


def _in(values):
    return "(" + ", ".join(f"'{v}'" for v in values) + ")"


# Mỗi cột: (tên, kiểu SQL, khóa, NOT NULL, mặc định, mô tả, ánh xạ SAP / ghi chú, quy tắc)
#   khóa: "PK", "FK:bảng.cột", "UQ", "PK,FK:bảng.cột" hoặc ""
TABLES = {
    "users": dict(
        desc="Người dùng hệ thống và vai trò",
        cols=[
            ("user_id", "INTEGER GENERATED ALWAYS AS IDENTITY", "PK", True, None, "Mã người dùng", "", ""),
            ("username", "VARCHAR(30)", "UQ", True, None, "Tên đăng nhập, mỗi người một tài khoản", "", "NFR-04"),
            ("full_name", "VARCHAR(100)", "", True, None, "Họ tên", "", ""),
            ("email", "VARCHAR(120)", "UQ", True, None, "Email công việc, nhận cảnh báo và tóm tắt 8h00", "", "FR-22, FR-23"),
            ("role", "VARCHAR(20)", "", True, None, "Vai trò: sales_admin, sales_manager, system_admin", "", "FR-24"),
            ("is_active", "BOOLEAN", "", True, "TRUE", "Còn sử dụng", "", ""),
        ],
        extra=[f"CONSTRAINT ck_users_role CHECK (role IN {_in(ROLES)})"],
    ),
    "customers": dict(
        desc="Khách hàng thường xuyên",
        cols=[
            ("customer_id", "VARCHAR(10)", "PK", True, None, "Mã khách (KH001…)", "Sold-To Party (VBAK-KUNNR), SoldToParty", ""),
            ("name", "VARCHAR(150)", "", True, None, "Tên khách hàng", "", ""),
            ("customer_type", "VARCHAR(10)", "", True, None, "office, school hoặc shop", "", ""),
            ("contact_name", "VARCHAR(100)", "", False, None, "Người liên hệ", "", ""),
            ("email", "VARCHAR(120)", "UQ", True, None, "Email đã đăng ký, dùng nhận diện người gửi", "", "BR-02"),
            ("phone", "VARCHAR(20)", "", False, None, "Số điện thoại, bị che trước khi gửi AI", "", "BR-14"),
            ("is_active", "BOOLEAN", "", True, "TRUE", "Còn giao dịch", "", ""),
        ],
        extra=["CONSTRAINT ck_customers_type CHECK (customer_type IN ('office', 'school', 'shop'))"],
    ),
    "customer_addresses": dict(
        desc="Địa chỉ giao hàng của khách; mỗi khách có đúng một địa chỉ mặc định",
        cols=[
            ("address_id", "INTEGER GENERATED ALWAYS AS IDENTITY", "PK", True, None, "Mã địa chỉ", "", ""),
            ("customer_id", "VARCHAR(10)", "FK:customers.customer_id", True, None, "Khách hàng", "", ""),
            ("address_text", "VARCHAR(255)", "", True, None, "Địa chỉ giao", "Ship-To Party (VBPA, chức năng WE)", ""),
            ("is_default", "BOOLEAN", "", True, "FALSE", "Địa chỉ mặc định, dùng khi email thiếu địa chỉ", "", "BR-13"),
        ],
        extra=[],
        indexes=["CREATE UNIQUE INDEX ux_customer_addresses_default ON customer_addresses (customer_id) WHERE is_default"],
    ),
    "products": dict(
        desc="Danh mục SKU, đồng bộ từ SAP",
        cols=[
            ("sku", "VARCHAR(10)", "PK", True, None, "Mã hàng", "Material (VBAP-MATNR), Material", ""),
            ("name", "VARCHAR(150)", "", True, None, "Tên chuẩn của sản phẩm", "", "BR-04"),
            ("product_group", "VARCHAR(4)", "", True, None, "Nhóm hàng (BU, GI, VO…)", "", ""),
            ("unit", "VARCHAR(10)", "", True, None, "Đơn vị bán", "Sales Unit (VBAP-VRKME), RequestedQuantityUnit", ""),
            ("pack_unit", "VARCHAR(10)", "", False, None, "Đơn vị đóng gói (hộp, thùng, lốc); trống nếu chỉ bán lẻ", "", "BR-06"),
            ("pack_size", "INTEGER", "", True, "1", "Số đơn vị bán trong một đơn vị đóng gói", "", "BR-06"),
            ("price_vnd", "INTEGER", "", True, None, "Giá tham khảo theo đơn vị bán; không gửi sang SAP", "SAP tự định giá (PR00)", ""),
            ("max_normal_qty", "INTEGER", "", True, None, "Ngưỡng số lượng bất thường theo đơn vị bán", "", "BR-07"),
            ("is_active", "BOOLEAN", "", True, "TRUE", "Còn kinh doanh; mã ngừng thì coi như không khớp", "", "EX-07"),
        ],
        extra=["CONSTRAINT ck_products_pack CHECK (pack_size >= 1 AND (pack_unit IS NOT NULL OR pack_size = 1))",
               "CONSTRAINT ck_products_qty CHECK (price_vnd >= 0 AND max_normal_qty > 0)"],
    ),
    "product_aliases": dict(
        desc="Bí danh: tên gọi riêng của khách cho một SKU",
        cols=[
            ("alias_id", "VARCHAR(10)", "PK", True, "'AL' || LPAD(nextval('product_aliases_seq')::TEXT, 3, '0')",
             "Mã bí danh (AL001…)", "", ""),
            ("customer_id", "VARCHAR(10)", "FK:customers.customer_id", False, None, "Khách dùng tên gọi; trống là bí danh chung",
             "KNMT-KUNNR", ""),
            ("alias_text", "VARCHAR(150)", "", True, None, "Tên gọi như khách viết", "KNMT-KDMAT / KNMT-POSTX", "BR-11"),
            ("sku", "VARCHAR(10)", "FK:products.sku", True, None, "Mã hàng tương ứng", "KNMT-MATNR", ""),
            ("status", "VARCHAR(10)", "", True, "'active'", "active hoặc inactive (ngừng dùng)", "", "FR-20"),
            ("created_by", "INTEGER", "FK:users.user_id", False, None, "Người đồng ý lưu; trống nếu nạp từ danh mục ban đầu", "", "BR-11"),
            ("created_at", "TIMESTAMPTZ", "", True, "now()", "Thời điểm tạo", "", ""),
        ],
        extra=["CONSTRAINT ck_product_aliases_status CHECK (status IN ('active', 'inactive'))"],
        indexes=["CREATE UNIQUE INDEX ux_product_aliases_active ON product_aliases "
                 "(COALESCE(customer_id, ''), lower(alias_text)) WHERE status = 'active'"],
        pre=["CREATE SEQUENCE product_aliases_seq"],
    ),
    "emails": dict(
        desc="Thông tin quản lý và trạng thái của email; nội dung gốc nằm ở MongoDB raw_emails",
        cols=[
            ("email_id", "VARCHAR(10)", "PK", True, None, "Mã email (E001…), trùng _id trong raw_emails",
             "Cust. Reference (VBAK-BSTNK), PurchaseOrderByCustomer", "NFR-07"),
            ("from_email", "VARCHAR(120)", "", True, None, "Địa chỉ người gửi", "", "BR-02"),
            ("from_name", "VARCHAR(100)", "", False, None, "Tên người gửi", "", ""),
            ("subject", "VARCHAR(255)", "", False, None, "Tiêu đề", "", ""),
            ("received_at", "TIMESTAMPTZ", "", True, None, "Thời điểm nhận", "Document Date (VBAK-AUDAT), SalesOrderDate", "BR-12"),
            ("status", "VARCHAR(12)", "", True, "'received'", "received, classified, drafted, forwarded", "", "FR-01"),
            ("category", "VARCHAR(15)", "", False, None, "Kết quả phân loại; trống khi chưa phân loại", "", "FR-03"),
            ("label", "VARCHAR(20)", "", False, None, "Nhãn khi chuyển người phụ trách hoặc cần lưu ý", "", "BR-02, BR-03, BR-08"),
            ("modifies_email_id", "VARCHAR(10)", "FK:emails.email_id", False, None, "Email gốc mà email sửa đơn tham chiếu", "", "BR-09"),
            ("forwarded_to", "INTEGER", "FK:users.user_id", False, None, "Người nhận khi email được chuyển", "", "FR-04"),
        ],
        extra=[f"CONSTRAINT ck_emails_status CHECK (status IN {_in(EMAIL_STATUSES)})",
               f"CONSTRAINT ck_emails_category CHECK (category IN {_in(CATEGORIES)})",
               f"CONSTRAINT ck_emails_label CHECK (label IN {_in(LABELS)})",
               "CONSTRAINT ck_emails_classified CHECK (status = 'received' OR category IS NOT NULL)",
               "CONSTRAINT ck_emails_forwarded CHECK (status <> 'forwarded' OR (forwarded_to IS NOT NULL AND label IS NOT NULL))"],
        indexes=["CREATE INDEX ix_emails_received_at ON emails (received_at)"],
    ),
    "orders": dict(
        desc="Đơn hàng từ lúc là đơn nháp đến khi đã xác nhận hoặc đã từ chối",
        cols=[
            ("order_id", "INTEGER GENERATED ALWAYS AS IDENTITY", "PK", True, None, "Mã đơn", "", ""),
            ("email_id", "VARCHAR(10)", "FK:emails.email_id,UQ", True, None, "Email tạo ra đơn; mỗi email tối đa một đơn",
             "Cust. Reference (VBAK-BSTNK)", "NFR-07"),
            ("customer_id", "VARCHAR(10)", "FK:customers.customer_id", False, None, "Khách đặt hàng; trống thì đơn phải ở Cần kiểm tra",
             "Sold-To Party (VBAK-KUNNR)", "BR-05"),
            ("ship_address_id", "INTEGER", "FK:customer_addresses.address_id", False, None, "Địa chỉ giao",
             "Ship-To Party (VBPA, WE)", "BR-13"),
            ("requested_delivery_date", "DATE", "", False, None, "Ngày giao yêu cầu", "Req. Deliv. Date (VBAK-VDATU)", "BR-13"),
            ("customer_note", "TEXT", "", False, None, "Ghi chú nguyên văn của khách", "Header text, to_Text", ""),
            ("status", "VARCHAR(16)", "", True, "'draft'", "draft, needs_review, waiting_customer, confirmed, rejected", "", "BR-01"),
            ("address_needs_review", "BOOLEAN", "", True, "FALSE", "Địa chỉ do hệ thống điền mặc định, cần kiểm tra", "", "BR-13"),
            ("date_needs_review", "BOOLEAN", "", True, "FALSE", "Ngày giao do hệ thống điền mặc định, cần kiểm tra", "", "BR-13"),
            ("adjusts_order_id", "INTEGER", "FK:orders.order_id", False, None, "Đơn gốc đã xác nhận mà đơn điều chỉnh này sửa", "", "BR-09"),
            ("adjustment_reason", "VARCHAR(16)", "", False, None, "customer_change, wrong_sku hoặc wrong_qty", "", "KPI-03"),
            ("created_at", "TIMESTAMPTZ", "", True, "now()", "Thời điểm tạo đơn nháp", "", "NFR-01"),
            ("ready_at", "TIMESTAMPTZ", "", True, None, "Thời điểm đưa vào danh sách duyệt (8h00 với email sau 17h00)", "", "BR-12"),
            ("locked_by", "INTEGER", "FK:users.user_id", False, None, "Sales Admin đang mở đơn", "", "EX-08"),
            ("opened_at", "TIMESTAMPTZ", "", False, None, "Lần đầu Sales Admin mở đơn", "", "KPI-01"),
            ("decided_by", "INTEGER", "FK:users.user_id", False, None, "Sales Admin xác nhận hoặc từ chối", "", "BR-01"),
            ("decided_at", "TIMESTAMPTZ", "", False, None, "Thời điểm xác nhận hoặc từ chối", "Lưu chứng từ (Save)", "KPI-01, KPI-04"),
            ("reject_reason", "TEXT", "", False, None, "Lý do từ chối, bắt buộc khi từ chối", "", "BR-01"),
        ],
        extra=[f"CONSTRAINT ck_orders_status CHECK (status IN {_in(ORDER_STATUSES)})",
               "CONSTRAINT ck_orders_adjust CHECK ((adjusts_order_id IS NULL) = (adjustment_reason IS NULL))",
               "CONSTRAINT ck_orders_adjust_reason CHECK (adjustment_reason IN ('customer_change', 'wrong_sku', 'wrong_qty'))",
               "CONSTRAINT ck_orders_decided CHECK (status NOT IN ('confirmed', 'rejected') "
               "OR (decided_by IS NOT NULL AND decided_at IS NOT NULL))",
               "CONSTRAINT ck_orders_reject_reason CHECK (status <> 'rejected' OR length(trim(reject_reason)) > 0)",
               "CONSTRAINT ck_orders_customer CHECK (customer_id IS NOT NULL OR status IN ('draft', 'needs_review', 'rejected'))"],
        indexes=["CREATE INDEX ix_orders_status_ready ON orders (status, ready_at)"],
    ),
    "order_items": dict(
        desc="Dòng hàng của đơn: tên gọi gốc, kết quả đối chiếu SKU, số lượng đã quy đổi",
        cols=[
            ("item_id", "INTEGER GENERATED ALWAYS AS IDENTITY", "PK", True, None, "Mã dòng", "", ""),
            ("order_id", "INTEGER", "FK:orders.order_id", True, None, "Đơn chứa dòng hàng", "", ""),
            ("line_no", "SMALLINT", "", True, None, "Số thứ tự dòng trong đơn", "Item (VBAP-POSNR)", ""),
            ("product_text", "VARCHAR(200)", "", True, None, "Tên gọi như khách viết", "", "BR-04"),
            ("qty_raw", "NUMERIC(10,2)", "", False, None, "Số lượng như khách viết; trống nếu email không nêu", "", "BR-05"),
            ("unit_raw", "VARCHAR(20)", "", False, None, "Đơn vị như khách viết", "", "BR-06"),
            ("sku", "VARCHAR(10)", "FK:products.sku", False, None, "Mã hàng đã khớp hoặc người đã chọn", "Material (VBAP-MATNR)", "BR-04"),
            ("qty_base", "NUMERIC(12,2)", "", False, None, "Số lượng đã quy đổi ra đơn vị bán", "Order Quantity (VBAP-KWMENG)", "BR-06, BR-07"),
            ("match_score", "SMALLINT", "", False, None, "Điểm tương đồng 0–100 của mã đang chọn", "", "BR-04"),
            ("match_status", "VARCHAR(10)", "", True, None, "matched, suggested, unmatched hoặc manual (người chọn)", "", "BR-04"),
        ],
        extra=["CONSTRAINT uq_order_items_line UNIQUE (order_id, line_no)",
               "CONSTRAINT ck_order_items_score CHECK (match_score BETWEEN 0 AND 100)",
               "CONSTRAINT ck_order_items_match CHECK (match_status IN ('matched', 'suggested', 'unmatched', 'manual'))",
               "CONSTRAINT ck_order_items_qty CHECK (qty_raw > 0 AND qty_base > 0)"],
        on_delete={"order_id": "CASCADE"},
    ),
    "order_item_suggestions": dict(
        desc="Tối đa 3 mã gợi ý cho dòng hàng có điểm 75–89",
        cols=[
            ("item_id", "INTEGER", "PK,FK:order_items.item_id", True, None, "Dòng hàng", "", ""),
            ("rank", "SMALLINT", "PK", True, None, "Thứ hạng gợi ý 1–3", "", "BR-04"),
            ("sku", "VARCHAR(10)", "FK:products.sku", True, None, "Mã gợi ý", "", ""),
            ("score", "SMALLINT", "", True, None, "Điểm tương đồng 0–100", "", ""),
        ],
        extra=["CONSTRAINT ck_suggestions_rank CHECK (rank BETWEEN 1 AND 3)",
               "CONSTRAINT ck_suggestions_score CHECK (score BETWEEN 0 AND 100)",
               "CONSTRAINT uq_suggestions_sku UNIQUE (item_id, sku)"],
        on_delete={"item_id": "CASCADE"},
    ),
    "order_edit_logs": dict(
        desc="Nhật ký mỗi lần đơn bị sửa sau khi tạo: do người sửa (BR-10) hoặc do email sửa đơn của khách (BR-09); chỉ được thêm",
        cols=[
            ("log_id", "BIGINT GENERATED ALWAYS AS IDENTITY", "PK", True, None, "Mã nhật ký", "", ""),
            ("order_id", "INTEGER", "FK:orders.order_id", True, None, "Đơn bị sửa", "", "BR-10"),
            ("item_id", "INTEGER", "FK:order_items.item_id", False, None, "Dòng bị sửa; trống nếu sửa phần đầu đơn", "", ""),
            ("field_name", "VARCHAR(40)", "", True, None, "Trường bị sửa (sku, qty_base, requested_delivery_date…)", "", "BR-10"),
            ("old_value", "TEXT", "", False, None, "Giá trị cũ", "", "BR-10"),
            ("new_value", "TEXT", "", False, None, "Giá trị mới", "", "BR-10"),
            ("edited_by", "INTEGER", "FK:users.user_id", False, None, "Người sửa; trống nếu thay đổi đến từ email sửa đơn", "", "BR-10"),
            ("source_email_id", "VARCHAR(10)", "FK:emails.email_id", False, None, "Email sửa đơn gây ra thay đổi", "", "BR-09"),
            ("edited_at", "TIMESTAMPTZ", "", True, "now()", "Thời điểm sửa", "", "BR-10, NFR-05"),
        ],
        extra=["CONSTRAINT ck_edit_logs_actor CHECK ((edited_by IS NULL) <> (source_email_id IS NULL))"],
        on_delete={"item_id": "SET NULL"},
        indexes=["CREATE INDEX ix_order_edit_logs_order ON order_edit_logs (order_id)"],
    ),
    "sap_sales_orders": dict(
        desc="Kết quả tạo Sales Order trong SAP cho đơn đã xác nhận",
        cols=[
            ("order_id", "INTEGER", "PK,FK:orders.order_id", True, None, "Đơn đã xác nhận", "", "BR-01"),
            ("sales_order_no", "VARCHAR(10)", "UQ", False, None, "Số Sales Order SAP trả về", "Sales Document (VBAK-VBELN), SalesOrder", ""),
            ("request_status", "VARCHAR(10)", "", True, "'pending'", "pending, success hoặc error", "", "EX-05"),
            ("attempt_count", "SMALLINT", "", True, "0", "Số lần gọi API", "", "EX-05"),
            ("last_error", "TEXT", "", False, None, "Thông báo lỗi gần nhất của API", "", "EX-05"),
            ("requested_at", "TIMESTAMPTZ", "", True, "now()", "Lần gọi API đầu tiên", "", ""),
            ("completed_at", "TIMESTAMPTZ", "", False, None, "Thời điểm SAP tạo đơn thành công", "", ""),
        ],
        extra=["CONSTRAINT ck_sap_status CHECK (request_status IN ('pending', 'success', 'error'))",
               "CONSTRAINT ck_sap_success CHECK (request_status <> 'success' OR (sales_order_no IS NOT NULL AND completed_at IS NOT NULL))"],
    ),
}

# Quan hệ cho ERD: (bảng cha, bảng con, cột FK, bản số phía con)
def relations():
    rels = []
    for t, spec in TABLES.items():
        for c in spec["cols"]:
            for part in c[2].split(","):
                if part.startswith("FK:"):
                    parent = part[3:].split(".")[0]
                    uq = "UQ" in c[2].split(",") or "PK" in c[2].split(",") and t != "order_item_suggestions"
                    rels.append((parent, t, c[0], "0..1" if uq else "n"))
    return rels
