"""رابط پایه کانکتور EHR."""

from __future__ import annotations

from abc import ABC, abstractmethod

from barekat_genomics.ehr.models import ConnectorResult, EHRContext


class EHRConnector(ABC):
    name: str
    display_name: str
    display_name_fa: str
    supported_formats: tuple[str, ...] = ("fhir", "hl7", "json")

    @abstractmethod
    def push(
        self,
        ctx: EHRContext,
        payload: str | dict,
        fmt: str,
    ) -> ConnectorResult:
        """ارسال payload به سیستم مقصد."""

    def info(self) -> dict:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "display_name_fa": self.display_name_fa,
            "supported_formats": list(self.supported_formats),
        }
