#!/usr/bin/env python3
"""
Server launcher for OmniBurn.
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from server.app import run_server

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8787))
    run_server(port=port)
