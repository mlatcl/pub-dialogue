"""
Configuration module for a Fynesse data science project.

Loads configuration from a layered set of YAML files, merging them in order
so that later files override earlier ones:

  1. fynesse/defaults.yml   — shared defaults, committed to the repo
  2. fynesse/machine.yml    — local/machine overrides, gitignored (do not commit)
  3. _config.yml            — project-level overrides in the repo root

This pattern allows shared configuration (data URLs, public settings) to
be committed while keeping credentials and local paths out of the repository.

USAGE
======
    from fynesse.config import config
    df = pd.read_csv(config['data_url'])

DO NOT hardcode credentials, file paths, or URLs in Python files.
Put shareable values in defaults.yml and local secrets in machine.yml.
"""

import os
from typing import Any, Dict

import yaml

_default_file: str = os.path.join(os.path.dirname(__file__), "defaults.yml")
_machine_file: str = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "machine.yml")
)
_user_file: str = "_config.yml"

config: Dict[str, Any] = {}

if os.path.exists(_default_file):
    with open(_default_file) as _f:
        config.update(yaml.load(_f, Loader=yaml.FullLoader) or {})

if os.path.exists(_machine_file):
    with open(_machine_file) as _f:
        config.update(yaml.load(_f, Loader=yaml.FullLoader) or {})

if os.path.exists(_user_file):
    with open(_user_file) as _f:
        config.update(yaml.load(_f, Loader=yaml.FullLoader) or {})

for _key, _item in config.items():
    if isinstance(_item, str):
        config[_key] = os.path.expandvars(_item)
