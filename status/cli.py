import argparse
import asyncio
import json
import os
import aiohttp
import time
import re

from .core import get_config, check_monitor, MonitorStatus, is_up, filter_monitors
from .web import create_web_app, run_web_server





def format_results_for_console(results: list[MonitorStatus]) -> list[str]:
    if not results:
        return []

    def strip_ansi(text):
        import re
        return re.sub(r'\x1b\[[0-9;]*m', '', text)

    results.sort(key=lambda r: r.monitor_type)

    if len(results) == 1:
        result = results[0]
        if is_up(result):
            name_str = f"\033[1m{result.name}\033[0m ({result.host_or_url})"
            status_label = "[✅ Up] "
        else:
            name_str = f"\033[31m{result.name}\033[0m ({result.host_or_url})"
            status_label = "[🔴 Down]"
        
        status_message = f"- {result.message}" if result.message else ""
        return [f"{name_str} {status_label} {result.status} {status_message}"]


    try:
        terminal_width = os.get_terminal_size().columns - 2 # Add padding
    except OSError:
        terminal_width = 78  # Default width if not a TTY

    output_lines = []
    from itertools import groupby
    slate_blue = "\033[38;5;68m"
    reset_color = "\033[0m"

    for monitor_type, group in groupby(results, key=lambda r: r.monitor_type):
        group_results = list(group)
        
        max_label_len = 0
        max_status_len = 0
        max_message_len = 0
        if group_results:
            max_label_len = max(len("[✅ Up] "), len("[🔴 Down]"))
            max_status_len = max(len(str(r.status)) for r in group_results)
            max_message_len = max(len(f"- {r.message}") for r in group_results)

        output_lines.append(f"{slate_blue}┌{'─' * (terminal_width - 1)}┐{reset_color}")

        for result in group_results:
            if is_up(result):
                name_str = f"\033[1m{result.name}\033[0m ({result.host_or_url})"
                status_label = "[✅ Up] "
            else:
                name_str = f"\033[31m{result.name}\033[0m ({result.host_or_url})"
                status_label = "[🔴 Down]"

            padded_label = f"{status_label}{' ' * (max_label_len - len(status_label))}"
            padded_status = f"{result.status}{' ' * (max_status_len - len(str(result.status)))}"
            status_message = f"- {result.message}" if result.message else ""
            padded_message = f"{status_message}{' ' * (max_message_len - len(status_message))}"

            full_status_str = f"{padded_label} {padded_status} {padded_message}"

            padding_len = terminal_width - len(strip_ansi(name_str)) - len(full_status_str) - 4
            if padding_len < 0:
                padding_len = 0
            padding = " " * padding_len

            line = f"{slate_blue}│{reset_color} {name_str}{padding}{full_status_str} {slate_blue}│{reset_color}"
            
            output_lines.append(line)

        output_lines.append(f"{slate_blue}└{'─' * (terminal_width - 1)}┘{reset_color}")
    
    return output_lines

def print_results(results: list[MonitorStatus]):
    for line in format_results_for_console(results):
        print(line)


async def main():
    parser = argparse.ArgumentParser(description="Check the status of URLs.", add_help=False)
    parser.add_argument("-h", "--help", action="help", default=argparse.SUPPRESS, help="Show this message and exit.")
    
    monitor_group = parser.add_mutually_exclusive_group()
    monitor_group.add_argument("monitor_name", nargs="?", default=None, help="Monitor a specific service by name.")
    monitor_group.add_argument("-m", "--monitor", action='append', help="Filter by monitor type, or by type and name.")

    status_group = parser.add_mutually_exclusive_group()
    status_group.add_argument("-d", "--down", action="store_true", help="Only show monitors that are down.")
    status_group.add_argument("-u", "--up", action="store_true", help="Only show monitors that are up.")

    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("-c", "--console", action="store_true", help="Run in console mode.")
    mode_group.add_argument("-f", "--follow", action="store_true", help="Run in follow mode.")
    mode_group.add_argument("-w", "--web", action="store_true", help="Run as a web server with API.")

    parser.add_argument("-i", "--interval", type=int, help="Refresh interval in seconds for watch mode.")
    parser.add_argument("-o", "--output", default="text", choices=["text", "json"], help="Specify the output format (e.g., text, json).")
    parser.add_argument("--config", default="config.yaml", help="Path to the configuration file.")
    args = parser.parse_args()

    config_path = args.config

    config = get_config(config_path)
    all_monitors = config.get("monitors", [])
    ignored_monitors = config.get("ignore", [])
    all_monitors = [m for m in all_monitors if m['name'] not in ignored_monitors]
    
    monitors_to_check = filter_monitors(all_monitors, name=args.monitor_name, types=args.monitor)

    async def run_checks():
        async with aiohttp.ClientSession() as session:
            tasks = [check_monitor(session, monitor) for monitor in monitors_to_check]
            return await asyncio.gather(*tasks)

    if args.follow:
        interval = args.interval or config.get("follow", {}).get("interval", 5)
        while True:
            results = await run_checks()
            if args.down:
                results = [r for r in results if not is_up(r)]
            elif args.up:
                results = [r for r in results if is_up(r)]

            if args.output == "json":
                print(json.dumps([r.model_dump() for r in results], indent=4))
            else:
                print_results(results)
            
            await asyncio.sleep(interval)
            print("\033[H\033[J", end="") # Clear screen

    elif args.console or not (args.web or args.follow):
        results = await run_checks()

        if args.down:
            results = [r for r in results if not is_up(r)]
        elif args.up:
            results = [r for r in results if is_up(r)]

        if args.output == "json":
            results.sort(key=lambda r: r.monitor_type)
            print(json.dumps([r.model_dump() for r in results], indent=4))
        else:
            print_results(results)
    
    if args.web:
        app = create_web_app(monitors_to_check, args)
        await run_web_server(app)
