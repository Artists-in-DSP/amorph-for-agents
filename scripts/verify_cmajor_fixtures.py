#!/usr/bin/env python3

import argparse
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile semantic fixtures with the exact Cmajor SDK")
    parser.add_argument("--sdk", type=Path, default=os.environ.get("CMAJOR_SDK_PATH"))
    args = parser.parse_args()
    if not args.sdk:
        parser.error("pass --sdk or set CMAJOR_SDK_PATH")

    sdk = args.sdk.resolve()
    library = sdk / ("libCmajPerformer.dylib" if os.uname().sysname == "Darwin" else "libCmajPerformer.so")
    if not (sdk / "include" / "cmajor" / "API" / "cmaj_Engine.h").is_file() or not library.is_file():
        raise SystemExit(f"invalid Cmajor SDK/runtime path: {sdk}")

    fixtures = sorted((ROOT / "tests" / "fixtures" / "cmajor").glob("*.cmajor"))
    if len(fixtures) != 5:
        raise SystemExit(f"expected 5 semantic fixtures, found {len(fixtures)}")

    with tempfile.TemporaryDirectory(prefix="amorph-cmajor-fixtures-") as temp:
        compiler = Path(temp) / "cmajor_fixture_compiler"
        command = [
            os.environ.get("CXX", "clang++"), "-std=c++17", "-DCMAJOR_DLL=1",
            f"-I{sdk / 'include'}", str(ROOT / "tests" / "cmajor_fixture_compiler.cpp"),
            "-o", str(compiler),
        ]
        subprocess.run(command, check=True)
        subprocess.run([str(compiler), str(library), *(str(path) for path in fixtures)], check=True)

    print(f"PASS: {len(fixtures)} semantic Cmajor fixtures with {sdk.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
