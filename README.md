A CLI/Web dashboard for monitoring the status of various services.
```shell
 $ ./status.py -m url
┌───────────────────────────────────────────────────────────────┐
│ Google (https://google.com)                [✅ Up]   200 - OK │
│ Github (https://github.com)                [✅ Up]   200 - OK │
│ Website (https://offline-domain.com)       [🔴 Up]   404 - OK │
└───────────────────────────────────────────────────────────────┘
```

# Features
- Monitor the status of multiple services.
- Run in the terminal or as a web server.

# Monitoring Services
- url
- ping
- command

# Usage
Requires UV to be installed:
./status.py [OPTIONS] [MONITOR]
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
