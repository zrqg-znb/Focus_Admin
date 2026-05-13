from __future__ import annotations

from io import StringIO

from django.core.cache import cache
from django.core.management import call_command
from django.test import RequestFactory, TestCase

from apps.deepaudit.management.commands.init_deepaudit import PERMISSION_SEEDS
from core.auth.auth_api import get_permission_codes
from core.menu.menu_model import Menu
from core.permission.permission_model import Permission
from core.role.role_model import Role
from core.user.user_model import User


class DeepAuditInitPermissionSeedTestCase(TestCase):
    def setUp(self) -> None:
        cache.clear()
        self.factory = RequestFactory()
        self.operator = User.objects.create(
            username='deepaudit-operator',
            password='secret',
            name='DeepAudit Operator',
            is_superuser=True,
            is_active=True,
        )
        self.default_role = Role.objects.create(
            name='默认',
            code='default',
            role_type=0,
            status=True,
        )
        self.superadmin_role = Role.objects.create(
            name='超级管理员',
            code='superadmin',
            role_type=0,
            status=True,
        )
        self.default_user = User.objects.create(
            username='deepaudit-default-user',
            password='secret',
            name='DeepAudit Default User',
            is_active=True,
        )
        self.default_user.core_roles.add(self.default_role)

    def _run_init(self) -> None:
        call_command('init_deepaudit', stdout=StringIO())

    def _get_scenario_menu(self) -> Menu:
        return Menu.objects.get(authCode='deepaudit:scenarios')

    def test_init_deepaudit_binds_scenarios_to_default_and_superadmin_roles(self) -> None:
        self._run_init()

        scenario_menu = self._get_scenario_menu()
        self.assertSetEqual(
            set(scenario_menu.core_roles.values_list('code', flat=True)),
            {'default', 'superadmin'},
        )

        expected_permission_codes = {item['code'] for item in PERMISSION_SEEDS['scenarios']}
        permissions = Permission.objects.filter(menu=scenario_menu, code__in=expected_permission_codes)
        self.assertEqual(permissions.count(), len(expected_permission_codes))

        for permission in permissions:
            self.assertSetEqual(
                set(permission.roles.values_list('code', flat=True)),
                {'default', 'superadmin'},
            )

    def test_perm_code_for_default_role_user_includes_scenario_permissions(self) -> None:
        self._run_init()

        request = self.factory.get('/api/core/auth/permCode')
        request.auth = self.default_user

        perm_codes = get_permission_codes(request)

        self.assertIn('deepaudit:scenarios', perm_codes)
        self.assertIn('deepaudit:scenarios:manage', perm_codes)
        self.assertIn('deepaudit:api:scenarios:list', perm_codes)
        self.assertIn('deepaudit:api:scenarios:create', perm_codes)

    def test_init_deepaudit_is_idempotent_for_scenario_role_bindings(self) -> None:
        self._run_init()

        scenario_menu = self._get_scenario_menu()
        first_menu_role_count = scenario_menu.core_roles.count()
        first_permission_role_counts = {
            permission.code: permission.roles.count()
            for permission in Permission.objects.filter(menu=scenario_menu)
        }

        self._run_init()

        scenario_menu.refresh_from_db()
        self.assertEqual(scenario_menu.core_roles.count(), first_menu_role_count)
        self.assertSetEqual(
            set(scenario_menu.core_roles.values_list('code', flat=True)),
            {'default', 'superadmin'},
        )

        for permission in Permission.objects.filter(menu=scenario_menu):
            self.assertEqual(permission.roles.count(), first_permission_role_counts[permission.code])
            self.assertSetEqual(
                set(permission.roles.values_list('code', flat=True)),
                {'default', 'superadmin'},
            )
