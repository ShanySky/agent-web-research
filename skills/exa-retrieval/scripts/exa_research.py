#!/usr/bin/env python3
import sys
from exa_cli import main

if __name__ == "__main__":
    raise SystemExit(main(["research", *sys.argv[1:]]))
