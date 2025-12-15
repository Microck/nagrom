#!/usr/bin/env python3
import subprocess
import sys
import os

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)) or ".")
    sys.exit(subprocess.call([sys.executable, "-m", "src"]))

if __name__ == "__main__":
    main()
