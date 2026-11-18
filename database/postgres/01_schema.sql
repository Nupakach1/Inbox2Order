-- Inbox2Order – Lược đồ PostgreSQL (mục 5.8 báo cáo, Hình 5.8 ERD)
-- Tệp này được sinh từ database/scripts/schema_def.py; sửa ở đó rồi chạy build_schema.py.
-- Chạy: psql -d inbox2order -f 01_schema.sql   (PostgreSQL 14 trở lên)

SET client_min_messages = warning;
DROP SCHEMA IF EXISTS i2o CASCADE;
CREATE SCHEMA i2o;
SET search_path TO i2o;

-- Người dùng hệ thống và vai trò
CREATE TABLE users (
    user_id                  INTEGER GENERATED ALWAYS AS IDENTITY,
    username                 VARCHAR(30) NOT NULL UNIQUE,
    full_name                VARCHAR(100) NOT NULL,
    email                    VARCHAR(120) NOT NULL UNIQUE,
    role                     VARCHAR(20) NOT NULL,
    is_active                BOOLEAN DEFAULT TRUE NOT NULL,
    CONSTRAINT pk_users PRIMARY KEY (user_id),
    CONSTRAINT ck_users_role CHECK (role IN ('sales_admin', 'sales_manager', 'system_admin'))
);
COMMENT ON COLUMN users.user_id IS 'Mã người dùng';
COMMENT ON COLUMN users.username IS 'Tên đăng nhập, mỗi người một tài khoản';
COMMENT ON COLUMN users.full_name IS 'Họ tên';
COMMENT ON COLUMN users.email IS 'Email công việc, nhận cảnh báo và tóm tắt 8h00';
COMMENT ON COLUMN users.role IS 'Vai trò: sales_admin, sales_manager, system_admin';
COMMENT ON COLUMN users.is_active IS 'Còn sử dụng';
COMMENT ON TABLE users IS 'Người dùng hệ thống và vai trò';

-- Khách hàng thường xuyên
CREATE TABLE customers (
    customer_id              VARCHAR(10),
    name                     VARCHAR(150) NOT NULL,
    customer_type            VARCHAR(10) NOT NULL,
    contact_name             VARCHAR(100),
    email                    VARCHAR(120) NOT NULL UNIQUE,
    phone                    VARCHAR(20),
    is_active                BOOLEAN DEFAULT TRUE NOT NULL,
    CONSTRAINT pk_customers PRIMARY KEY (customer_id),
    CONSTRAINT ck_customers_type CHECK (customer_type IN ('office', 'school', 'shop'))
);
COMMENT ON COLUMN customers.customer_id IS 'Mã khách (KH001…)';
COMMENT ON COLUMN customers.name IS 'Tên khách hàng';
COMMENT ON COLUMN customers.customer_type IS 'office, school hoặc shop';
COMMENT ON COLUMN customers.contact_name IS 'Người liên hệ';
COMMENT ON COLUMN customers.email IS 'Email đã đăng ký, dùng nhận diện người gửi';
COMMENT ON COLUMN customers.phone IS 'Số điện thoại, bị che trước khi gửi AI';
COMMENT ON COLUMN customers.is_active IS 'Còn giao dịch';
COMMENT ON TABLE customers IS 'Khách hàng thường xuyên';

-- Địa chỉ giao hàng của khách; mỗi khách có đúng một địa chỉ mặc định
CREATE TABLE customer_addresses (
    address_id               INTEGER GENERATED ALWAYS AS IDENTITY,
    customer_id              VARCHAR(10) NOT NULL REFERENCES customers (customer_id),
    address_text             VARCHAR(255) NOT NULL,
    is_default               BOOLEAN DEFAULT FALSE NOT NULL,
    CONSTRAINT pk_customer_addresses PRIMARY KEY (address_id)
);
CREATE UNIQUE INDEX ux_customer_addresses_default ON customer_addresses (customer_id) WHERE is_default;
COMMENT ON COLUMN customer_addresses.address_id IS 'Mã địa chỉ';
COMMENT ON COLUMN customer_addresses.customer_id IS 'Khách hàng';
COMMENT ON COLUMN customer_addresses.address_text IS 'Địa chỉ giao';
COMMENT ON COLUMN customer_addresses.is_default IS 'Địa chỉ mặc định, dùng khi email thiếu địa chỉ';
COMMENT ON TABLE customer_addresses IS 'Địa chỉ giao hàng của khách; mỗi khách có đúng một địa chỉ mặc định';

-- Danh mục SKU, đồng bộ từ SAP
CREATE TABLE products (
    sku                      VARCHAR(10),
    name                     VARCHAR(150) NOT NULL,
    product_group            VARCHAR(4) NOT NULL,
    unit                     VARCHAR(10) NOT NULL,
    pack_unit                VARCHAR(10),
    pack_size                INTEGER DEFAULT 1 NOT NULL,
    price_vnd                INTEGER NOT NULL,
    max_normal_qty           INTEGER NOT NULL,
    is_active                BOOLEAN DEFAULT TRUE NOT NULL,
    CONSTRAINT pk_products PRIMARY KEY (sku),
    CONSTRAINT ck_products_pack CHECK (pack_size >= 1 AND (pack_unit IS NOT NULL OR pack_size = 1)),
    CONSTRAINT ck_products_qty CHECK (price_vnd >= 0 AND max_normal_qty > 0)
);
COMMENT ON COLUMN products.sku IS 'Mã hàng';
COMMENT ON COLUMN products.name IS 'Tên chuẩn của sản phẩm';
COMMENT ON COLUMN products.product_group IS 'Nhóm hàng (BU, GI, VO…)';
COMMENT ON COLUMN products.unit IS 'Đơn vị bán';
COMMENT ON COLUMN products.pack_unit IS 'Đơn vị đóng gói (hộp, thùng, lốc); trống nếu chỉ bán lẻ';
COMMENT ON COLUMN products.pack_size IS 'Số đơn vị bán trong một đơn vị đóng gói';
COMMENT ON COLUMN products.price_vnd IS 'Giá tham khảo theo đơn vị bán; không gửi sang SAP';
COMMENT ON COLUMN products.max_normal_qty IS 'Ngưỡng số lượng bất thường theo đơn vị bán';
COMMENT ON COLUMN products.is_active IS 'Còn kinh doanh; mã ngừng thì coi như không khớp';
COMMENT ON TABLE products IS 'Danh mục SKU, đồng bộ từ SAP';

CREATE SEQUENCE product_aliases_seq;
-- Bí danh: tên gọi riêng của khách cho một SKU
CREATE TABLE product_aliases (
    alias_id                 VARCHAR(10) DEFAULT 'AL' || LPAD(nextval('product_aliases_seq')::TEXT, 3, '0'),
    customer_id              VARCHAR(10) REFERENCES customers (customer_id),
    alias_text               VARCHAR(150) NOT NULL,
    sku                      VARCHAR(10) NOT NULL REFERENCES products (sku),
    status                   VARCHAR(10) DEFAULT 'active' NOT NULL,
    created_by               INTEGER REFERENCES users (user_id),
    created_at               TIMESTAMPTZ DEFAULT now() NOT NULL,
    CONSTRAINT pk_product_aliases PRIMARY KEY (alias_id),
    CONSTRAINT ck_product_aliases_status CHECK (status IN ('active', 'inactive'))
);
CREATE UNIQUE INDEX ux_product_aliases_active ON product_aliases (COALESCE(customer_id, ''), lower(alias_text)) WHERE status = 'active';
COMMENT ON COLUMN product_aliases.alias_id IS 'Mã bí danh (AL001…)';
COMMENT ON COLUMN product_aliases.customer_id IS 'Khách dùng tên gọi; trống là bí danh chung';
COMMENT ON COLUMN product_aliases.alias_text IS 'Tên gọi như khách viết';
COMMENT ON COLUMN product_aliases.sku IS 'Mã hàng tương ứng';
COMMENT ON COLUMN product_aliases.status IS 'active hoặc inactive (ngừng dùng)';
COMMENT ON COLUMN product_aliases.created_by IS 'Người đồng ý lưu; trống nếu nạp từ danh mục ban đầu';
COMMENT ON COLUMN product_aliases.created_at IS 'Thời điểm tạo';
COMMENT ON TABLE product_aliases IS 'Bí danh: tên gọi riêng của khách cho một SKU';

-- Thông tin quản lý và trạng thái của email; nội dung gốc nằm ở MongoDB raw_emails
CREATE TABLE emails (
    email_id                 VARCHAR(10),
    from_email               VARCHAR(120) NOT NULL,
    from_name                VARCHAR(100),
    subject                  VARCHAR(255),
    received_at              TIMESTAMPTZ NOT NULL,
    status                   VARCHAR(12) DEFAULT 'received' NOT NULL,
    category                 VARCHAR(15),
    label                    VARCHAR(20),
    modifies_email_id        VARCHAR(10) REFERENCES emails (email_id),
    forwarded_to             INTEGER REFERENCES users (user_id),
    CONSTRAINT pk_emails PRIMARY KEY (email_id),
    CONSTRAINT ck_emails_status CHECK (status IN ('received', 'classified', 'drafted', 'forwarded')),
    CONSTRAINT ck_emails_category CHECK (category IN ('new_order', 'modify_order', 'price_inquiry', 'complaint', 'other')),
    CONSTRAINT ck_emails_label CHECK (label IN ('new_customer', 'price_inquiry', 'complaint', 'other', 'possible_duplicate', 'has_attachment')),
    CONSTRAINT ck_emails_classified CHECK (status = 'received' OR category IS NOT NULL),
    CONSTRAINT ck_emails_forwarded CHECK (status <> 'forwarded' OR (forwarded_to IS NOT NULL AND label IS NOT NULL))
);
CREATE INDEX ix_emails_received_at ON emails (received_at);
COMMENT ON COLUMN emails.email_id IS 'Mã email (E001…), trùng _id trong raw_emails';
COMMENT ON COLUMN emails.from_email IS 'Địa chỉ người gửi';
COMMENT ON COLUMN emails.from_name IS 'Tên người gửi';
COMMENT ON COLUMN emails.subject IS 'Tiêu đề';
COMMENT ON COLUMN emails.received_at IS 'Thời điểm nhận';
COMMENT ON COLUMN emails.status IS 'received, classified, drafted, forwarded';
COMMENT ON COLUMN emails.category IS 'Kết quả phân loại; trống khi chưa phân loại';
COMMENT ON COLUMN emails.label IS 'Nhãn khi chuyển người phụ trách hoặc cần lưu ý';
COMMENT ON COLUMN emails.modifies_email_id IS 'Email gốc mà email sửa đơn tham chiếu';
COMMENT ON COLUMN emails.forwarded_to IS 'Người nhận khi email được chuyển';
COMMENT ON TABLE emails IS 'Thông tin quản lý và trạng thái của email; nội dung gốc nằm ở MongoDB raw_emails';

-- Đơn hàng từ lúc là đơn nháp đến khi đã xác nhận hoặc đã từ chối
CREATE TABLE orders (
    order_id                 INTEGER GENERATED ALWAYS AS IDENTITY,
    email_id                 VARCHAR(10) NOT NULL UNIQUE REFERENCES emails (email_id),
    customer_id              VARCHAR(10) REFERENCES customers (customer_id),
    ship_address_id          INTEGER REFERENCES customer_addresses (address_id),
    requested_delivery_date  DATE,
    customer_note            TEXT,
    status                   VARCHAR(16) DEFAULT 'draft' NOT NULL,
    address_needs_review     BOOLEAN DEFAULT FALSE NOT NULL,
    date_needs_review        BOOLEAN DEFAULT FALSE NOT NULL,
    adjusts_order_id         INTEGER REFERENCES orders (order_id),
    adjustment_reason        VARCHAR(16),
    created_at               TIMESTAMPTZ DEFAULT now() NOT NULL,
    ready_at                 TIMESTAMPTZ NOT NULL,
    locked_by                INTEGER REFERENCES users (user_id),
    opened_at                TIMESTAMPTZ,
    decided_by               INTEGER REFERENCES users (user_id),
    decided_at               TIMESTAMPTZ,
    reject_reason            TEXT,
    CONSTRAINT pk_orders PRIMARY KEY (order_id),
    CONSTRAINT ck_orders_status CHECK (status IN ('draft', 'needs_review', 'waiting_customer', 'confirmed', 'rejected')),
    CONSTRAINT ck_orders_adjust CHECK ((adjusts_order_id IS NULL) = (adjustment_reason IS NULL)),
    CONSTRAINT ck_orders_adjust_reason CHECK (adjustment_reason IN ('customer_change', 'wrong_sku', 'wrong_qty')),
    CONSTRAINT ck_orders_decided CHECK (status NOT IN ('confirmed', 'rejected') OR (decided_by IS NOT NULL AND decided_at IS NOT NULL)),
    CONSTRAINT ck_orders_reject_reason CHECK (status <> 'rejected' OR length(trim(reject_reason)) > 0),
    CONSTRAINT ck_orders_customer CHECK (customer_id IS NOT NULL OR status IN ('draft', 'needs_review', 'rejected'))
);
CREATE INDEX ix_orders_status_ready ON orders (status, ready_at);
COMMENT ON COLUMN orders.order_id IS 'Mã đơn';
COMMENT ON COLUMN orders.email_id IS 'Email tạo ra đơn; mỗi email tối đa một đơn';
COMMENT ON COLUMN orders.customer_id IS 'Khách đặt hàng; trống thì đơn phải ở Cần kiểm tra';
COMMENT ON COLUMN orders.ship_address_id IS 'Địa chỉ giao';
COMMENT ON COLUMN orders.requested_delivery_date IS 'Ngày giao yêu cầu';
COMMENT ON COLUMN orders.customer_note IS 'Ghi chú nguyên văn của khách';
COMMENT ON COLUMN orders.status IS 'draft, needs_review, waiting_customer, confirmed, rejected';
COMMENT ON COLUMN orders.address_needs_review IS 'Địa chỉ do hệ thống điền mặc định, cần kiểm tra';
COMMENT ON COLUMN orders.date_needs_review IS 'Ngày giao do hệ thống điền mặc định, cần kiểm tra';
COMMENT ON COLUMN orders.adjusts_order_id IS 'Đơn gốc đã xác nhận mà đơn điều chỉnh này sửa';
COMMENT ON COLUMN orders.adjustment_reason IS 'customer_change, wrong_sku hoặc wrong_qty';
COMMENT ON COLUMN orders.created_at IS 'Thời điểm tạo đơn nháp';
COMMENT ON COLUMN orders.ready_at IS 'Thời điểm đưa vào danh sách duyệt (8h00 với email sau 17h00)';
COMMENT ON COLUMN orders.locked_by IS 'Sales Admin đang mở đơn';
COMMENT ON COLUMN orders.opened_at IS 'Lần đầu Sales Admin mở đơn';
COMMENT ON COLUMN orders.decided_by IS 'Sales Admin xác nhận hoặc từ chối';
COMMENT ON COLUMN orders.decided_at IS 'Thời điểm xác nhận hoặc từ chối';
COMMENT ON COLUMN orders.reject_reason IS 'Lý do từ chối, bắt buộc khi từ chối';
COMMENT ON TABLE orders IS 'Đơn hàng từ lúc là đơn nháp đến khi đã xác nhận hoặc đã từ chối';

-- Dòng hàng của đơn: tên gọi gốc, kết quả đối chiếu SKU, số lượng đã quy đổi
CREATE TABLE order_items (
    item_id                  INTEGER GENERATED ALWAYS AS IDENTITY,
    order_id                 INTEGER NOT NULL REFERENCES orders (order_id) ON DELETE CASCADE,
    line_no                  SMALLINT NOT NULL,
    product_text             VARCHAR(200) NOT NULL,
    qty_raw                  NUMERIC(10,2),
    unit_raw                 VARCHAR(20),
    sku                      VARCHAR(10) REFERENCES products (sku),
    qty_base                 NUMERIC(12,2),
    match_score              SMALLINT,
    match_status             VARCHAR(10) NOT NULL,
    CONSTRAINT pk_order_items PRIMARY KEY (item_id),
    CONSTRAINT uq_order_items_line UNIQUE (order_id, line_no),
    CONSTRAINT ck_order_items_score CHECK (match_score BETWEEN 0 AND 100),
    CONSTRAINT ck_order_items_match CHECK (match_status IN ('matched', 'suggested', 'unmatched', 'manual')),
    CONSTRAINT ck_order_items_qty CHECK (qty_raw > 0 AND qty_base > 0)
);
COMMENT ON COLUMN order_items.item_id IS 'Mã dòng';
COMMENT ON COLUMN order_items.order_id IS 'Đơn chứa dòng hàng';
COMMENT ON COLUMN order_items.line_no IS 'Số thứ tự dòng trong đơn';
COMMENT ON COLUMN order_items.product_text IS 'Tên gọi như khách viết';
COMMENT ON COLUMN order_items.qty_raw IS 'Số lượng như khách viết; trống nếu email không nêu';
COMMENT ON COLUMN order_items.unit_raw IS 'Đơn vị như khách viết';
COMMENT ON COLUMN order_items.sku IS 'Mã hàng đã khớp hoặc người đã chọn';
COMMENT ON COLUMN order_items.qty_base IS 'Số lượng đã quy đổi ra đơn vị bán';
COMMENT ON COLUMN order_items.match_score IS 'Điểm tương đồng 0–100 của mã đang chọn';
COMMENT ON COLUMN order_items.match_status IS 'matched, suggested, unmatched hoặc manual (người chọn)';
COMMENT ON TABLE order_items IS 'Dòng hàng của đơn: tên gọi gốc, kết quả đối chiếu SKU, số lượng đã quy đổi';

-- Tối đa 3 mã gợi ý cho dòng hàng có điểm 75–89
CREATE TABLE order_item_suggestions (
    item_id                  INTEGER REFERENCES order_items (item_id) ON DELETE CASCADE,
    rank                     SMALLINT,
    sku                      VARCHAR(10) NOT NULL REFERENCES products (sku),
    score                    SMALLINT NOT NULL,
    CONSTRAINT pk_order_item_suggestions PRIMARY KEY (item_id, rank),
    CONSTRAINT ck_suggestions_rank CHECK (rank BETWEEN 1 AND 3),
    CONSTRAINT ck_suggestions_score CHECK (score BETWEEN 0 AND 100),
    CONSTRAINT uq_suggestions_sku UNIQUE (item_id, sku)
);
COMMENT ON COLUMN order_item_suggestions.item_id IS 'Dòng hàng';
COMMENT ON COLUMN order_item_suggestions.rank IS 'Thứ hạng gợi ý 1–3';
COMMENT ON COLUMN order_item_suggestions.sku IS 'Mã gợi ý';
COMMENT ON COLUMN order_item_suggestions.score IS 'Điểm tương đồng 0–100';
COMMENT ON TABLE order_item_suggestions IS 'Tối đa 3 mã gợi ý cho dòng hàng có điểm 75–89';

-- Nhật ký mỗi lần đơn bị sửa sau khi tạo: do người sửa (BR-10) hoặc do email sửa đơn của khách (BR-09); chỉ được thêm
CREATE TABLE order_edit_logs (
    log_id                   BIGINT GENERATED ALWAYS AS IDENTITY,
    order_id                 INTEGER NOT NULL REFERENCES orders (order_id),
    item_id                  INTEGER REFERENCES order_items (item_id) ON DELETE SET NULL,
    field_name               VARCHAR(40) NOT NULL,
    old_value                TEXT,
    new_value                TEXT,
    edited_by                INTEGER REFERENCES users (user_id),
    source_email_id          VARCHAR(10) REFERENCES emails (email_id),
    edited_at                TIMESTAMPTZ DEFAULT now() NOT NULL,
    CONSTRAINT pk_order_edit_logs PRIMARY KEY (log_id),
    CONSTRAINT ck_edit_logs_actor CHECK ((edited_by IS NULL) <> (source_email_id IS NULL))
);
CREATE INDEX ix_order_edit_logs_order ON order_edit_logs (order_id);
COMMENT ON COLUMN order_edit_logs.log_id IS 'Mã nhật ký';
COMMENT ON COLUMN order_edit_logs.order_id IS 'Đơn bị sửa';
COMMENT ON COLUMN order_edit_logs.item_id IS 'Dòng bị sửa; trống nếu sửa phần đầu đơn';
COMMENT ON COLUMN order_edit_logs.field_name IS 'Trường bị sửa (sku, qty_base, requested_delivery_date…)';
COMMENT ON COLUMN order_edit_logs.old_value IS 'Giá trị cũ';
COMMENT ON COLUMN order_edit_logs.new_value IS 'Giá trị mới';
COMMENT ON COLUMN order_edit_logs.edited_by IS 'Người sửa; trống nếu thay đổi đến từ email sửa đơn';
COMMENT ON COLUMN order_edit_logs.source_email_id IS 'Email sửa đơn gây ra thay đổi';
COMMENT ON COLUMN order_edit_logs.edited_at IS 'Thời điểm sửa';
COMMENT ON TABLE order_edit_logs IS 'Nhật ký mỗi lần đơn bị sửa sau khi tạo: do người sửa (BR-10) hoặc do email sửa đơn của khách (BR-09); chỉ được thêm';

-- Kết quả tạo Sales Order trong SAP cho đơn đã xác nhận
CREATE TABLE sap_sales_orders (
    order_id                 INTEGER REFERENCES orders (order_id),
    sales_order_no           VARCHAR(10) UNIQUE,
    request_status           VARCHAR(10) DEFAULT 'pending' NOT NULL,
    attempt_count            SMALLINT DEFAULT 0 NOT NULL,
    last_error               TEXT,
    requested_at             TIMESTAMPTZ DEFAULT now() NOT NULL,
    completed_at             TIMESTAMPTZ,
    CONSTRAINT pk_sap_sales_orders PRIMARY KEY (order_id),
    CONSTRAINT ck_sap_status CHECK (request_status IN ('pending', 'success', 'error')),
    CONSTRAINT ck_sap_success CHECK (request_status <> 'success' OR (sales_order_no IS NOT NULL AND completed_at IS NOT NULL))
);
COMMENT ON COLUMN sap_sales_orders.order_id IS 'Đơn đã xác nhận';
COMMENT ON COLUMN sap_sales_orders.sales_order_no IS 'Số Sales Order SAP trả về';
COMMENT ON COLUMN sap_sales_orders.request_status IS 'pending, success hoặc error';
COMMENT ON COLUMN sap_sales_orders.attempt_count IS 'Số lần gọi API';
COMMENT ON COLUMN sap_sales_orders.last_error IS 'Thông báo lỗi gần nhất của API';
COMMENT ON COLUMN sap_sales_orders.requested_at IS 'Lần gọi API đầu tiên';
COMMENT ON COLUMN sap_sales_orders.completed_at IS 'Thời điểm SAP tạo đơn thành công';
COMMENT ON TABLE sap_sales_orders IS 'Kết quả tạo Sales Order trong SAP cho đơn đã xác nhận';

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
