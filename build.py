#!/usr/bin/env python3
"""Build the NVDA add-on from a Windows source checkout in an isolated environment."""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tempfile
import venv

import buildVars


ROOT = pathlib.Path(__file__).resolve().parent
MINIMUM_PYTHON = (3, 10)
PRODUCT_NAME = buildVars.addon_info["summary"]


def _environment_python(environment: pathlib.Path) -> pathlib.Path:
    if os.name == "nt":
        return environment / "Scripts" / "python.exe"
    return environment / "bin" / "python"


def build() -> None:
    if sys.version_info < MINIMUM_PYTHON:
        required = ".".join(str(part) for part in MINIMUM_PYTHON)
        raise RuntimeError(f"Python {required} or newer is required")
    if len(sys.argv) != 1:
        raise RuntimeError("This optional build entry point does not accept arguments")
    requirements = ROOT / "tools" / "requirements-build.txt"
    builder = ROOT / "tools" / "build_nvda_addon.py"
    with tempfile.TemporaryDirectory(prefix="neovim-access-link-build-") as temporary:
        environment = pathlib.Path(temporary) / "environment"
        print("Creating a temporary Python environment...", flush=True)
        venv.EnvBuilder(with_pip=True).create(environment)
        python = _environment_python(environment)
        child_environment = os.environ.copy()
        child_environment["PYTHONNOUSERSITE"] = "1"
        print("Installing the pinned build dependencies...", flush=True)
        subprocess.run(
            (
                str(python),
                "-m",
                "pip",
                "--isolated",
                "install",
                "--disable-pip-version-check",
                "--no-input",
                "--no-cache-dir",
                "-r",
                str(requirements),
            ),
            cwd=ROOT,
            env=child_environment,
            check=True,
        )
        print(f"Building {PRODUCT_NAME}...", flush=True)
        subprocess.run(
            (str(python), str(builder)),
            cwd=ROOT,
            env=child_environment,
            check=True,
        )
    print(f"{PRODUCT_NAME} build complete. The NVDA add-on is in: {ROOT / 'dist'}")


def main() -> int:
    try:
        build()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Build failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
