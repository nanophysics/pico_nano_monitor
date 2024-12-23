# Folder: fridge_monitoring

See:
* fridge_monitoring/README.md
* fridge_monitoring/secrets_file.py
* Folder to be observe: BlueforsFridge, log_folder=rf"C:\Users\{username}\Bluefors logs"

## Strategy

Install venv
Refactor:
  * Mock grafana
  * Loop to read all files may be read
    * Test parsing
    * Test grafana formatting


## Installation

uv venv --python 3.13.1 --prompt=fridge_monitoring2025 ./venv

source ./venv/bin/activate
uv pip install -r requirements.txt
