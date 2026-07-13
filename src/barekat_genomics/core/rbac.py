"""Role-Based Access Control."""

from enum import Enum


class Role(str, Enum):
    CLINICIAN = "clinician"
    GENETICIST = "geneticist"
    LAB_TECH = "lab_tech"
    ADMIN = "admin"


class Permission(str, Enum):
    PATIENTS_READ = "patients:read"
    PATIENTS_READ_OWN = "patients:read_own"
    PATIENTS_WRITE = "patients:write"
    SAMPLES_READ = "samples:read"
    SAMPLES_WRITE = "samples:write"
    PIPELINE_READ = "pipeline:read"
    PIPELINE_RUN = "pipeline:run"
    REPORTS_READ = "reports:read"
    REPORTS_READ_OWN = "reports:read_own"
    REPORTS_APPROVE = "reports:approve"
    VARIANTS_READ = "variants:read"
    VARIANTS_READ_OWN = "variants:read_own"
    VARIANTS_INTERPRET = "variants:interpret"
    EHR_EXPORT = "ehr:export"
    EHR_EXPORT_OWN = "ehr:export_own"
    AI_ASSIST = "ai:assist"
    DASHBOARD_READ = "dashboard:read"
    AUDIT_READ = "audit:read"
    ADMIN_SETTINGS = "admin:settings"


ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.CLINICIAN: {
        Permission.PATIENTS_READ_OWN,
        Permission.PATIENTS_WRITE,
        Permission.REPORTS_READ_OWN,
        Permission.VARIANTS_READ_OWN,
        Permission.EHR_EXPORT_OWN,
        Permission.AI_ASSIST,
        Permission.DASHBOARD_READ,
    },
    Role.GENETICIST: {
        Permission.PATIENTS_READ,
        Permission.REPORTS_READ,
        Permission.REPORTS_APPROVE,
        Permission.VARIANTS_READ,
        Permission.VARIANTS_INTERPRET,
        Permission.EHR_EXPORT,
        Permission.AI_ASSIST,
        Permission.DASHBOARD_READ,
    },
    Role.LAB_TECH: {
        Permission.PATIENTS_READ,
        Permission.SAMPLES_READ,
        Permission.SAMPLES_WRITE,
        Permission.PIPELINE_READ,
        Permission.PIPELINE_RUN,
        Permission.DASHBOARD_READ,
    },
    Role.ADMIN: set(Permission),
}


def has_permission(role: str, permission: Permission) -> bool:
    try:
        role_enum = Role(role)
    except ValueError:
        return False
    perms = ROLE_PERMISSIONS.get(role_enum, set())
    return permission in perms


def is_privileged_role(role: str) -> bool:
    """نقش‌هایی که به همه بیماران دسترسی دارند."""
    return role in (Role.ADMIN.value, Role.GENETICIST.value, Role.LAB_TECH.value)
