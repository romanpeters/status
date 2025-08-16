A CLI tool dashboard for monitoring the status of various services.

# Features
- Monitor the status of multiple services.
- Pluggable architecture for adding new services.
- Multiple modes

# Modes
- Print to console
- Terminal UI
- Web UI + API

# Monitoring Services
- url
- ping
- command

# Usage
uv run status.py [OPTIONS] [MONITOR]
# Options
- `-h`, `--help`: Show this message and exit.
- `-c`, `--console`: Run in console mode.
- `-f`, `--follow`: Live update console mode.
- `-w`, `--web`: Run as a web server with API.
- `-o`, `--output`: Specify the output format (e.g., text, json).
- `--config`: Path to the configuration file.
# Monitor
- `service_name`: Monitor a specific service by name.

# Configuration
The configuration is done via a YAML file (e.g., `config.yaml`). The file should contain a list of monitors, where each monitor has a `name` and a `url`.

Example:
```yaml
monitors:
  - name: Google
    url: https://www.google.com
  - name: GitHub
    url: https://www.github.com
```

# Tests
To run the tests, first install the dependencies:
```
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

Then run the tests using:
```
python -m unittest tests/test_status.py
```
