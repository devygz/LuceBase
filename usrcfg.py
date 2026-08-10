import json
import os
import syspr

_settings = {}
_changed = False
_FILENAME = "usrcfg.json"
dname = "usrcfg"
loaded = False

def load():
    global _settings, _changed, loaded
    try:
        with open(_FILENAME, "r") as f:
            _settings = json.load(f)
    except:
        syspr.log_print(dname, 3, "Couldn't load usrcfg.json. Starting empty.")
        _settings = {}
    _changed = False
    loaded = True

def get(key, default=None):
    return _settings.get(key, default)

def set(key, value):
    global _changed
    if _settings.get(key) != value:
        _settings[key] = value
        _changed = True

def store():
    global _changed
    if not _changed:
        print("No changes made.")
        return
    try:
        with open(_FILENAME, "w") as f:
            json.dump(_settings, f)
        _changed = False
        syspr.log_print(dname, 0, f"New usrcfg stored successfully.")
    except OSError as e:
        syspr.log_print(dname, 1, f"Error while store: {e}")
        pass

def reset():
    global _settings, _changed
    _settings = {}
    _changed = False
    try:
        os.remove(_FILENAME)
    except:
        pass