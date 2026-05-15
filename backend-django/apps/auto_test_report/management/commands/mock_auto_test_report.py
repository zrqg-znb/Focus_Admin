from datetime import date, datetime, timedelta
import random

from django.core.management.base import BaseCommand

from core.user.user_model import User
from apps.auto_test_report.auto_test_report_model import (
    DOMAIN_COCKPIT,
    DOMAIN_VEHICLE,
    DailyExecutionResult,
    McuPlatform,
    TestCase,
    VehicleModel,
    RESULT_FAILED,
    RESULT_SUCCESS,
    RESULT_SKIP,
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
            (DOMAIN_COCKPIT, 'MCU 2.0', 'mcu20'),
            (DOMAIN_COCKPIT, 'MCU 2.2', 'mcu22'),
            (DOMAIN_VEHICLE, 'VIU 2.0', 'viu20'),
            (DOMAIN_VEHICLE, 'VIU 2.2', 'viu22'),
        ]
        viu_sets = [
            ['viu0', 'viu1', 'viu2'],
            ['viu0', 'viu1', 'viu2', 'viu3'],
            ['viu0', 'viu1', 'viu2', 'viu3', 'viu4'],
        ]
        results = [RESULT_SUCCESS, RESULT_FAILED, RESULT_TIMEOUT, RESULT_SKIP]
        created_vehicle_count = 0
        created_case_count = 0

        for index, (domain, name, code) in enumerate(platforms, start=1):
            platform, created_platform = McuPlatform.objects.get_or_create(
                version_code=code,
                defaults={
                    'name': name,
                    'domain': domain,
                    'sort': 100 - index,
                    'is_active': True,
                    'remark': 'mock 平台数据',
                    'sys_creator': operator,
                    'sys_modifier': operator,
                },
            )
            if not created_platform and platform.domain != domain:
                platform.domain = domain
                platform.save(update_fields=['domain', 'sys_update_datetime'])

            for vehicle_index in range(1, 3):
                vehicle_code = f'{code}-veh-{vehicle_index}'
                viu_codes = (
                    viu_sets[(index + vehicle_index - 2) % len(viu_sets)]
                    if domain == DOMAIN_VEHICLE
                    else []
                )
                vehicle, created_vehicle = VehicleModel.objects.get_or_create(
                    vehicle_code=vehicle_code,
                    defaults={
                        'platform': platform,
                        'name': f'{name} 车型{vehicle_index}',
                        'cdc_platform': f'CDC-{vehicle_index}',
                        'execution_machine': f'10.10.{index}.{vehicle_index}',
                        'viu_codes': viu_codes,
                        'is_active': True,
                        'remark': 'mock 车型数据',
                        'sys_creator': operator,
                        'sys_modifier': operator,
                    },
                )
                if not created_vehicle:
                    vehicle.platform = platform
                    vehicle.viu_codes = viu_codes
                    vehicle.save(update_fields=['platform', 'viu_codes', 'sys_update_datetime'])
                created_vehicle_count += int(created_vehicle)

                target_dates = [
                    date.today() - timedelta(days=day_offset)
                    for day_offset in range(days)
                ]
                DailyExecutionResult.objects.filter(
                    vehicle=vehicle,
                    execute_date__in=target_dates,
                ).delete()

                cases = []
                for case_index in range(1, 11):
                    case_no = f'CASE-{vehicle_index:02d}-{case_index:03d}'
                    case_viu_code = viu_codes[(case_index - 1) % len(viu_codes)] if viu_codes else ''
                    case, created_case = TestCase.objects.get_or_create(
                        vehicle=vehicle,
                        viu_code=case_viu_code,
                        case_no=case_no,
                        defaults={
                            'case_name': f'自动化用例 {vehicle_index}-{case_index}',
                            'is_active': True,
                            'sort': 100 - case_index,
                            'sys_creator': operator,
                            'sys_modifier': operator,
                        },
                    )
                    created_case_count += int(created_case)
                    cases.append(case)

                for day_offset in range(days):
                    execute_date = date.today() - timedelta(days=day_offset)
                    for case in cases:
                        start_at = datetime.combine(execute_date, datetime.min.time()) + timedelta(
                            hours=random.randint(0, 23),
                            minutes=random.randint(0, 59),
                            seconds=random.randint(0, 59),
                        )
                        status = random.choices(results, weights=[0.72, 0.16, 0.07, 0.05], k=1)[0]
                        DailyExecutionResult.objects.create(
                            vehicle=vehicle,
                            execute_date=execute_date,
                            test_case=case,
                            start_time=start_at,
                            duration_seconds=0 if status == RESULT_SKIP else random.randint(10, 1800),
                            result=status,
                            log_url=(
                                None
                                if status == RESULT_SKIP
                                else f'https://mock.example.com/logs/{vehicle.vehicle_code}/{case.case_no}/{execute_date.isoformat()}'
                            ),
                            sys_creator=operator,
                            sys_modifier=operator,
                        )
                    recalculate_daily_batch(vehicle.id, execute_date, datetime.now())

        self.stdout.write(self.style.SUCCESS(
            f'mock 数据生成完成：新增车型 {created_vehicle_count}，新增用例 {created_case_count}，覆盖 {days} 天结果。'
        ))
