from django.test import TestCase
from ninja.errors import HttpError

from core.role.role_model import Role
from core.user.user_model import User

from .models import EnvironmentQueue, TestEnvironment
from .schemas import DeviceTypeIn, EnvironmentAnnouncementIn, EnvironmentIn, EnvironmentListQuery, TestDeviceIn
from .services import (
    create_environment,
    create_device,
    create_device_type,
    delete_device,
    delete_device_type,
    enqueue_environment,
    get_announcement,
    list_environments,
    occupy_environment,
    release_environment,
    save_announcement,
    update_environment,
)


def make_user(username: str, *role_codes: str, is_superuser: bool = False) -> User:
    user = User.objects.create(username=username, password='pass', name=username, is_superuser=is_superuser)
    for code in role_codes:
        role, _ = Role.objects.get_or_create(code=code, defaults={'name': code, 'status': True})
        user.core_roles.add(role)
    return user


def payload(ip: str = '192.168.1.10', password: str = 'secret') -> EnvironmentIn:
    return EnvironmentIn(
        ip_address=ip,
        account='tester',
        password=password,
        domain='cockpit',
        category='test',
        project_name='P1',
        vehicle_model='V1',
        device_ids=[],
        config_description='版本 v1',
        shelf_location='A-01',
        remark='remark',
        sort=0,
    )


class EnvironmentManagementServiceTests(TestCase):
    def setUp(self):
        self.admin = make_user('admin', 'env_admin')
        self.env_user = make_user('env_user', 'environment_user')
        self.user = make_user('user')
        self.user2 = make_user('user2')
        self.user3 = make_user('user3')

    def test_password_is_encrypted_and_only_environment_user_gets_plain_text(self):
        env_data = create_environment(self.admin, payload(password='Pa55w0rd'))
        env = TestEnvironment.objects.get(id=env_data['id'])

        self.assertNotEqual(env.password_encrypted, 'Pa55w0rd')
        normal_page = list_environments(self.user, EnvironmentListQuery(page=1, pageSize=20))
        env_user_page = list_environments(self.env_user, EnvironmentListQuery(page=1, pageSize=20))

        self.assertEqual(normal_page['items'][0]['password'], 'Pa****rd')
        self.assertFalse(normal_page['items'][0]['can_view_secret'])
        self.assertFalse(normal_page['items'][0]['can_use_environment'])
        self.assertEqual(env_user_page['items'][0]['password'], 'Pa55w0rd')
        self.assertTrue(env_user_page['items'][0]['can_view_secret'])
        self.assertTrue(env_user_page['items'][0]['can_use_environment'])

    def test_non_admin_cannot_create_or_update_environment(self):
        with self.assertRaises(HttpError):
            create_environment(self.user, payload())

        env_data = create_environment(self.admin, payload())
        with self.assertRaises(HttpError):
            update_environment(self.user, env_data['id'], payload(ip='192.168.1.11'))

    def test_device_type_device_and_environment_binding(self):
        tree = create_device_type(
            self.admin,
            DeviceTypeIn(parent_id=None, name='电源设备', sort=1, is_active=True),
        )
        parent_id = tree[0]['id']
        tree = create_device_type(
            self.admin,
            DeviceTypeIn(parent_id=parent_id, name='程控电源', sort=1, is_active=True),
        )
        child_id = tree[0]['children'][0]['id']
        device = create_device(
            self.admin,
            TestDeviceIn(
                device_type_id=child_id,
                name='Power-01',
                sort=1,
                is_active=True,
                remark='bench',
            ),
        )

        env_payload = payload()
        env_payload.device_ids = [device['id']]
        env_data = create_environment(self.admin, env_payload)

        self.assertEqual(env_data['device_ids'], [device['id']])
        self.assertEqual(env_data['devices'][0]['display_name'], '电源设备 / 程控电源 / Power-01')
        self.assertEqual(env_data['config_description'], '版本 v1')
        self.assertEqual(env_data['remark'], 'remark')

        with self.assertRaises(HttpError):
            delete_device(self.admin, device['id'])
        with self.assertRaises(HttpError):
            delete_device_type(self.admin, child_id)

    def test_occupy_queue_jump_and_release_do_not_auto_transfer(self):
        env_id = create_environment(self.admin, payload())['id']

        with self.assertRaises(HttpError):
            occupy_environment(self.user, env_id)

        occupied = occupy_environment(self.env_user, env_id)
        self.assertTrue(occupied['success'])
        self.assertEqual(occupied['environment']['current_user_name'], 'env_user')

        with self.assertRaises(HttpError):
            occupy_environment(self.user2, env_id)

        environment_user2 = make_user('environment_user2', 'environment_user')
        environment_user3 = make_user('environment_user3', 'environment_user')
        enqueue_environment(environment_user2, env_id, 'normal')
        enqueue_environment(environment_user3, env_id, 'jump')
        queues = list(EnvironmentQueue.objects.filter(environment_id=env_id, status='waiting').order_by('position'))
        self.assertEqual([row.user.username for row in queues], ['environment_user3', 'environment_user2'])

        released = release_environment(self.env_user, env_id)
        self.assertIn('队首用户 environment_user3', released['message'])
        env = TestEnvironment.objects.get(id=env_id)
        self.assertEqual(env.status, 'idle')
        self.assertIsNone(env.current_user_id)

        with self.assertRaises(HttpError):
            occupy_environment(environment_user2, env_id)
        next_occupied = occupy_environment(environment_user3, env_id)
        self.assertEqual(next_occupied['environment']['current_user_name'], 'environment_user3')

    def test_reject_device_type_value_when_binding_environment(self):
        tree = create_device_type(
            self.admin,
            DeviceTypeIn(parent_id=None, name='空类型', sort=1, is_active=True),
        )
        env_payload = payload()
        env_payload.device_ids = [f"type:{tree[0]['id']}"]

        with self.assertRaises(HttpError):
            create_environment(self.admin, env_payload)

    def test_announcement_can_only_be_saved_by_admin(self):
        initial = get_announcement()
        self.assertFalse(initial['enabled'])

        with self.assertRaises(HttpError):
            save_announcement(
                self.env_user,
                EnvironmentAnnouncementIn(title='提示', content_html='<p>hello</p>', enabled=True),
            )

        saved = save_announcement(
            self.admin,
            EnvironmentAnnouncementIn(title='操作前确认', content_html='<p>请确认</p>', enabled=True),
        )
        self.assertTrue(saved['enabled'])
        self.assertEqual(saved['title'], '操作前确认')
        self.assertEqual(get_announcement()['content_html'], '<p>请确认</p>')
