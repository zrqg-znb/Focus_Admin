from django.core.management.base import BaseCommand
from apps.project_manager.iteration.iteration_sync import sync_all_projects_iterations

class Command(BaseCommand):
    help = '同步所有开启迭代统计项目的迭代数据'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting iteration synchronization...'))
        try:
            sync_all_projects_iterations()
            self.stdout.write(self.style.SUCCESS('Successfully synced iterations'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error syncing iterations: {e}'))
