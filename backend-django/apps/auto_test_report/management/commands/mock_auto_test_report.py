from datetime import date, datetime, timedelta
import random

from django.core.management.base import BaseCommand

from core.user.user_model import User
from apps.auto_test_report.auto_test_report_model import (
    DailyExecutionResult,
    McuPlatform,
    TestCase,
    VehicleModel,
    RESULT_FAILED,
    RESULT_SUCCESS,
    RESULT_TIMEOUT,
)
from apps.auto_test_report.auto_test_report_services import recalculate_daily_batch


class Command(BaseCommand):
    help = '生成自动化测试日报 mock 数据'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=7)

    def handle(self, *args, **options):
        days = max(int(options['days'] or 7), 1)
        operator = User.objects.filter(is_superuser=True).order_by('sys_create_datetime').first()
        random.seed(20260407)

        platforms = [
            ('MCU 2.0', 'mcu20'),
            ('MCU 2.2', 'mcu22'),
            ('MCU 3.0', 'mcu30'),
        ]
        results = [RESULT_SUCCESS, RESULT_FAILED, RESULT_TIMEOUT]
        created_vehicle_count = 0
        created_case_count = 0

        for index, (name, code) in enumerate(platforms, start=1):
            platform, _ = McuPlatform.objects.get_or_create(
                version_code=code,
                defaults={
                    'name': name,
                    'sort': 100 - index,
                    'is_active': True,
                    'remark': 'mock 平台数据',
                    'sys_creator': operator,
                    'sys_modifier': operator,
                },
            )
            for vehicle_index in range(1, 3):
                vehicle_code = f'{code}-veh-{vehicle_index}'
                vehicle, created = VehicleModel.objects.get_or_create(
                    vehicle_code=vehicle_code,
                    defaults={
                        'platform': platform,
                        'name': f'{name} 车型{vehicle_index}',
                        'cdc_platform': f'CDC-{vehicle_index}',
                        'execution_machine': f'10.10.{index}.{vehicle_index}',
                        'is_active': True,
                        'remark': 'mock 车型数据',
                        'sys_creator': operator,
                        'sys_modifier': operator,
                    },
                )
                created_vehicle_count += int(created)

                cases = []
                for case_index in range(1, 11):
                    case, case_created = TestCase.objects.get_or_create(
                        vehicle=vehicle,
                        case_no=f'CASE-{vehicle_index:02d}-{case_index:03d}',
                        defaults={
                            'case_name': f'自动化用例 {vehicle_index}-{case_index}',
                            'is_active': True,
                            'sort': 100 - case_index,
                            'sys_creator': operator,
                            'sys_modifier': operator,
                        },
                    )
                    created_case_count += int(case_created)
                    cases.append(case)

                for day_offset in range(days):
                    execute_date = date.today() - timedelta(days=day_offset)
                    for case in cases:
                        if random.random() < 0.2:
                            continue
                        start_at = datetime.combine(execute_date, datetime.min.time()) + timedelta(
                            hours=random.randint(0, 23),
                            minutes=random.randint(0, 59),
                            seconds=random.randint(0, 59),
                        )
                        duration = random.randint(10, 1800)
                        status = random.choices(results, weights=[0.75, 0.18, 0.07], k=1)[0]
                        DailyExecutionResult.objects.update_or_create(
                            vehicle=vehicle,
                            execute_date=execute_date,
                            test_case=case,
                            defaults={
                                'start_time': start_at,
                                'duration_seconds': duration,
                                'result': status,
                                'log_url': f'https://mock.example.com/logs/{vehicle.vehicle_code}/{case.case_no}/{execute_date.isoformat()}',
                                'sys_creator': operator,
                                'sys_modifier': operator,
                            },
                        )
                    recalculate_daily_batch(vehicle.id, execute_date, datetime.now())

        self.stdout.write(self.style.SUCCESS(
            f'mock 数据生成完成：新增车型 {created_vehicle_count}，新增用例 {created_case_count}，覆盖 {days} 天结果。'
        ))
