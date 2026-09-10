"""Parses real BIND9 `named.log` query-log lines (the format Ovnicom's dnstap
pipeline produces) and streams them indefinitely. Optional: only used when a
real capture is present under `data/dns_logs/` (see generator.py); otherwise
the fully-synthetic generator is the whole story.

Line shape:
09-Sep-2026 08:04:59.901 queries: info: client @0x7fa2... 190.102.59.241#35082 \
    (www.apple.com): query: www.apple.com IN A + (172.19.1.2)
"""
import re
from datetime import datetime
from pathlib import Path
from typing import Iterator

_LINE_RE = re.compile(
    r"^(?P<ts>\d{2}-\w{3}-\d{4} \d{2}:\d{2}:\d{2}\.\d{3}) "
    r"queries: info: client @\S+ (?P<ip>[\d.]+)#\d+ \([^)]+\): query: "
    r"(?P<qname>\S+) IN (?P<qtype>\S+)"
)


def parse_line(line: str) -> dict | None:
    m = _LINE_RE.match(line)
    if not m:
        return None
    try:
        ts = datetime.strptime(m["ts"], "%d-%b-%Y %H:%M:%S.%f").timestamp()
    except ValueError:
        return None
    return {"ts": ts, "client_ip": m["ip"], "qname": m["qname"], "qtype": m["qtype"]}


def stream_real_events(log_dir: Path) -> Iterator[dict]:
    """Cycle through every queries.* file in log_dir forever, yielding parsed
    records one line at a time. Files are read lazily (never loaded whole) so
    this is cheap regardless of how large the capture is; looping back to the
    start on exhaustion keeps the stream live for a demo of any length."""
    files = sorted(log_dir.glob("queries.*"))
    if not files:
        return
    while True:
        for path in files:
            with open(path, encoding="utf-8", errors="replace") as f:
                for line in f:
                    record = parse_line(line)
                    if record:
                        yield record
