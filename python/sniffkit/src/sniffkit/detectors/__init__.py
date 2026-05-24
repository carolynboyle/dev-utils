"""
sniffkit.detectors
~~~~~~~~~~~~~~~~~~
Detector protocol, registry, and auto-import of all built-in detectors.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class Detector(Protocol):
    type_label: str
    extension: str

    def detect(self, text: str) -> float:
        ...


_REGISTRY: dict[str, Detector] = {}


def register(detector: Detector) -> Detector:
    if detector.type_label in _REGISTRY:
        raise ValueError(
            f"Detector conflict: '{detector.type_label}' is already registered."
        )
    _REGISTRY[detector.type_label] = detector
    return detector


def get_registry() -> dict[str, Detector]:
    return dict(_REGISTRY)


# Auto-import all detectors to trigger @register
from sniffkit.detectors import (  # noqa: F401
    css_detector,
    html_detector,
    json_detector,
    md_detector,
    sql_detector,
)