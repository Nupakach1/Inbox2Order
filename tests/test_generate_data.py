"""Kiểm thử bộ dữ liệu mẫu khớp đúng mô tả ở mục 1.3.3 và 7.1 báo cáo."""
import csv
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "data" / "generated"
LAB = ROOT / "data" / "labels"


def load_csv(name):
    with open(GEN / name, encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest():
    h = hashlib.sha256()
    for p in sorted(list(GEN.glob("*")) + list(LAB.glob("*"))):
        h.update(p.read_bytes())
    return h.hexdigest()


def test_counts():
    assert len(load_csv("products.csv")) == 120
    assert len(load_csv("product_aliases.csv")) == 60
    assert len(load_csv("customers.csv")) == 30
    assert len(load_json(GEN / "emails_dev.json")) == 30
    assert len(load_json(GEN / "emails_test.json")) == 30
    assert len(load_json(LAB / "ground_truth_test.json")) == 30


def test_test_set_composition():
    labels = load_json(LAB / "ground_truth_test.json")
    cats = Counter(l["category"] for l in labels)
    assert cats == {"new_order": 26, "modify_order": 2, "price_inquiry": 1, "other": 1}
    flags = Counter(k for l in labels for k in l["flags"])
    assert flags["missing"] == 3
    assert flags["unknown_sender"] == 1
    assert flags["qty_anomaly_sku"] == 1


def test_every_test_email_has_one_label():
    emails = {e["email_id"] for e in load_json(GEN / "emails_test.json")}
    labels = {l["email_id"] for l in load_json(LAB / "ground_truth_test.json")}
    assert emails == labels


def test_labels_reference_valid_data():
    skus = {p["sku"] for p in load_csv("products.csv")}
    customers = {c["customer_id"] for c in load_csv("customers.csv")}
    all_ids = {e["email_id"] for e in load_json(GEN / "emails_dev.json") + load_json(GEN / "emails_test.json")}
    for l in load_json(LAB / "ground_truth_test.json"):
        assert l["customer_id"] is None or l["customer_id"] in customers
        if l["modifies_email_id"]:
            assert l["modifies_email_id"] in all_ids
        for ln in l["lines"]:
            assert ln["sku"] is None or ln["sku"] in skus


def test_unknown_sender_not_in_customer_list():
    emails = {c["email"] for c in load_csv("customers.csv")}
    test = {e["email_id"]: e for e in load_json(GEN / "emails_test.json")}
    for l in load_json(LAB / "ground_truth_test.json"):
        if l["flags"].get("unknown_sender"):
            assert test[l["email_id"]]["from_email"] not in emails


def test_after_cutoff_share_about_15_percent():
    all_emails = load_json(GEN / "emails_dev.json") + load_json(GEN / "emails_test.json")
    late = sum(int(e["received_at"][11:13]) >= 17 for e in all_emails)
    assert 8 <= late <= 11


def test_aliases_point_to_existing_sku():
    skus = {p["sku"] for p in load_csv("products.csv")}
    assert all(a["sku"] in skus for a in load_csv("product_aliases.csv"))


def test_only_example_domains():
    for c in load_csv("customers.csv"):
        assert c["email"].endswith(".example.vn")


def test_regeneration_is_reproducible():
    before = digest()
    subprocess.run([sys.executable, str(ROOT / "src" / "generate_data.py")], check=True, capture_output=True)
    assert digest() == before
