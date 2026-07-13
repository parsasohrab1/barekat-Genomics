"""اتصال استاندارد EHR — FHIR R4، HL7 v2، کانکتورهای بیمارستانی."""

from barekat_genomics.ehr.fhir_r4 import build_fhir_bundle
from barekat_genomics.ehr.hl7_v2 import build_oru_message
from barekat_genomics.ehr.models import EHRContext
from barekat_genomics.ehr.service import EHRIntegrationService

__all__ = [
    "EHRContext",
    "EHRIntegrationService",
    "build_fhir_bundle",
    "build_oru_message",
]
