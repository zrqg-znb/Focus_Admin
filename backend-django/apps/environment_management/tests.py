from unittest.mock import patch

from django.test import TestCase
from ninja.errors import HttpError

from core.role.role_model import Role
from core.user.user_model import User

from .models import EnvironmentDeviceBinding, EnvironmentFavorite, EnvironmentQueue, EnvironmentRecord, TestEnvironment
from .schemas import DeviceTypeIn, EnvironmentAnnouncementIn, EnvironmentIn, EnvironmentListQuery, TestDeviceIn
from .services import (
    auto_release_all_occupied_environments,
    create_environment,
    create_device,
    create_device_type,
    delete_device_type,
    cancel_my_queue,
    enqueue_environment,
    get_announcement,
    list_devices,
    list_environments,
    list_filter_options,
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
        bomid='BOM-001',
        project_name='P1',
        vehicle_model='V1',
        devices=[],
        device_ids=[],
        config_description='版本 v1',
        asset_number='ENV-ASSET-001',
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

    def test_password_is_encrypted_and_never_returned_to_environment_list(self):
        env_data = create_environment(self.admin, payload(password='Pa55w0rd'))
        env = TestEnvironment.objects.get(id=env_data['id'])

        self.assertNotEqual(env.password_encrypted, 'Pa55w0rd')
        normal_page = list_environments(self.user, EnvironmentListQuery(page=1, pageSize=20))
        env_user_page = list_environments(self.env_user, EnvironmentListQuery(page=1, pageSize=20))

        self.assertNotIn('password', normal_page['items'][0])
        self.assertEqual(normal_page['items'][0]['account'], 'tester')
        self.assertFalse(normal_page['items'][0]['can_view_secret'])
        self.assertFalse(normal_page['items'][0]['can_use_environment'])
        self.assertNotIn('password', env_user_page['items'][0])
        self.assertEqual(env_user_page['items'][0]['account'], 'tester')
        self.assertFalse(env_user_page['items'][0]['can_view_secret'])
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
        env_payload.devices = [
            {
                'device_id': device['id'],
                'asset_number': 'DEV-ASSET-01',
                'remark': 'bench',
                'sort': 1,
            }
        ]
        env_data = create_environment(self.admin, env_payload)

        self.assertEqual(env_data['bomid'], 'BOM-001')
        self.assertEqual(env_data['asset_number'], 'ENV-ASSET-001')
        self.assertEqual(env_data['devices'][0]['device_id'], device['id'])
        self.assertEqual(env_data['devices'][0]['device_name'], 'Power-01')
        self.assertEqual(env_data['devices'][0]['asset_number'], 'DEV-ASSET-01')
        self.assertEqual(env_data['device_display'], 'Power-01')
        self.assertNotIn('电源设备 / 程控电源', env_data['device_display'])
        self.assertEqual(env_data['config_description'], '版本 v1')
        self.assertEqual(env_data['remark'], 'remark')

        with self.assertRaises(HttpError):
            delete_device_type(self.admin, child_id)

        # 旧 device_ids 入参仍会兼容生成环境设备实例，方便旧前端短期过渡。
        legacy_payload = payload(ip='192.168.1.11')
        legacy_payload.device_ids = [device['id']]
        legacy_env = create_environment(self.admin, legacy_payload)
        self.assertEqual(legacy_env['devices'][0]['device_name'], 'Power-01')
        self.assertEqual(EnvironmentDeviceBinding.objects.filter(environment_id=legacy_env['id']).count(), 1)


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

    def test_idle_environment_with_waiting_queue_allows_later_user_to_queue(self):
        env_id = create_environment(self.admin, payload())['id']
        occupy_environment(self.env_user, env_id)
        queue_head = make_user('queue_head', 'environment_user')
        later_user = make_user('later_user', 'environment_user')
        enqueue_environment(queue_head, env_id, 'normal')
        release_environment(self.env_user, env_id)

        with self.assertRaises(HttpError) as error:
            occupy_environment(later_user, env_id)
        self.assertIn('当前队首为 queue_head', str(error.exception))

        queued = enqueue_environment(later_user, env_id, 'normal')
        self.assertEqual(queued['my_queue_position'], 2)
        occupied = occupy_environment(queue_head, env_id)
        self.assertEqual(occupied['environment']['current_user_name'], 'queue_head')
        self.assertTrue(
            EnvironmentQueue.objects.filter(environment_id=env_id, user=queue_head, status='done').exists()
        )

    def test_reject_invalid_device_when_binding_environment(self):
        env_payload = payload()
        env_payload.devices = [{'device_id': 'not-exists', 'asset_number': '', 'remark': '', 'sort': 0}]

        with self.assertRaises(HttpError):
            create_environment(self.admin, env_payload)

    def test_environment_keyword_search_supports_bomid_and_device_assets(self):
        tree = create_device_type(
            self.admin,
            DeviceTypeIn(parent_id=None, name='外设', sort=1, is_active=True),
        )
        device = create_device(
            self.admin,
            TestDeviceIn(device_type_id=tree[0]['id'], name='采集卡', sort=0, is_active=True, remark=''),
        )
        env_payload = payload()
        env_payload.devices = [
            {
                'device_id': device['id'],
                'asset_number': 'DAQ-ASSET',
                'remark': '高速采集',
                'sort': 0,
            }
        ]
        create_environment(self.admin, env_payload)

        by_bomid = list_environments(self.user, EnvironmentListQuery(keyword='BOM-001', page=1, pageSize=20))
        by_device_asset = list_environments(self.user, EnvironmentListQuery(keyword='DAQ-ASSET', page=1, pageSize=20))
        self.assertEqual(by_bomid['total'], 1)
        self.assertEqual(by_device_asset['total'], 1)

    def test_environment_header_filters_support_dropdown_and_text_conditions(self):
        tree = create_device_type(
            self.admin,
            DeviceTypeIn(parent_id=None, name='外设', sort=1, is_active=True),
        )
        device = create_device(
            self.admin,
            TestDeviceIn(device_type_id=tree[0]['id'], name='采集卡', sort=0, is_active=True, remark=''),
        )
        first_payload = payload(ip='192.168.1.21')
        first_payload.project_name = 'P-Alpha'
        first_payload.vehicle_model = 'Model-X'
        first_payload.devices = [{'device_id': device['id'], 'asset_number': 'DAQ-01', 'remark': '', 'sort': 0}]
        create_environment(self.admin, first_payload)

        second_payload = payload(ip='192.168.1.22')
        second_payload.domain = 'vehicle'
        second_payload.category = 'dev'
        second_payload.project_name = 'P-Beta'
        second_payload.vehicle_model = 'Model-Y'
        second_payload.bomid = 'BOM-002'
        create_environment(self.admin, second_payload)

        # 表头下拉筛选提交逗号字符串，服务层需要按精确多选处理，而不是把逗号串当模糊文本。
        exact_page = list_environments(
            self.user,
            EnvironmentListQuery(
                domains='cockpit',
                categories='test',
                project_name='Alpha',
                vehicle_model='Model-X',
                device_ids=device['id'],
                page=1,
                pageSize=20,
            ),
        )
        fuzzy_page = list_environments(
            self.user,
            EnvironmentListQuery(ip_address='1.22', bomid='BOM-002', page=1, pageSize=20),
        )

        self.assertEqual(exact_page['total'], 1)
        self.assertEqual(exact_page['items'][0]['project_name'], 'P-Alpha')
        self.assertEqual(fuzzy_page['total'], 1)
        self.assertEqual(fuzzy_page['items'][0]['domain'], 'vehicle')

    def test_environment_device_filter_uses_intersection_for_multiple_devices(self):
        tree = create_device_type(
            self.admin,
            DeviceTypeIn(parent_id=None, name='外设', sort=1, is_active=True),
        )
        device_a = create_device(
            self.admin,
            TestDeviceIn(device_type_id=tree[0]['id'], name='采集卡', sort=0, is_active=True, remark=''),
        )
        device_b = create_device(
            self.admin,
            TestDeviceIn(device_type_id=tree[0]['id'], name='程控电源', sort=1, is_active=True, remark=''),
        )
        device_c = create_device(
            self.admin,
            TestDeviceIn(device_type_id=tree[0]['id'], name='示波器', sort=2, is_active=True, remark=''),
        )

        both_payload = payload(ip='192.168.2.10')
        both_payload.devices = [
            {'device_id': device_a['id'], 'asset_number': '', 'remark': '', 'sort': 0},
            {'device_id': device_b['id'], 'asset_number': '', 'remark': '', 'sort': 1},
        ]
        both_env = create_environment(self.admin, both_payload)

        only_a_payload = payload(ip='192.168.2.11')
        only_a_payload.devices = [{'device_id': device_a['id'], 'asset_number': '', 'remark': '', 'sort': 0}]
        create_environment(self.admin, only_a_payload)

        only_c_payload = payload(ip='192.168.2.12')
        only_c_payload.devices = [{'device_id': device_c['id'], 'asset_number': '', 'remark': '', 'sort': 0}]
        create_environment(self.admin, only_c_payload)

        page = list_environments(
            self.user,
            EnvironmentListQuery(device_ids=f"{device_a['id']},{device_b['id']}", page=1, pageSize=20),
        )

        self.assertEqual(page['total'], 1)
        self.assertEqual(page['items'][0]['id'], both_env['id'])

    def test_favorites_are_globally_pinned_before_pagination(self):
        favorite_id = ''
        for index in range(25):
            env_payload = payload(ip=f'10.10.0.{index + 1}')
            env_payload.sort = 25 - index
            env_data = create_environment(self.admin, env_payload)
            if index == 24:
                favorite_id = env_data['id']
        EnvironmentFavorite.objects.create(environment_id=favorite_id, user=self.env_user)

        page = list_environments(self.env_user, EnvironmentListQuery(page=1, pageSize=20))

        self.assertEqual(page['total'], 25)
        self.assertEqual(page['items'][0]['id'], favorite_id)
        self.assertTrue(page['items'][0]['is_favorite'])

    def test_favorite_pin_only_applies_inside_filtered_result_set(self):
        favorite_payload = payload(ip='10.20.0.1')
        favorite_payload.domain = 'vehicle'
        favorite_payload.sort = 0
        favorite_id = create_environment(self.admin, favorite_payload)['id']
        EnvironmentFavorite.objects.create(environment_id=favorite_id, user=self.env_user)

        cockpit_payload = payload(ip='10.20.0.2')
        cockpit_payload.domain = 'cockpit'
        cockpit_payload.sort = 1
        cockpit_id = create_environment(self.admin, cockpit_payload)['id']

        page = list_environments(
            self.env_user,
            EnvironmentListQuery(domains='cockpit', page=1, pageSize=20),
        )

        self.assertEqual(page['total'], 1)
        self.assertEqual(page['items'][0]['id'], cockpit_id)
        self.assertFalse(page['items'][0]['is_favorite'])

    def test_filter_options_and_device_header_filters_do_not_return_sensitive_fields(self):
        tree = create_device_type(
            self.admin,
            DeviceTypeIn(parent_id=None, name='采集设备', sort=1, is_active=True),
        )
        device = create_device(
            self.admin,
            TestDeviceIn(device_type_id=tree[0]['id'], name='DAQ-9000', sort=0, is_active=True, remark='高速采集'),
        )
        env_payload = payload()
        env_payload.devices = [{'device_id': device['id'], 'asset_number': 'DAQ-ASSET-9000', 'remark': '', 'sort': 0}]
        create_environment(self.admin, env_payload)

        options = list_filter_options(self.user)
        filtered_devices = list_devices(name='DAQ', is_active_values='true', remark='高速')

        self.assertEqual(filtered_devices[0]['name'], 'DAQ-9000')
        self.assertIn({'label': 'P1', 'value': 'P1'}, options['projects'])
        self.assertEqual(options['device_options'][0]['label'], '采集设备')
        self.assertEqual(options['device_options'][0]['children'][0]['value'], device['id'])
        self.assertTrue(all('password' not in item for values in options.values() for item in values))
        self.assertTrue(all('rdp' not in item for values in options.values() for item in values))

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

    def test_release_notifies_first_queue_user_available(self):
        env_id = create_environment(self.admin, payload())['id']
        occupy_environment(self.env_user, env_id)
        environment_user2 = make_user('environment_user2', 'environment_user')
        environment_user3 = make_user('environment_user3', 'environment_user')
        enqueue_environment(environment_user2, env_id, 'normal')
        enqueue_environment(environment_user3, env_id, 'normal')

        with patch('apps.environment_management.services.send_environment_queue_notification_by_username') as mock_send:
            with self.captureOnCommitCallbacks(execute=True):
                release_environment(self.env_user, env_id)

        self.assertEqual(mock_send.call_count, 1)
        username, title, content, notify_payload = mock_send.call_args.args
        self.assertEqual(username, 'environment_user2')
        self.assertIn('轮到你', title)
        self.assertIn('请及时手动占用', content)
        self.assertTrue(notify_payload['available'])
        self.assertNotIn('password', notify_payload)
        self.assertNotIn('password_encrypted', notify_payload)
        self.assertNotIn('account', notify_payload)

    def test_cancel_queue_notifies_users_that_moved_forward(self):
        env_id = create_environment(self.admin, payload())['id']
        occupy_environment(self.env_user, env_id)
        environment_user2 = make_user('environment_user2', 'environment_user')
        environment_user3 = make_user('environment_user3', 'environment_user')
        environment_user4 = make_user('environment_user4', 'environment_user')
        enqueue_environment(environment_user2, env_id, 'normal')
        enqueue_environment(environment_user3, env_id, 'normal')
        enqueue_environment(environment_user4, env_id, 'normal')

        with patch('apps.environment_management.services.send_environment_queue_notification_by_username') as mock_send:
            with self.captureOnCommitCallbacks(execute=True):
                cancel_my_queue(environment_user2, env_id)

        self.assertEqual([call.args[0] for call in mock_send.call_args_list], ['environment_user3', 'environment_user4'])
        self.assertEqual([call.args[3]['position'] for call in mock_send.call_args_list], [1, 2])
        self.assertTrue(all(not call.args[3]['available'] for call in mock_send.call_args_list))

    def test_occupy_from_queue_notifies_next_users_that_moved_forward(self):
        env_id = create_environment(self.admin, payload())['id']
        occupy_environment(self.env_user, env_id)
        environment_user2 = make_user('environment_user2', 'environment_user')
        environment_user3 = make_user('environment_user3', 'environment_user')
        enqueue_environment(environment_user2, env_id, 'normal')
        enqueue_environment(environment_user3, env_id, 'normal')
        with self.captureOnCommitCallbacks(execute=True):
            release_environment(self.env_user, env_id)

        with patch('apps.environment_management.services.send_environment_queue_notification_by_username') as mock_send:
            with self.captureOnCommitCallbacks(execute=True):
                occupy_environment(environment_user2, env_id)

        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(mock_send.call_args.args[0], 'environment_user3')
        self.assertIn('前进到第 1 位', mock_send.call_args.args[2])
        self.assertFalse(mock_send.call_args.args[3]['available'])

    def test_jump_queue_does_not_notify_users_moved_backward(self):
        env_id = create_environment(self.admin, payload())['id']
        occupy_environment(self.env_user, env_id)
        environment_user2 = make_user('environment_user2', 'environment_user')
        environment_user3 = make_user('environment_user3', 'environment_user')
        environment_user4 = make_user('environment_user4', 'environment_user')
        enqueue_environment(environment_user2, env_id, 'normal')
        enqueue_environment(environment_user3, env_id, 'normal')

        with patch('apps.environment_management.services.send_environment_queue_notification_by_username') as mock_send:
            with self.captureOnCommitCallbacks(execute=True):
                enqueue_environment(environment_user4, env_id, 'jump')

        mock_send.assert_not_called()

    def test_notification_error_does_not_break_release_flow(self):
        env_id = create_environment(self.admin, payload())['id']
        occupy_environment(self.env_user, env_id)
        environment_user2 = make_user('environment_user2', 'environment_user')
        enqueue_environment(environment_user2, env_id, 'normal')

        with patch(
            'apps.environment_management.services.send_environment_queue_notification_by_username',
            side_effect=RuntimeError('company notification unavailable'),
        ):
            with self.captureOnCommitCallbacks(execute=True):
                released = release_environment(self.env_user, env_id)

        self.assertTrue(released['success'])
        env = TestEnvironment.objects.get(id=env_id)
        self.assertEqual(env.status, 'idle')

    def test_auto_release_all_occupied_environments_records_and_keeps_queue(self):
        first_id = create_environment(self.admin, payload(ip='172.16.0.1'))['id']
        second_id = create_environment(self.admin, payload(ip='172.16.0.2'))['id']
        idle_id = create_environment(self.admin, payload(ip='172.16.0.3'))['id']
        occupy_environment(self.env_user, first_id)
        occupy_environment(self.env_user, second_id)
        waiting_user = make_user('waiting_user', 'environment_user')
        enqueue_environment(waiting_user, first_id, 'normal')

        with patch('apps.environment_management.services.send_environment_queue_notification_by_username') as mock_send:
            with self.captureOnCommitCallbacks(execute=True):
                result = auto_release_all_occupied_environments()

        self.assertEqual(result['released_count'], 2)
        self.assertEqual(set(result['environment_ids']), {first_id, second_id})
        self.assertEqual(TestEnvironment.objects.get(id=first_id).status, 'idle')
        self.assertEqual(TestEnvironment.objects.get(id=second_id).status, 'idle')
        self.assertEqual(TestEnvironment.objects.get(id=idle_id).status, 'idle')
        self.assertTrue(EnvironmentQueue.objects.filter(environment_id=first_id, user=waiting_user, status='waiting').exists())

        records = EnvironmentRecord.objects.filter(action='auto_release').order_by('environment_id')
        self.assertEqual(records.count(), 2)
        self.assertTrue(all(record.operator_id is None for record in records))
        self.assertTrue(all(record.started_at and record.ended_at for record in records))
        self.assertTrue(all(record.duration_seconds >= 0 for record in records))
        self.assertTrue(all('系统自动释放环境' in record.message for record in records))
        mock_send.assert_called_once()
        self.assertEqual(mock_send.call_args.args[0], 'waiting_user')

    def test_auto_release_all_occupied_environments_is_noop_when_none_occupied(self):
        create_environment(self.admin, payload(ip='172.16.1.1'))

        result = auto_release_all_occupied_environments()

        self.assertEqual(result, {'released_count': 0, 'environment_ids': []})
        self.assertFalse(EnvironmentRecord.objects.filter(action='auto_release').exists())
