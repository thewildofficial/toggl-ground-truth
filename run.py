#!/usr/bin/env python3
"""Quick start: python run.py [sync|web|report]"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from toggl_goals.cli import run as run_cli
from web.app import app

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("command", nargs="?", choices=["sync", "web", "report"], default="report")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    if args.command == "sync" or args.command == "report":
        run_cli()
    elif args.command == "web":
        print(f"Starting dashboard on http://{args.host}:{args.port}")
        app.run(host=args.host, port=args.port, debug=False)
