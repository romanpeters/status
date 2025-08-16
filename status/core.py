import asyncio
import aiohttp
import yaml
import csv
from icmplib import async_ping
from pydantic import BaseModel
from typing import Union, List


class MonitorStatus(BaseModel):
    name: str
    host_or_url: str
    status: Union[int, str]
    message: str
    monitor_type: str


async def check_url(session, monitor):
    try:
        async with session.get(monitor["url"], timeout=monitor.get("timeout", 10)) as response:
            return MonitorStatus(
                name=monitor["name"],
                host_or_url=monitor.get("host", monitor.get("url")),
                status=response.status,
                message="OK",
                monitor_type="url",
            )
    except asyncio.TimeoutError:
        return MonitorStatus(
            name=monitor["name"],
            host_or_url=monitor.get("host", monitor.get("url")),
            status="Timeout",
            message="",
            monitor_type="url",
        )
    except aiohttp.ClientError as e:
        return MonitorStatus(
            name=monitor["name"],
            host_or_url=monitor.get("host", monitor.get("url")),
            status=f"Error: {e}",
            message="",
            monitor_type="url",
        )


async def check_syncthing(session, monitor):
    url = f"{monitor['url']}/rest/system/status"
    headers = {"X-API-Key": monitor["api_key"]}
    try:
        async with session.get(url, headers=headers, timeout=monitor.get("timeout", 10)) as response:
            if response.status == 200:
                data = await response.json()
                uptime = data.get("uptime", 0)
                return MonitorStatus(
                    name=monitor["name"],
                    host_or_url=monitor.get("host", monitor.get("url")),
                    status="OK",
                    message=f"Uptime: {uptime}s",
                    monitor_type="syncthing",
                )
            else:
                return MonitorStatus(
                    name=monitor["name"],
                    host_or_url=monitor.get("host", monitor.get("url")),
                    status=f"HTTP {response.status}",
                    message=await response.text(),
                    monitor_type="syncthing",
                )
    except asyncio.TimeoutError:
        return MonitorStatus(
            name=monitor["name"],
            host_or_url=monitor.get("host", monitor.get("url")),
            status="Timeout",
            message="",
            monitor_type="syncthing",
        )
    except aiohttp.ClientError as e:
        return MonitorStatus(
            name=monitor["name"],
            host_or_url=monitor.get("host", monitor.get("url")),
            status=f"Error: {e}",
            message="",
            monitor_type="syncthing",
        )


async def check_ping(session, monitor):
    host = monitor["host"]
    try:
        result = await async_ping(host, count=1, timeout=monitor.get("timeout", 2), privileged=False)
        if result.is_alive:
            return MonitorStatus(
                name=monitor["name"],
                host_or_url=host,
                status="OK",
                message=f"{result.avg_rtt}ms",
                monitor_type="ping",
            )
        else:
            return MonitorStatus(
                name=monitor["name"],
                host_or_url=host,
                status="Down",
                message="Host is down",
                monitor_type="ping",
            )
    except Exception as e:
        return MonitorStatus(
            name=monitor["name"],
            host_or_url=host,
            status="Error",
            message=str(e),
            monitor_type="ping",
        )


async def check_command(session, monitor):
    command = monitor["command"]
    host = monitor.get("host")

    if host:
        command = f"ssh {host} '{command}'"

    try:
        proc = await asyncio.create_subprocess_shell(
            command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await proc.communicate()

        if proc.returncode == 0:
            return MonitorStatus(
                name=monitor["name"],
                host_or_url=command,
                status="OK",
                message=f"Exit code: {proc.returncode}",
                monitor_type="command",
            )
        else:
            return MonitorStatus(
                name=monitor["name"],
                host_or_url=command,
                status="Down",
                message=f"Exit code: {proc.returncode}",
                monitor_type="command",
            )
    except Exception as e:
        return MonitorStatus(
            name=monitor["name"],
            host_or_url=command,
            status="Error",
            message=str(e),
            monitor_type="command",
        )

def _load_ping_monitors_from_csv(monitor_config):
    csv_path = monitor_config.get("path")
    if not csv_path:
        return []

    new_monitors = []
    try:
        with open(csv_path, "r") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                host = row.get("host") or row.get("ip")
                if not host:
                    print(
                        f"Warning: Skipping row in {csv_path} because it's missing 'host' or 'ip' column: {row}"
                    )
                    continue
                new_monitor = {
                    "name": row["name"],
                    "host": host,
                    "type": "ping",
                }
                new_monitor.update(
                    {
                        k: v
                        for k, v in monitor_config.items()
                        if k not in ["type", "path"]
                    }
                )
                new_monitors.append(new_monitor)
    except FileNotFoundError:
        print(f"Warning: CSV file not found at {csv_path}")
    except Exception as e:
        print(f"Error reading CSV file {csv_path}: {e}")

    return new_monitors


def _load_url_monitors_from_csv(monitor_config):
    csv_path = monitor_config.get("path")
    default_domain = monitor_config.get("domain")
    if not csv_path:
        return []

    new_monitors = []
    try:
        with open(csv_path, "r") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if "url" in row and row["url"]:
                    url = row["url"]
                else:
                    subdomain = row.get("name") or row.get("subdomain")
                    domain = row.get("domain") or default_domain
                    if not subdomain or not domain:
                        print(
                            f"Warning: Skipping row in {csv_path} because it's missing 'subdomain' or 'domain' column: {row}"
                        )
                        continue

                    ssl_val = str(row.get("ssl", "")).lower()
                    protocol = "https" if ssl_val in ["true", "1", "yes"] else "http"

                    url = f"{protocol}://{subdomain}.{domain}"

                new_monitor = {"name": row["name"], "url": url, "type": "url"}
                new_monitor.update(
                    {
                        k: v
                        for k, v in monitor_config.items()
                        if k not in ["type", "path", "domain"]
                    }
                )
                new_monitors.append(new_monitor)
    except FileNotFoundError:
        print(f"Warning: CSV file not found at {csv_path}")
    except Exception as e:
        print(f"Error reading CSV file {csv_path}: {e}")

    return new_monitors


def get_config(config_path):
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    new_monitors = []
    monitors_to_remove = []

    if "monitors" in config:
        for monitor in config["monitors"]:
            if monitor.get("type") == "ping_csv":
                new_monitors.extend(_load_ping_monitors_from_csv(monitor))
                monitors_to_remove.append(monitor)
            elif monitor.get("type") == "url_csv":
                new_monitors.extend(_load_url_monitors_from_csv(monitor))
                monitors_to_remove.append(monitor)

    if "monitors" in config:
        config["monitors"].extend(new_monitors)
        for monitor in monitors_to_remove:
            config["monitors"].remove(monitor)

    return config

async def check_monitor(session, monitor):
    monitor_type = monitor.get("type", "url")
    if monitor_type == "url":
        return await check_url(session, monitor)
    elif monitor_type == "syncthing":
        return await check_syncthing(session, monitor)
    elif monitor_type == "ping":
        return await check_ping(session, monitor)
    elif monitor_type == "command":
        return await check_command(session, monitor)
    else:
        return MonitorStatus(
            name=monitor["name"],
            host_or_url=monitor.get("host", monitor.get("url")),
            status="Unknown type",
            message=f"Monitor type '{monitor_type}' is not recognized.",
            monitor_type=monitor_type,
        )


class Monitor(BaseModel):
    name: str
    type: str
    url: str = None
    host: str = None
    api_key: str = None
    command: str = None
    timeout: int = 10

def is_up(result: MonitorStatus) -> bool:
    return (isinstance(result.status, int) and 200 <= result.status < 300) or result.status == "OK"

def filter_monitors(monitors: list, name: str = None, types: List[str] = None) -> list:
    if name:
        monitors = [m for m in monitors if m['name'] == name]
    if types:
        monitors = [m for m in monitors if m.get('type', 'url') in types]
    return monitors
