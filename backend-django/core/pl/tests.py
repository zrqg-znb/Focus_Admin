from types import SimpleNamespace

from django.test import TestCase
from ninja.errors import HttpError

from core.pl.pl_model import PlGroup
from core.pl.pl_schemas import PlGroupIn, PlGroupPatch
from core.pl.pl_services import create_pl_group, remove_pl_group_users, update_pl_group
from core.user.user_model import User


class PlGroupServiceTests(TestCase):
    def setUp(self):
        self.operator = User.objects.create(username='operator', password='123456')
        self.lead_one = User.objects.create(username='lead_one', password='123456', name='Lead One')
        self.lead_two = User.objects.create(username='lead_two', password='123456', name='Lead Two')
        self.member = User.objects.create(username='member_one', password='123456', name='Member One')
        self.request = SimpleNamespace(auth=self.operator)

    def test_create_group_auto_adds_pl_member(self):
        group = create_pl_group(
            self.request,
            PlGroupIn(name='PL组A', code='pl-a', pl_user_id=str(self.lead_one.id)),
        )

        self.assertEqual(str(group.pl_user_id), str(self.lead_one.id))
        self.assertEqual(group.members.count(), 1)
        self.assertTrue(group.members.filter(id=self.lead_one.id).exists())

    def test_update_group_keeps_old_pl_and_adds_new_pl(self):
        group = create_pl_group(
            self.request,
            PlGroupIn(name='PL组B', code='pl-b', pl_user_id=str(self.lead_one.id)),
        )

        updated_group = update_pl_group(
            self.request,
            group.id,
            PlGroupPatch(pl_user_id=str(self.lead_two.id)),
            partial=True,
        )

        self.assertEqual(str(updated_group.pl_user_id), str(self.lead_two.id))
        self.assertTrue(updated_group.members.filter(id=self.lead_one.id).exists())
        self.assertTrue(updated_group.members.filter(id=self.lead_two.id).exists())

    def test_remove_current_pl_is_forbidden(self):
        group = create_pl_group(
            self.request,
            PlGroupIn(name='PL组C', code='pl-c', pl_user_id=str(self.lead_one.id)),
        )
        group.members.add(self.member)

        with self.assertRaises(HttpError):
            remove_pl_group_users(group.id, [str(self.lead_one.id)])

        removed_count = remove_pl_group_users(group.id, [str(self.member.id)])
        self.assertEqual(removed_count, 1)
        self.assertFalse(group.members.filter(id=self.member.id).exists())
        self.assertTrue(PlGroup.objects.filter(id=group.id).exists())
