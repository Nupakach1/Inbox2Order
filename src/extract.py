"""Gọi mô hình AI để phân loại và trích xuất đơn hàng (FR-03, FR-05), lưu kết quả nguyên văn.

Ba bước, đúng quy trình chấm ở mục 7.1 báo cáo:
    python src/extract.py prepare dev|test
        Che PII từng email (BR-14) và ghi evaluation/results/inputs_<tập>.json: đúng nội dung sẽ gửi cho mô hình.
    python src/extract.py api dev|test
        Có ANTHROPIC_API_KEY và AI_MODEL trong .env: gọi API, thử lại tối đa 3 lần (NFR-06, EX-03).
    python src/extract.py import dev|test <tệp_trả_lời.json> --model "<tên mô hình>" --channel "<cách chạy>"
        Không có khóa API: chạy thủ công trên giao diện chat với cùng prompt, lưu các câu trả lời
        (một đối tượng {email_id: chuỗi JSON mô hình trả về}) rồi nhập vào đây. Không sửa câu trả lời trước khi nhập.

Kết quả: evaluation/results/ai_output_<tập>.json, mỗi phần tử theo cấu trúc collection ai_extractions (mục 5.8.5).
"""
import argparse
import json
import time
from datetime import datetime, timezone

from config import GENERATED_DIR, EVAL_DIR, PROMPTS_DIR, env
from mask_pii import mask_email

PROMPT_VERSION = "extract_v1"
RESULTS = EVAL_DIR / "results"
CATEGORIES = {"new_order", "modify_order", "price_inquiry", "complaint", "other"}


def load_set(name):
    return json.loads((GENERATED_DIR / f"emails_{name}.json").read_text(encoding="utf-8"))


def prompt_text():
    return (PROMPTS_DIR / f"{PROMPT_VERSION}.txt").read_text(encoding="utf-8")


def prepare(name):
    tpl = prompt_text()
    rows = []
    for e in load_set(name):
        masked, counts = mask_email(e)
        rows.append({"email_id": e["email_id"], "masked_input": masked, "mask_counts": counts,
                     "prompt": tpl.replace("{masked_email}", masked)})
    out = RESULTS / f"inputs_{name}.json"
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Ghi", out, len(rows), "email")
    return rows


def parse_output(raw):
    """Kiểm tra JSON đúng cấu trúc tối thiểu; sai thì trả (None, lỗi) – EX-04."""
    try:
        s = raw.strip()
        if s.startswith("```"):
            s = s.strip("`").split("\n", 1)[1].rsplit("```", 1)[0]
        obj = json.loads(s)
    except Exception as ex:  # noqa: BLE001
        return None, f"invalid_json: {ex}"
    if obj.get("category") not in CATEGORIES or not isinstance(obj.get("lines"), list):
        return None, "invalid_json: thiếu category hoặc lines"
    for k in ("customer_name", "delivery_date", "delivery_address", "note", "modifies_reference"):
        obj.setdefault(k, None)
    return obj, None


def record(row, raw, model, run_at, attempt=1, latency_ms=None, channel=None):
    out, err = parse_output(raw) if raw is not None else (None, "timeout")
    return {"email_id": row["email_id"], "model": model, "prompt_version": PROMPT_VERSION, "channel": channel,
            "run_at": run_at, "attempt": attempt, "status": "ok" if out else err.split(":")[0],
            "latency_ms": latency_ms, "masked_input": row["masked_input"], "mask_counts": row["mask_counts"],
            "raw_response": raw, "output": out, "error": err}


def save(name, docs):
    out = RESULTS / f"ai_output_{name}.json"
    if name == "test" and out.exists():
        raise SystemExit("Tập kiểm tra chỉ chạy một lần (mục 7.1): đã có ai_output_test.json, không ghi đè.")
    out.write_text(json.dumps(docs, ensure_ascii=False, indent=2), encoding="utf-8")
    ok = sum(d["status"] == "ok" for d in docs)
    print("Ghi", out, f"{ok}/{len(docs)} kết quả hợp lệ")


def run_api(name):
    import anthropic
    model = env("AI_MODEL")
    client = anthropic.Anthropic(api_key=env("ANTHROPIC_API_KEY"))
    docs = []
    for row in prepare(name):
        raw, t0, attempt = None, time.time(), 0
        for attempt in range(1, 4):
            try:
                msg = client.messages.create(model=model, max_tokens=1500, temperature=0,
                                             messages=[{"role": "user", "content": row["prompt"]}])
                raw = msg.content[0].text
                if parse_output(raw)[0]:
                    break
            except Exception:  # noqa: BLE001
                time.sleep(2 * attempt)
        docs.append(record(row, raw, model, datetime.now(timezone.utc).isoformat(), attempt,
                           int((time.time() - t0) * 1000), "api"))
    save(name, docs)


def run_import(name, path, model, channel, run_at):
    answers = json.loads(open(path, encoding="utf-8").read())
    rows = {r["email_id"]: r for r in json.loads((RESULTS / f"inputs_{name}.json").read_text(encoding="utf-8"))}
    missing = set(rows) - set(answers)
    if missing:
        raise SystemExit(f"Thiếu câu trả lời cho {sorted(missing)}")
    docs = [record(rows[eid], answers[eid] if isinstance(answers[eid], str) else json.dumps(answers[eid], ensure_ascii=False),
                   model, run_at, channel=channel) for eid in sorted(rows)]
    save(name, docs)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["prepare", "api", "import"])
    ap.add_argument("set", choices=["dev", "test"])
    ap.add_argument("answers", nargs="?")
    ap.add_argument("--model", default="")
    ap.add_argument("--channel", default="chat")
    ap.add_argument("--run-at", default=datetime.now(timezone.utc).isoformat())
    a = ap.parse_args()
    if a.cmd == "prepare":
        prepare(a.set)
    elif a.cmd == "api":
        run_api(a.set)
    else:
        run_import(a.set, a.answers, a.model, a.channel, a.run_at)
