"""ثبت کانکتورهای EHR."""

from __future__ import annotations

from barekat_genomics.ehr.connectors.base import EHRConnector
from barekat_genomics.ehr.connectors.sepas import SepasConnector
from barekat_genomics.ehr.connectors.tajhiz import TajhizConnector

_CONNECTORS: dict[str, EHRConnector] = {
    "tajhiz": TajhizConnector(),
    "sepas": SepasConnector(),
}


def get_connector(name: str) -> EHRConnector | None:
    return _CONNECTORS.get(name.lower())


def list_connectors() -> list[dict]:
    return [c.info() for c in _CONNECTORS.values()]
