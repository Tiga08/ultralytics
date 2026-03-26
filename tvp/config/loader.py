import json
import os
import yaml
from config.models import TvpConfig, TaskConfig


class ConfigLoader:
    @staticmethod
    def load(config_path: str) -> TvpConfig:
        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        ConfigLoader._apply_env_overrides(data, prefix="TVP")
        return TvpConfig.model_validate(data)

    @staticmethod
    def load_task(task_path: str) -> TaskConfig:
        with open(task_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return TaskConfig.model_validate(data)

    @staticmethod
    def _apply_env_overrides(data: dict, prefix: str) -> None:
        prefix_upper = prefix.upper() + "__"
        for key, val in os.environ.items():
            if not key.upper().startswith(prefix_upper):
                continue
            parts = key[len(prefix_upper):].lower().split("__")
            node = data
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            try:
                node[parts[-1]] = json.loads(val)
            except (json.JSONDecodeError, ValueError):
                node[parts[-1]] = val
