"""Targeted fuzz campaign for Tatou's get-version/<link> endpoint.

THIS IS MY FUZZING CAMPAIN ONE 
Usage:
    TATOU_BASE=http://127.0.0.1:5000 TATOU_ROUTE=/get-version/ \
    VALID_LINK=<a real 32-hex link> python fuzz_get_version.py

Results are written to fuzz_get_version_results.csv.
"""
import csv
import os
import random
import string
import time
from urllib.parse import quote

import requests

BASE = os.environ.get("TATOU_BASE", "http://127.0.0.1:5000").rstrip("/")
ROUTE = os.environ.get("TATOU_ROUTE", "/api/get-version/")
VALID_LINK = os.environ.get("VALID_LINK")
SEED = int(os.environ.get("SEED", "1"))
N_RANDOM = int(os.environ.get("N_RANDOM", "200"))
TIMEOUT = 8
SLOW_SECONDS = 2.0
LEAK_MARKERS = ("Traceback", 'File "', "/app/", "sqlalchemy", "pymysql", "mariadb")
HEX = "0123456789abcdef"


def rnd(chars, n, rng):
    return "".join(rng.choice(chars) for _ in range(n))


def build_cases(rng):
    """Return a list of (input_class, path) tuples."""
    h32 = rnd(HEX, 32, rng)
    segs = []
    for n in (1, 16, 31, 32, 33, 64, 256, 1000, 4000, 5000):
        segs.append(("length_hex", rnd(HEX, n, rng)))
    segs.append(("uppercase_hex", h32.upper()))
    segs.append(("non_hex", "g" * 32))
    segs.append(("whitespace", quote(" " + h32, safe="")))
    segs.append(("whitespace", quote(h32 + " ", safe="")))
    segs.append(("whitespace", "%09" + h32))
    segs.append(("control_chars", "%00"))
    segs.append(("control_chars", h32 + "%00"))
    segs.append(("control_chars", "%0d%0a"))
    for payload in ("' OR '1'='1", "'; SELECT SLEEP(3);--", '" OR ""="'):
        segs.append(("sql_style", quote(payload, safe="")))
    for payload in ("..%2f..%2fetc%2fpasswd", "%2e%2e%2f" * 3, "%252e%252e%252f"):
        segs.append(("traversal", payload))
    segs.append(("unicode", quote("\u00e9" * 32, safe="")))
    segs.append(("unicode", quote("\u202e" + h32, safe="")))
    segs.append(("unicode", quote("\U0001F600" * 16, safe="")))
    alphabet = string.printable.strip() + "\u00e9\u4e2d"
    for _ in range(N_RANDOM):
        segs.append(("random", quote(rnd(alphabet, rng.randint(1, 80), rng), safe="")))

    cases = [(cls, ROUTE + seg) for cls, seg in segs]
    cases.append(("layer_check", "/nonexistent/" + "a" * 5000))
    if VALID_LINK:
        cases.insert(0, ("positive_control", ROUTE + VALID_LINK))
    return cases


def classify(cls, status, elapsed, body):
    flags = []
    if status >= 500:
        flags.append("5xx")
    if elapsed > SLOW_SECONDS:
        flags.append("slow")
    if any(m in body for m in LEAK_MARKERS):
        flags.append("possible_leak")
    if cls == "positive_control":
        if status != 200:
            flags.append("control_failed")
    elif status == 200:
        flags.append("unexpected_200")
    elif status not in (400, 404):
        flags.append("unexpected_status")
    return flags


def main():
    rng = random.Random(SEED)
    cases = build_cases(rng)
    session = requests.Session()
    rows = []
    for cls, path in cases:
        start = time.time()
        try:
            resp = session.get(BASE + path, timeout=TIMEOUT)
            elapsed = time.time() - start
            body = resp.text[:300]
            flags = classify(cls, resp.status_code, elapsed, body)
            rows.append([cls, path[:90], resp.status_code, round(elapsed, 4),
                         len(resp.content), ";".join(flags), body[:100].replace("\n", " ")])
        except requests.RequestException as exc:
            elapsed = time.time() - start
            rows.append([cls, path[:90], "", round(elapsed, 4), 0,
                         "request_error", type(exc).__name__])

    with open("fuzz_get_version_results.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["class", "path", "status", "seconds", "body_len", "flags", "body_start"])
        w.writerows(rows)

    flagged = [r for r in rows if r[5]]
    print(f"{len(rows)} requests sent, {len(flagged)} flagged for triage")
    for r in flagged:
        print(r[0], r[1][:50], r[2], r[5])


if __name__ == "__main__":
    main()
