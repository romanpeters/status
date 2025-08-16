from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
import aiohttp
import asyncio
from typing import List

from .core import check_monitor, MonitorStatus, is_up, filter_monitors

def create_web_app(monitors: list, args):
    app = FastAPI()

    @app.get("/api/args")
    async def get_args():
        return {
            "down": args.down,
            "up": args.up,
            "monitor_name": args.monitor_name,
            "monitor": args.monitor,
            "follow": args.follow,
            "interval": args.interval
        }

    @app.get("/api/status", response_model=list[MonitorStatus])
    async def get_status(
        name: str = Query(None, description="Filter by monitor name"),
        type: str = Query(None, description="Filter by monitor type"),
        status: str = Query(None, description="Filter by status (up or down)")
    ):
        types_list = [type] if type else None
        monitors_to_check = filter_monitors(monitors, name=name, types=types_list)

        async with aiohttp.ClientSession() as session:
            tasks = [check_monitor(session, monitor) for monitor in monitors_to_check]
            results = await asyncio.gather(*tasks)

        if status == "up":
            results = [r for r in results if is_up(r)]
        elif status == "down":
            results = [r for r in results if not is_up(r)]
        
        results.sort(key=lambda r: r.monitor_type)
        return results

    app.mount("/static", StaticFiles(directory="static"), name="static")

    @app.get("/")
    async def get_index():
        return FileResponse("index.html")

    return app

async def run_web_server(app: FastAPI):
    config = uvicorn.Config(app, host="0.0.0.0", port=8000)
    server = uvicorn.Server(config)
    await server.serve()