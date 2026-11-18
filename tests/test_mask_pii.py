"""Kiểm thử che thông tin cá nhân (BR-14, NFR-03): không còn số điện thoại, số tài khoản, chữ ký cá nhân."""
import json

from config import GENERATED_DIR
from mask_pii import has_pii, mask_email, mask_text


def all_emails():
    return json.loads((GENERATED_DIR / "emails_dev.json").read_text(encoding="utf-8")) + \
        json.loads((GENERATED_DIR / "emails_test.json").read_text(encoding="utf-8"))


def test_no_pii_left_in_60_emails():
    for e in all_emails():
        masked, counts = mask_email(e)
        assert not has_pii(masked, e), e["email_id"]
        assert counts["signature"] >= 1, e["email_id"]
        assert e["from_email"] not in masked


def test_order_content_is_kept():
    e = {"email_id": "X", "from_name": "Chị Mai", "subject": "Đơn", "received_at": "2026-11-02T09:00",
         "body": "Gửi em 5 hộp bút bi xanh 0.5, giao thứ 6.\nChị Mai\nĐT: 0909 123 456"}
    masked, counts = mask_email(e)
    assert "5 hộp bút bi xanh 0.5" in masked and "0909" not in masked and "Chị Mai" not in masked
    assert counts == {"phone": 1, "bank_account": 0, "signature": 1}


def test_phone_and_account_formats():
    for raw in ["gọi 0912.345.678 nhé", "sđt +84 912 345 678", "liên hệ 0283-123-4567"]:
        assert "[SĐT]" in mask_text(raw)[0], raw
    t, c = mask_text("chuyển khoản STK: 0071 0012 34567 Vietcombank")
    assert "[STK]" in t and "34567" not in t and c["bank_account"] == 1
    t, _ = mask_text("số tài khoản 1903 5555 8888 nhé")
    assert "8888" not in t


def test_quantities_and_sizes_not_masked():
    t, c = mask_text("2 thùng giấy A4 70, 36 hộp bút 0.7, giao ngày 05/11")
    assert t == "2 thùng giấy A4 70, 36 hộp bút 0.7, giao ngày 05/11" and c["phone"] == 0
