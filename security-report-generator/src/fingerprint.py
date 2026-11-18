import hashlib
import os
import re
from typing import Optional


def normalize_file_path(path: Optional[str]) -> str:
    if not path:
        return ""
    p = str(path).strip().replace("\\", "/")
    # Remove leading ./ or /
    p = re.sub(r"^\.?/+", "", p)
    # Strip common temporary Jenkins workspace prefixes if present
    workspace_pattern = r"^var/jenkins_home/workspace/[^/]+/"
    p = re.sub(workspace_pattern, "", p)
    return p


def compute_sha256(raw_str: str) -> str:
    digest = hashlib.sha256(raw_str.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def generate_secret_fingerprint(rule_id: str, file_path: Optional[str], secret_value: Optional[str] = None) -> str:
    norm_file = normalize_file_path(file_path)
    rule = (rule_id or "unknown-secret-rule").strip().lower()
    
    # Hash the secret value if provided so raw secret is NEVER in fingerprint or plaintext
    secret_hash = ""
    if secret_value:
        secret_hash = hashlib.sha256(str(secret_value).strip().encode("utf-8")).hexdigest()[:16]

    key = f"secret:{rule}:{norm_file}:{secret_hash}"
    return compute_sha256(key)


def generate_dependency_fingerprint(cve: Optional[str], package: Optional[str], installed_version: Optional[str]) -> str:
    c = (cve or "no-cve").strip().upper()
    pkg = (package or "unknown-pkg").strip().lower()
    ver = (installed_version or "unknown-version").strip()

    key = f"dep:{c}:{pkg}:{ver}"
    return compute_sha256(key)


def generate_sonar_fingerprint(rule_id: str, component: Optional[str], line: Optional[int]) -> str:
    rule = (rule_id or "unknown-sonar-rule").strip()
    norm_comp = normalize_file_path(component)
    # If line is present, use line; otherwise 0
    l = int(line) if line is not None else 0

    key = f"sonar:{rule}:{norm_comp}:{l}"
    return compute_sha256(key)


def generate_misconfig_fingerprint(rule_id: str, resource: Optional[str], file_path: Optional[str]) -> str:
    rule = (rule_id or "unknown-misconfig").strip()
    res = (resource or "").strip().lower()
    norm_file = normalize_file_path(file_path)

    key = f"misconfig:{rule}:{res}:{norm_file}"
    return compute_sha256(key)


def generate_generic_fingerprint(rule_id: Optional[str], file_path: Optional[str], line: Optional[int], title: Optional[str]) -> str:
    rule = (rule_id or "").strip()
    norm_file = normalize_file_path(file_path)
    l = int(line) if line is not None else 0
    t = (title or "").strip().lower()

    key = f"generic:{rule}:{norm_file}:{l}:{t}"
    return compute_sha256(key)
