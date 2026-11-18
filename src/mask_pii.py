"""Che thông tin cá nhân trước khi gửi nội dung email cho mô hình AI (BR-14, FR-02, NFR-03).

Che ba loại: số điện thoại, số tài khoản ngân hàng, khối chữ ký cá nhân ở cuối email.
Chỉ trả về phần nội dung cần cho phân loại và trích xuất (tiêu đề + thân email đã che);
địa chỉ email người gửi không gửi cho AI vì hệ thống tự tra khách hàng theo địa chỉ này (BR-02).

    from mask_pii import mask_email
    masked, counts = mask_email(email_dict)
"""
import re
import unicodedata

PHONE_TAG, ACCOUNT_TAG, SIGNATURE_TAG = "[SĐT]", "[STK]", "[CHỮ KÝ]"

# Số tài khoản: có từ khóa đi trước (STK, số tài khoản, TK, account) rồi dãy 6–20 chữ số, có thể có dấu cách/gạch.
ACCOUNT_RE = re.compile(
    r"(?i)(\b(?:stk|s[ốo] t[àa]i kho[ảa]n|tk|t[àa]i kho[ảa]n|account|acc)\b\s*(?:s[ốo])?\s*[:.\-]?\s*)"
    r"(\d[\d .\-]{4,22}\d)")
# Số điện thoại Việt Nam: 0 hoặc +84/84 rồi 8–10 chữ số, cho phép dấu cách, chấm, gạch giữa các nhóm.
PHONE_RE = re.compile(r"(?<![\w\d])(?:\+?84|0)(?:[ .\-]?\d){8,10}(?![\w\d])")
# Dòng chỉ chứa nhãn liên hệ (ĐT, SĐT, Tel, Mobile, Zalo, Hotline) thường nằm trong chữ ký.
CONTACT_LINE_RE = re.compile(r"(?i)^\s*(?:đt|sđt|dt|sdt|tel|mobile|phone|hotline|zalo|di động)\s*[:.]")
CLOSINGS = ("cảm ơn", "cám ơn", "trân trọng", "thanks", "thank you", "best regards", "regards", "tks", "thân", "--")


def _plain(s):
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("đ", "d").strip()


def _signature_start(lines, from_name):
    """Vị trí dòng bắt đầu khối chữ ký: dòng trùng tên người gửi trong 5 dòng cuối,
    hoặc dòng '--', hoặc dòng nhãn liên hệ cuối email."""
    n = len(lines)
    name = _plain(from_name or "")
    for i in range(max(0, n - 5), n):
        p = _plain(lines[i])
        if p == "--" or (name and p == name):
            return i
    for i in range(max(0, n - 3), n):
        if CONTACT_LINE_RE.match(lines[i]):
            return i
    return None


def mask_text(body, from_name=None):
    counts = {"phone": 0, "bank_account": 0, "signature": 0}
    lines = body.rstrip().split("\n")
    start = _signature_start(lines, from_name)
    if start is not None:
        counts["phone"] += len(PHONE_RE.findall("\n".join(lines[start:])))
        lines = lines[:start] + [SIGNATURE_TAG]
        counts["signature"] = 1
    text = "\n".join(lines)
    text, k = ACCOUNT_RE.subn(lambda m: m.group(1) + ACCOUNT_TAG, text)
    counts["bank_account"] = k
    text, k = PHONE_RE.subn(PHONE_TAG, text)
    counts["phone"] += k
    # Tên người gửi còn sót trong thân (ví dụ ký ở cuối câu) cũng được che.
    if from_name and len(from_name) > 3:
        text, k = re.subn(re.escape(from_name), SIGNATURE_TAG, text)
        counts["signature"] += k
    return text, counts


def mask_email(email):
    """Trả về (nội dung gửi AI, số chỗ đã che theo loại)."""
    body, counts = mask_text(email["body"], email.get("from_name"))
    subject, c2 = mask_text(email.get("subject") or "", None)
    for k in counts:
        counts[k] += c2[k]
    return f"Tiêu đề: {subject}\nThời điểm nhận: {email['received_at']}\n\n{body}", counts


def has_pii(text, email=None):
    """Kiểm tra còn sót thông tin cá nhân không (dùng trong kiểm thử NFR-03)."""
    if PHONE_RE.search(text) or ACCOUNT_RE.search(text):
        return True
    if email and email.get("from_name") and email["from_name"] in text:
        return True
    return False
