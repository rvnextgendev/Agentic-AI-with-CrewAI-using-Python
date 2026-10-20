"""Refresh local settings while preserving explicit environment/Cloud secrets."""

import os
from pathlib import Path
from threading import RLock

from dotenv import dotenv_values

_managed = {}
_protected = set()
_lock = RLock()


def refresh_local_environment(path=None, protected_keys=None):
    path = Path(path) if path else Path(__file__).resolve().parents[1] / ".env"
    with _lock:
        if protected_keys is not None:
            _protected.clear()
            _protected.update(protected_keys)
        values = dotenv_values(path)
        for name, previous in list(_managed.items()):
            if name not in values:
                if name not in _protected and os.environ.get(name) == previous:
                    os.environ.pop(name, None)
                _managed.pop(name, None)
        for name, value in values.items():
            if value is None or name in _protected:
                continue
            if name not in os.environ or (name in _managed and os.environ[name] == _managed[name]):
                os.environ[name] = value
                _managed[name] = value
