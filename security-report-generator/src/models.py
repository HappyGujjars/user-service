from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, List, Dict, Any


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"

    @classmethod
    def normalize(cls, val: Optional[str]) -> "Severity":
        if not val:
            return cls.INFO
        v = str(val).strip().upper()
        if v in ("CRITICAL", "BLOCKER"):
            return cls.CRITICAL
        if v in ("HIGH", "MAJOR"):
            return cls.HIGH
        if v in ("MEDIUM", "MODERATE"):
            return cls.MEDIUM
        if v in ("LOW", "MINOR"):
            return cls.LOW
        return cls.INFO

    @property
    def rank(self) -> int:
        order = {
            Severity.CRITICAL: 5,
            Severity.HIGH: 4,
            Severity.MEDIUM: 3,
            Severity.LOW: 2,
            Severity.INFO: 1,
        }
        return order.get(self, 0)


class Category(str, Enum):
    SECRET = "secret"
    DEPENDENCY = "dependency"
    CODE = "code"
    MISCONFIG = "misconfiguration"
    HOTSPOT = "security_hotspot"
    OTHER = "other"


@dataclass
class Finding:
    fingerprint: str
    scanner: str
    category: str
    severity: str
    title: str
    description: str
    file: Optional[str] = None
    line: Optional[int] = None
    rule_id: Optional[str] = None
    cve: Optional[str] = None
    package: Optional[str] = None
    installed_version: Optional[str] = None
    fixed_version: Optional[str] = None
    url: Optional[str] = None
    status: str = "OPEN"
    detected_by: List[str] = field(default_factory=list)
    remediation: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        return data


@dataclass
class ReportMetadata:
    project: str = "critical"
    service: str = "backend"
    branch: str = "main"
    commit: str = "HEAD"
    build_num: str = "1"
    triggered_by: str = "CI"
    build_status: str = "PASSED"
    timestamp: str = ""
    jenkins_url: Optional[str] = None
    sonarqube_url: Optional[str] = None
    defectdojo_url: Optional[str] = None
    git_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AggregatedReport:
    metadata: ReportMetadata
    findings: List[Finding] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)
    scanner_summary: Dict[str, int] = field(default_factory=dict)
    deduplication_summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "summary": self.summary,
            "scanner_summary": self.scanner_summary,
            "deduplication_summary": self.deduplication_summary,
            "findings": [f.to_dict() for f in self.findings],
        }
