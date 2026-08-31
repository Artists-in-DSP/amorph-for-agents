#!/usr/bin/env python3

import argparse
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic Cmajor host-tempo sync scenarios")
    parser.add_argument("--sdk", type=Path, default=os.environ.get("CMAJOR_SDK_PATH"))
    args = parser.parse_args()
    if not args.sdk:
        parser.error("pass --sdk or set CMAJOR_SDK_PATH")

    sdk = args.sdk.resolve()
    library = sdk / ("libCmajPerformer.dylib" if os.uname().sysname == "Darwin" else "libCmajPerformer.so")
    if not (sdk / "include" / "cmajor" / "API" / "cmaj_Engine.h").is_file() or not library.is_file():
        raise SystemExit(f"invalid Cmajor SDK/runtime path: {sdk}")

    source = ROOT / "tests" / "cmajor_transport_sync_runner.cpp"
    fixture = ROOT / "tests" / "fixtures" / "cmajor" / "tempo_synced_delay.cmajor"
    with tempfile.TemporaryDirectory(prefix="amorph-cmajor-transport-") as temp:
        runner = Path(temp) / "cmajor_transport_sync_runner"
        command = [
            os.environ.get("CXX", "clang++"), "-std=c++17", "-DCMAJOR_DLL=1",
            f"-I{sdk / 'include'}", str(source), "-o", str(runner),
        ]
        subprocess.run(command, check=True)
        subprocess.run([str(runner), str(library), str(fixture)], check=True)

    print(f"PASS: deterministic host-tempo sync scenarios with {sdk.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
