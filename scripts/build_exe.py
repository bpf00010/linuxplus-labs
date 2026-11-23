import os
import subprocess
import sys
from pathlib import Path


def build():
    root = Path(__file__).resolve().parent.parent
    os.chdir(root)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "lplab.spec",
    ]
    print("Running:", " ".join(cmd))
    res = subprocess.run(cmd)
    if res.returncode != 0:
        sys.exit(res.returncode)
    print("Build finished successfully.")


if __name__ == "__main__":
    build()
