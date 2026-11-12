#!/usr/bin/env python3
"""Map data-model ids by diffing snapshots while the heater is changed by hand.

Read-only: only sends CMD 1. Usage:

    python3 scripts/map_ids.py 192.168.1.22

At each prompt, change one thing on the heater (mode, setpoint...), type a
label for it and press Enter: the ids that changed since the previous
snapshot are printed and everything is logged to mapping-<timestamp>.jsonl.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request
from datetime import datetime

BLOCKS = (range(4000, 4200), range(8500, 8600), range(1300, 1320), (570, 571, 573))


def read(host: str, data_id: int) -> object | None:
    body = json.dumps([{"CMD": 1, "SN": 1, "ID": data_id}]).encode()
    request = urllib.request.Request(f"http://{host}/passthrough/cmd", data=body)
    with urllib.request.urlopen(request, timeout=5) as response:
        record = json.loads(json.loads(response.read())["payload"])[0]
    if record.get("STATUS") != 2:
        return None
    return next(value for key, value in record.items() if key.startswith("V"))


def discover(host: str) -> list[int]:
    ids = [i for block in BLOCKS for i in block if read(host, i) is not None]
    print(f"{len(ids)} ids présents")
    return ids


def snapshot(host: str, ids: list[int]) -> dict[int, object]:
    return {i: read(host, i) for i in ids}


def main() -> None:
    host = sys.argv[1] if len(sys.argv) > 1 else "192.168.1.22"
    log_path = f"mapping-{datetime.now():%Y%m%d-%H%M%S}.jsonl"
    ids = discover(host)
    previous = snapshot(host, ids)
    with open(log_path, "a") as log:
        log.write(json.dumps({"label": "initial", "values": previous}) + "\n")
        while True:
            try:
                label = input("\nChangement effectué (vide pour quitter) : ").strip()
            except EOFError:
                break
            if not label:
                break
            time.sleep(2)
            current = snapshot(host, ids)
            changed = {
                i: (previous[i], v) for i, v in current.items() if v != previous[i]
            }
            for i, (old, new) in changed.items():
                print(f"  {i}: {old} -> {new}")
            if not changed:
                print("  aucun changement")
            log.write(json.dumps({"label": label, "changed": changed}) + "\n")
            log.flush()
            previous = current
    print(f"Journal : {log_path}")


if __name__ == "__main__":
    main()
