import json
import os
from typing import Any, Optional, Dict


def read_json_file(file_path: Optional[str]) -> Optional[Any]:
    if not file_path or not os.path.isfile(file_path):
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return None
            return json.loads(content)
    except Exception as e:
        print(f"Warning: Failed to parse JSON file {file_path}: {e}")
        return None


def _fallback_yaml_parse(file_path: str) -> Dict[str, Any]:
    data: Dict[str, Any] = {
        "project": "critical",
        "services": {"frontend": {}, "backend": {}},
        "escalation": {"email": []}
    }
    current_section = None
    current_service = None
    current_key = None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.rstrip()
                if not line_str or line_str.startswith("#"):
                    continue
                stripped = line_str.strip()
                indent = len(line_str) - len(line_str.lstrip())
                if indent == 0 and ":" in stripped:
                    k, v = stripped.split(":", 1)
                    current_section = k.strip()
                    if v.strip():
                        data[current_section] = v.strip()
                    current_service = None
                    current_key = None
                elif current_section == "services" and indent == 2 and ":" in stripped:
                    k = stripped.split(":", 1)[0].strip()
                    current_service = k
                    if k not in data["services"]:
                        data["services"][k] = {}
                    current_key = None
                elif indent >= 4 and stripped.startswith("- "):
                    val = stripped[2:].strip().strip('"').strip("'")
                    if current_service and current_key:
                        data["services"][current_service].setdefault(current_key, []).append(val)
                    elif current_section == "escalation" and current_key:
                        data["escalation"].setdefault(current_key, []).append(val)
                elif indent >= 4 and ":" in stripped:
                    k, v = stripped.split(":", 1)
                    k, v = k.strip(), v.strip().strip('"').strip("'")
                    current_key = k
                    if current_service:
                        if v:
                            data["services"][current_service][k] = v
                        else:
                            data["services"][current_service][k] = []
                    elif current_section == "escalation":
                        if v:
                            data["escalation"][k] = v
                        else:
                            data["escalation"][k] = []
    except Exception as e:
        print(f"Warning in fallback YAML parse: {e}")
    return data


def read_yaml_file(file_path: Optional[str]) -> Optional[Any]:
    if not file_path or not os.path.isfile(file_path):
        return None
    try:
        import yaml
        with open(file_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except ImportError:
        return _fallback_yaml_parse(file_path)
    except Exception as e:
        print(f"Warning: Failed to parse YAML file {file_path}: {e}")
        return _fallback_yaml_parse(file_path)


def write_json_file(file_path: str, data: Any) -> bool:
    try:
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error: Failed to write JSON file {file_path}: {e}")
        return False


def write_text_file(file_path: str, content: str) -> bool:
    try:
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"Error: Failed to write text file {file_path}: {e}")
        return False
