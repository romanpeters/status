#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#  "aiohttp",
#  "pyyaml",
#  "fastapi",
#  "uvicorn",
#  "icmplib",
# ]
# ///

import asyncio
from status.cli import main

if __name__ == "__main__":
    asyncio.run(main())