"""Cấu hình chung cho toàn bộ mã nguồn Inbox2Order."""
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
GENERATED_DIR = DATA_DIR / "generated"
LABELS_DIR = DATA_DIR / "labels"
EVAL_DIR = ROOT / "evaluation"
PROMPTS_DIR = ROOT / "src" / "prompts"

# Sinh dữ liệu: seed cố định để chạy lại ra cùng kết quả (mục 1.3.3 báo cáo)
SEED = 20261102

# Tuần dữ liệu email: thứ Hai 02/11/2026 đến thứ Bảy 07/11/2026
WEEK_START = "2026-11-02"
CUTOFF_HOUR = 17          # BR-12: mốc 17h00
WORK_START_HOUR = 8       # BR-12: đơn nháp sẵn sàng lúc 8h00

# BR-04: ngưỡng điểm tương đồng khi đối chiếu SKU
SKU_MATCH_THRESHOLD = 90
SKU_SUGGEST_THRESHOLD = 75
SKU_SUGGEST_TOP_K = 3

# BR-08: ngưỡng phát hiện email trùng
DUPLICATE_SIMILARITY = 90
DUPLICATE_WINDOW_HOURS = 24

COMPANY_INBOX = "donhang@anphat.example.vn"


def env(name, default=None):
    """Đọc biến môi trường (khóa API, kết nối CSDL) từ .env nếu có."""
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
    return os.environ.get(name, default)
