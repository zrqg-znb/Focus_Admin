from types import SimpleNamespace
from uuid import uuid4

from django.test import TestCase
from ninja.errors import HttpError

from common.fu_crud import retrieve
from core.pl.pl_model import PlGroup
from core.user.user_api import update_user
from core.user.user_model import User
from core.user.user_schema import UserFilters, UserSchemaIn


class UserPlGroupTests(TestCase):
    def setUp(self):
        self.operator = User.objects.create(username='operator', password='123456')
        self.lead = User.objects.create(username='lead', password='123456', name='Lead')
        self.member_a = User.objects.create(username='member_a', password='123456', name='Member A')
        self.member_b = User.objects.create(username='member_b', password='123456', name='Member B')
        self.group_a = PlGroup.objects.create(name='PL组A', code='pl-a', pl_user=self.lead)
        self.group_b = PlGroup.objects.create(name='PL组B', code='pl-b', pl_user=self.lead)
        self.request = SimpleNamespace(auth=self.operator)

    def _payload(self, user: User, pl_group_ids=None):
        return UserSchemaIn(
            username=user.username,
            name=user.name,
            gender=user.gender or 0,
            user_type=user.user_type,
            user_status=user.user_status,
            pl_group_ids=pl_group_ids or [],
        )

    def test_user_filter_by_multiple_pl_groups_uses_distinct_users(self):
        self.group_a.members.add(self.member_a, self.member_b)
        self.group_b.members.add(self.member_b)

        filters = UserFilters(pl_group_ids=[str(self.group_a.id), str(self.group_b.id)])
        queryset = retrieve(self.request, User, filters).distinct()

        self.assertEqual(queryset.count(), 2)
        self.assertEqual(
            {str(user.id) for user in queryset},
            {str(self.member_a.id), str(self.member_b.id)},
        )

        empty_filters = UserFilters(pl_group_ids=[str(uuid4())])
        self.assertEqual(retrieve(self.request, User, empty_filters).distinct().count(), 0)

    def test_update_user_replaces_pl_group_membership(self):
        updated = update_user(
            self.request,
            str(self.member_a.id),
            self._payload(self.member_a, [str(self.group_a.id)]),
        )
        self.assertTrue(updated.pl_groups.filter(id=self.group_a.id).exists())
        self.assertFalse(updated.pl_groups.filter(id=self.group_b.id).exists())

        updated = update_user(
            self.request,
            str(self.member_a.id),
            self._payload(self.member_a, [str(self.group_b.id)]),
        )
        self.assertFalse(updated.pl_groups.filter(id=self.group_a.id).exists())
        self.assertTrue(updated.pl_groups.filter(id=self.group_b.id).exists())

    def test_update_user_rejects_unknown_pl_group(self):
        with self.assertRaises(HttpError):
            update_user(
                self.request,
                str(self.member_a.id),
                self._payload(self.member_a, [str(uuid4())]),
            )

    def test_update_user_keeps_lead_user_in_owned_pl_group(self):
        self.group_a.members.add(self.lead)

        update_user(
            self.request,
            str(self.lead.id),
            self._payload(self.lead, []),
        )

        self.assertTrue(self.group_a.members.filter(id=self.lead.id).exists())
