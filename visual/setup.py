#!/usr/bin/env python3
"""
Simple setup script for Detectron2 + Detic.
"""
import os
import sys
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent


def run(cmd):
    subprocess.check_call(cmd)


def setup_detectron2():
    run([sys.executable, "-m", "pip", "install", "--no-build-isolation", "git+https://github.com/facebookresearch/detectron2.git"])


def setup_detic():
    repo = HERE / "Detic"
    run(["git", "submodule", "update", "--init", "--recursive"])
    run([sys.executable, "-m", "pip", "install", "-r", str(repo / 'requirements.txt')])

def setup_requirements():
    run([sys.executable, "-m", "pip", "install", "-r", 'requirements.txt'])

def main():
    setup_requirements()
    setup_detectron2()
    setup_detic()
    print("Setup completed successfully.")


if __name__ == "__main__":
    main()
