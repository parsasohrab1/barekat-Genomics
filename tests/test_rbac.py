"""RBAC permission matrix tests."""

import pytest

from barekat_genomics.core.rbac import Permission, Role, ROLE_PERMISSIONS, has_permission, is_privileged_role


class TestRolePermissions:
    @pytest.mark.parametrize(
      "role,permission,expected",
      [
          ("clinician", Permission.REPORTS_READ_OWN, True),
          ("clinician", Permission.REPORTS_APPROVE, False),
          ("clinician", Permission.SAMPLES_WRITE, False),
          ("geneticist", Permission.REPORTS_APPROVE, True),
          ("geneticist", Permission.VARIANTS_INTERPRET, True),
          ("geneticist", Permission.PIPELINE_RUN, False),
          ("lab_tech", Permission.SAMPLES_WRITE, True),
          ("lab_tech", Permission.PIPELINE_RUN, True),
          ("lab_tech", Permission.REPORTS_READ, False),
          ("admin", Permission.AUDIT_READ, True),
          ("admin", Permission.ADMIN_SETTINGS, True),
      ],
    )
    def test_has_permission(self, role, permission, expected):
        assert has_permission(role, permission) is expected

    def test_all_roles_defined(self):
        for role in Role:
            assert role in ROLE_PERMISSIONS

    def test_privileged_roles(self):
        assert is_privileged_role("admin") is True
        assert is_privileged_role("geneticist") is True
        assert is_privileged_role("lab_tech") is True
        assert is_privileged_role("clinician") is False
