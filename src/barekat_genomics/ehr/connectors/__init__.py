"""کانکتورهای EHR بیمارستانی ایران."""

from barekat_genomics.ehr.connectors.base import EHRConnector
from barekat_genomics.ehr.connectors.registry import get_connector, list_connectors

__all__ = ["EHRConnector", "get_connector", "list_connectors"]
