from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FFI = ROOT / "glc" / "backend" / "ffi"
CPP = FFI / "cpp"
BUILD = CPP / "build"
LIB = BUILD / "liblambda_script_ffi.so"

sys.path.insert(0, str(FFI / "python"))

from lambda_script_ffi import add_int, load_runtime, runtime_name


def build_runtime() -> None:
    BUILD.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "g++",
            "-std=c++17",
            "-fPIC",
            "-shared",
            str(CPP / "src" / "lambda_script_ffi.cpp"),
            "-I",
            str(CPP / "include"),
            "-o",
            str(LIB),
        ],
        check=True,
    )


def main() -> None:
    build_runtime()
    runtime = load_runtime(LIB)
    assert runtime_name(runtime) == "lambda-script-cpp-ffi"
    assert add_int(runtime, 20, 22) == 42
    print("ffi backend ok")


if __name__ == "__main__":
    main()
