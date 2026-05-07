from __future__ import annotations

import argparse
import os

import uvicorn

from app.main import app as readqraft_app


def main() -> None:
    parser = argparse.ArgumentParser(description="ReadQraft local backend")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=int(os.environ.get("READQRAFT_PORT", "8765")))
    args = parser.parse_args()
    if args.host != "127.0.0.1":
        raise SystemExit("ReadQraft backend must bind to 127.0.0.1.")
    uvicorn.run(readqraft_app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
