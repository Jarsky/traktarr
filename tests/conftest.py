import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def pytest_configure(config):
    """traktarr's modules load the config singleton on import. Give it the built-in defaults: loading an older file
    makes traktarr add the missing options and exit."""
    tmp = tempfile.mkdtemp(prefix="traktarr-tests-")
    from misc.config import Config
    c = Config(configfile=os.path.join(tmp, "config.json"), cachefile=os.path.join(tmp, "cache.db"),
               logfile=os.path.join(tmp, "traktarr.log"))
    with open(c.config_path, "w") as f:
        json.dump(c.base_config, f)
