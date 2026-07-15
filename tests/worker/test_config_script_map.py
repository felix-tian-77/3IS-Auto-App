import json
import os
import importlib


def _reload_config(monkeypatch, env_value=None):
    """Reload worker.config with a controlled SCRIPT_MAP env value."""
    if env_value is None:
        monkeypatch.delenv("SCRIPT_MAP", raising=False)
    else:
        monkeypatch.setenv("SCRIPT_MAP", env_value)
    import worker.config as cfg
    importlib.reload(cfg)
    return cfg


def test_script_map_default_is_empty_dict(monkeypatch):
    cfg = _reload_config(monkeypatch, env_value=None)
    assert cfg.config.SCRIPT_MAP == {}


def test_script_map_parses_valid_json(monkeypatch):
    raw = json.dumps({"NEW_VEHICLE": "new/new_01.air", "OLD_VEHICLE": "renew/renew_01.air"})
    cfg = _reload_config(monkeypatch, env_value=raw)
    assert cfg.config.SCRIPT_MAP == {
        "NEW_VEHICLE": "new/new_01.air",
        "OLD_VEHICLE": "renew/renew_01.air",
    }


def test_script_map_invalid_json_falls_back_to_empty_dict(monkeypatch):
    cfg = _reload_config(monkeypatch, env_value="this is not json {")
    assert cfg.config.SCRIPT_MAP == {}


def test_script_map_non_object_json_falls_back_to_empty_dict(monkeypatch):
    # JSON list at top level is valid JSON but not a dict.
    cfg = _reload_config(monkeypatch, env_value='["not", "a", "dict"]')
    assert cfg.config.SCRIPT_MAP == {}
