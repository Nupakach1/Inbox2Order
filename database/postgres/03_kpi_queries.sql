-- Inbox2Order – Truy vấn KPI-01 đến KPI-04 theo đúng cách đo ở Bảng 4.1 (mục 4.1 báo cáo)
-- Mọi mốc thời gian quy về giờ Việt Nam; mốc 17h00 theo BR-12.
-- Dashboard MH-04 (UC-06, FR-23) đọc từ các truy vấn này.
SET search_path TO i2o;

-- ---------------------------------------------------------------------------
-- KPI-01 Thời gian xử lý trung bình mỗi đơn (phút)
-- Cách đo: từ lúc Sales Admin mở đơn nháp đến lúc xác nhận hoặc từ chối.
-- Mục tiêu ≤ 1,5 phút. Theo ngày và theo Sales Admin.
-- ---------------------------------------------------------------------------
SELECT (o.decided_at AT TIME ZONE 'Asia/Ho_Chi_Minh')::date              AS ngay,
       u.full_name                                                       AS sales_admin,
       count(*)                                                          AS so_don,
       round(avg(extract(epoch FROM o.decided_at - o.opened_at)) / 60, 2) AS kpi01_phut
FROM orders o
JOIN users u ON u.user_id = o.decided_by
WHERE o.status IN ('confirmed', 'rejected') AND o.opened_at IS NOT NULL
GROUP BY 1, 2
ORDER BY 1, 2;

-- ---------------------------------------------------------------------------
-- KPI-02 Tỷ lệ đơn nháp phải sửa (%)
-- Cách đo: số đơn nháp có ít nhất một trường bị người sửa (nhật ký BR-10; không tính thay đổi do email sửa đơn)
--          ÷ tổng số đơn nháp đã duyệt. Mục tiêu < 20%.
-- ---------------------------------------------------------------------------
SELECT (o.decided_at AT TIME ZONE 'Asia/Ho_Chi_Minh')::date AS ngay,
       count(*)                                            AS don_da_duyet,
       count(*) FILTER (WHERE EXISTS (SELECT 1 FROM order_edit_logs l WHERE l.order_id = o.order_id AND l.edited_by IS NOT NULL))
                                                           AS don_phai_sua,
       round(100.0 * count(*) FILTER (WHERE EXISTS (SELECT 1 FROM order_edit_logs l WHERE l.order_id = o.order_id AND l.edited_by IS NOT NULL))
             / count(*), 1)                                AS kpi02_phan_tram
FROM orders o
WHERE o.status IN ('confirmed', 'rejected')
GROUP BY 1
ORDER BY 1;

-- ---------------------------------------------------------------------------
-- KPI-03 Tỷ lệ đơn sai lọt qua sau khi duyệt (%)
-- Cách đo: số đơn đã xác nhận phải tạo đơn điều chỉnh vì sai mã hàng hoặc số lượng
--          (adjustment_reason = wrong_sku, wrong_qty; BR-09) ÷ tổng số đơn đã xác nhận.
-- Mục tiêu < 1%. Tính theo ngày xác nhận của đơn gốc.
-- ---------------------------------------------------------------------------
SELECT (g.decided_at AT TIME ZONE 'Asia/Ho_Chi_Minh')::date AS ngay,
       count(*)                                            AS don_da_xac_nhan,
       count(*) FILTER (WHERE EXISTS (SELECT 1 FROM orders a WHERE a.adjusts_order_id = g.order_id
                                       AND a.adjustment_reason IN ('wrong_sku', 'wrong_qty')))
                                                           AS don_sai_lot_qua,
       round(100.0 * count(*) FILTER (WHERE EXISTS (SELECT 1 FROM orders a WHERE a.adjusts_order_id = g.order_id
                                                    AND a.adjustment_reason IN ('wrong_sku', 'wrong_qty')))
             / count(*), 1)                                AS kpi03_phan_tram
FROM orders g
WHERE g.status = 'confirmed'
GROUP BY 1
ORDER BY 1;

-- ---------------------------------------------------------------------------
-- KPI-04 Tỷ lệ đơn nhận trước 17h00 được xác nhận trong ngày (%)
-- Cách đo: số đơn nhận trước 17h00 có thời điểm xác nhận cùng ngày
--          ÷ tổng số đơn nhận trước 17h00. Mục tiêu ≥ 95%.
-- ---------------------------------------------------------------------------
SELECT (e.received_at AT TIME ZONE 'Asia/Ho_Chi_Minh')::date AS ngay,
       count(*)                                             AS don_truoc_17h,
       count(*) FILTER (WHERE o.status = 'confirmed'
                        AND (o.decided_at AT TIME ZONE 'Asia/Ho_Chi_Minh')::date
                            = (e.received_at AT TIME ZONE 'Asia/Ho_Chi_Minh')::date)
                                                            AS xac_nhan_trong_ngay,
       round(100.0 * count(*) FILTER (WHERE o.status = 'confirmed'
                                      AND (o.decided_at AT TIME ZONE 'Asia/Ho_Chi_Minh')::date
                                          = (e.received_at AT TIME ZONE 'Asia/Ho_Chi_Minh')::date)
             / count(*), 1)                                 AS kpi04_phan_tram
FROM orders o
JOIN emails e ON e.email_id = o.email_id
WHERE (e.received_at AT TIME ZONE 'Asia/Ho_Chi_Minh')::time < TIME '17:00'
GROUP BY 1
ORDER BY 1;

-- ---------------------------------------------------------------------------
-- Cảnh báo 16h30 (FR-22, BR-12): đơn nhận trước 17h00 hôm nay mà chưa duyệt.
-- n8n chạy truy vấn này lúc 16h30 và gửi kết quả cho Trưởng phòng kinh doanh.
-- ---------------------------------------------------------------------------
SELECT q.order_id, q.email_id, q.customer_name, q.status, q.received_at, q.locked_by_name
FROM v_review_queue q
WHERE q.before_cutoff
  AND (q.received_at AT TIME ZONE 'Asia/Ho_Chi_Minh')::date = (now() AT TIME ZONE 'Asia/Ho_Chi_Minh')::date
ORDER BY q.received_at;
