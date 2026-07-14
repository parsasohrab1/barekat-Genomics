"""Role-Based Access Control — Admin / Analyst / Physician (+ نقش‌های عملیاتی)."""

from enum import Enum


class Role(str, Enum):
    # نام‌های محصولی Phase 3
    ADMIN = "admin"
    ANALYST = "analyst"
    PHYSICIAN = "physician"
    # نام‌های سازگار با نسخهٔ قبلی
    CLINICIAN = "clinician"
    GENETICIST = "geneticist"
    LAB_TECH = "lab_tech"


# نگاشت نام‌های جایگزین به نقشِ canonical برای برخی بررسی‌ها
ROLE_ALIASES: dict[str, str] = {
    "physician": "clinician",
    "analyst": "geneticist",
    "doctor": "clinician",
    "md": "clinician",
}


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
    EHR_IMPORT = "ehr:import"
    AI_ASSIST = "ai:assist"
    DASHBOARD_READ = "dashboard:read"
    AUDIT_READ = "audit:read"
    ADMIN_SETTINGS = "admin:settings"
    USERS_MANAGE = "users:manage"
    TENANT_MANAGE = "tenant:manage"
    BILLING_READ = "billing:read"
    BILLING_MANAGE = "billing:manage"
    COMPLIANCE_READ = "compliance:read"
    COMPLIANCE_MANAGE = "compliance:manage"
    COHORTS_READ = "cohorts:read"
    COHORTS_WRITE = "cohorts:write"
    PARTNER_KEYS_MANAGE = "partner_keys:manage"
    KNOWLEDGE_ASSETS_READ = "knowledge_assets:read"
    KNOWLEDGE_ASSETS_MANAGE = "knowledge_assets:manage"
    COMPUTE_READ = "compute:read"


_PHYSICIAN_PERMS = {
    Permission.PATIENTS_READ_OWN,
    Permission.PATIENTS_WRITE,
    Permission.REPORTS_READ_OWN,
    Permission.VARIANTS_READ_OWN,
    Permission.EHR_EXPORT_OWN,
    Permission.AI_ASSIST,
    Permission.DASHBOARD_READ,
    Permission.COMPLIANCE_READ,
}

_ANALYST_PERMS = {
    Permission.PATIENTS_READ,
    Permission.REPORTS_READ,
    Permission.REPORTS_APPROVE,
    Permission.VARIANTS_READ,
    Permission.VARIANTS_INTERPRET,
    Permission.EHR_EXPORT,
    Permission.EHR_IMPORT,
    Permission.AI_ASSIST,
    Permission.DASHBOARD_READ,
    Permission.COMPLIANCE_READ,
    Permission.COHORTS_READ,
    Permission.COHORTS_WRITE,
    Permission.KNOWLEDGE_ASSETS_READ,
    Permission.COMPUTE_READ,
}

_LAB_PERMS = {
    Permission.PATIENTS_READ,
    Permission.SAMPLES_READ,
    Permission.SAMPLES_WRITE,
    Permission.PIPELINE_READ,
    Permission.PIPELINE_RUN,
    Permission.EHR_IMPORT,
    Permission.DASHBOARD_READ,
    Permission.COMPUTE_READ,
}

ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.PHYSICIAN: set(_PHYSICIAN_PERMS),
    Role.CLINICIAN: set(_PHYSICIAN_PERMS),
    Role.ANALYST: set(_ANALYST_PERMS),
    Role.GENETICIST: set(_ANALYST_PERMS),
    Role.LAB_TECH: set(_LAB_PERMS),
    Role.ADMIN: set(Permission),
}


def normalize_role(role: str) -> str:
    """نقش canonical برای سازگاری کدهای قدیمی (clinician/geneticist)."""
    return ROLE_ALIASES.get(role, role)


def canonical_product_role(role: str) -> str:
    """نام محصولی: admin / analyst / physician / lab_tech."""
    mapping = {
        "clinician": "physician",
        "geneticist": "analyst",
        "physician": "physician",
        "analyst": "analyst",
        "admin": "admin",
        "lab_tech": "lab_tech",
    }
    return mapping.get(role, role)


def has_permission(role: str, permission: Permission) -> bool:
    try:
        role_enum = Role(role)
    except ValueError:
        aliased = ROLE_ALIASES.get(role)
        if aliased is None:
            return False
        try:
            role_enum = Role(aliased)
        except ValueError:
            return False
    perms = ROLE_PERMISSIONS.get(role_enum, set())
    return permission in perms


def is_privileged_role(role: str) -> bool:
    """نقش‌هایی که به همه بیماران سازمان دسترسی دارند."""
    r = normalize_role(role)
    return r in (
        Role.ADMIN.value,
        Role.GENETICIST.value,
        Role.ANALYST.value,
        Role.LAB_TECH.value,
    )


def is_physician_role(role: str) -> bool:
    return normalize_role(role) == Role.CLINICIAN.value


def is_valid_role(role: str) -> bool:
    try:
        Role(role)
        return True
    except ValueError:
        return role in ROLE_ALIASES
