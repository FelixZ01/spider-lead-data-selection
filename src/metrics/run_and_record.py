#!/usr/bin/env python3
"""Run a command and save reproducible wall-time/GPU-memory metadata."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path


def gpu_memory_mib() -> int | None:
    if shutil.which("nvidia-smi") is None:
        return None
    result = subprocess.run(
        [
            "nvidia-smi",
            "--query-compute-apps=used_memory",
            "--format=csv,noheader,nounits",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    values = [int(value.strip()) for value in result.stdout.splitlines() if value.strip().isdigit()]
    return sum(values) if values else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        raise ValueError("Provide a command after --")

    stop = threading.Event()
    samples: list[int] = []

    def monitor() -> None:
        while not stop.wait(1):
            value = gpu_memory_mib()
            if value is not None:
                samples.append(value)

    started_at = datetime.now(timezone.utc)
    start = time.monotonic()
    thread = threading.Thread(target=monitor, daemon=True)
    thread.start()
    completed = subprocess.run(command, check=False)
    stop.set()
    thread.join(timeout=2)
    ended_at = datetime.now(timezone.utc)

    record = {
        "name": args.name,
        "command": command,
        "started_at_utc": started_at.isoformat(),
        "ended_at_utc": ended_at.isoformat(),
        "wall_seconds": round(time.monotonic() - start, 3),
        "exit_code": completed.returncode,
        "peak_observed_gpu_memory_mib": max(samples) if samples else None,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(json.dumps(record, indent=2))
    raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
