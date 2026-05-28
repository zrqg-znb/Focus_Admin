from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone

from apps.auto_test_report import auto_test_report_services as services
from apps.auto_test_report.auto_test_report_model import (
    DailyExecutionResult,
    McuPlatform,
    TestCase as AutoTestCase,
    VehicleModel,
    DOMAIN_COCKPIT,
    DOMAIN_VEHICLE,
    RESULT_FAILED,
    RESULT_SUCCESS,
    RESULT_SKIP,
    RESULT_TIMEOUT,
)
from apps.auto_test_report.auto_test_report_schemas import (
    DailyOverviewQuery,
    ImportCasePayload,
    ImportCaseRow,
    ReportDailyResultsIn,
    ReportResultItemIn,
    TestCaseFilter,
)


class AutoTestReportOverviewTests(TestCase):
    def setUp(self) -> None:
        self.execute_date = date(2026, 4, 26)
        self.platform = McuPlatform.objects.create(
            name='Test Platform',
            version_code='test-platform',
            domain=DOMAIN_COCKPIT,
            is_active=True,
        )

    def _create_vehicle(
        self,
        suffix: str,
        *,
        domain: str = DOMAIN_COCKPIT,
        viu_codes: list[str] | None = None,
    ) -> VehicleModel:
        return VehicleModel.objects.create(
            platform=self.platform,
            name=f'Vehicle {suffix}',
            vehicle_code=f'VEH-{suffix}',
            cdc_platform='CDC',
            execution_machine=f'machine-{suffix}',
            viu_codes=viu_codes or [],
            is_active=True,
        )

    def _create_cases(self, vehicle: VehicleModel, count: int) -> list[AutoTestCase]:
        return [
            AutoTestCase.objects.create(
                vehicle=vehicle,
                case_no=f'CASE-{vehicle.vehicle_code}-{index + 1}',
                case_name=f'Case {index + 1}',
                is_active=True,
            )
            for index in range(count)
        ]

    def _report_result(
        self,
        vehicle: VehicleModel,
        test_case: AutoTestCase,
        result: str,
        *,
        minutes_offset: int = 0,
        log_url: str | None = None,
    ) -> DailyExecutionResult:
        return DailyExecutionResult.objects.create(
            vehicle=vehicle,
            test_case=test_case,
            execute_date=self.execute_date,
            start_time=timezone.now() + timedelta(minutes=minutes_offset),
            duration_seconds=60,
            result=result,
            log_url=log_url,
        )

    def _get_row(self, overview, vehicle: VehicleModel):
        return next(item for item in overview.items if item.vehicle_id == str(vehicle.id))

    def _build_overview(self, *, abnormal_only: bool = False):
        return services.get_daily_overview(
            DailyOverviewQuery(
                execute_date=self.execute_date,
                abnormal_only=abnormal_only,
            )
        )

    def test_overview_marks_all_success_uploaded_vehicle_as_normal(self):
        vehicle = self._create_vehicle('success')
        cases = self._create_cases(vehicle, 2)

        for index, case in enumerate(cases):
            self._report_result(vehicle, case, RESULT_SUCCESS, minutes_offset=index)

        overview = self._build_overview()
        row = self._get_row(overview, vehicle)

        self.assertFalse(row.is_abnormal)
        self.assertEqual(row.success_count, 2)
        self.assertEqual(row.skip_count, 0)
        self.assertEqual(overview.summary.abnormal_vehicle_count, 0)

    def test_overview_marks_failed_vehicle_as_abnormal(self):
        vehicle = self._create_vehicle('failed')
        cases = self._create_cases(vehicle, 2)
        self._report_result(vehicle, cases[0], RESULT_SUCCESS)
        self._report_result(vehicle, cases[1], RESULT_FAILED, minutes_offset=1)

        overview = self._build_overview()
        row = self._get_row(overview, vehicle)

        self.assertTrue(row.is_abnormal)
        self.assertEqual(row.failed_count, 1)
        self.assertEqual(overview.summary.abnormal_vehicle_count, 1)

    def test_overview_marks_timeout_vehicle_as_abnormal(self):
        vehicle = self._create_vehicle('timeout')
        cases = self._create_cases(vehicle, 2)
        self._report_result(vehicle, cases[0], RESULT_SUCCESS)
        self._report_result(vehicle, cases[1], RESULT_TIMEOUT, minutes_offset=1)

        overview = self._build_overview()
        row = self._get_row(overview, vehicle)

        self.assertTrue(row.is_abnormal)
        self.assertEqual(row.timeout_count, 1)
        self.assertEqual(overview.summary.abnormal_vehicle_count, 1)

    def test_overview_ignores_unuploaded_cases_when_calculating_abnormality(self):
        vehicle = self._create_vehicle('partial')
        cases = self._create_cases(vehicle, 2)
        self._report_result(vehicle, cases[0], RESULT_SUCCESS)

        overview = self._build_overview()
        row = self._get_row(overview, vehicle)

        self.assertFalse(row.is_abnormal)
        self.assertEqual(row.success_count, 1)
        self.assertEqual(row.skip_count, 0)
        self.assertEqual(row.total_count, 1)
        self.assertEqual(overview.summary.abnormal_vehicle_count, 0)

    def test_overview_marks_no_upload_vehicle_as_abnormal(self):
        vehicle = self._create_vehicle('no-upload')
        self._create_cases(vehicle, 2)

        overview = self._build_overview()
        row = self._get_row(overview, vehicle)

        self.assertTrue(row.is_abnormal)
        self.assertEqual(row.success_count, 0)
        self.assertEqual(row.skip_count, 0)
        self.assertEqual(row.total_count, 0)
        self.assertEqual(overview.summary.abnormal_vehicle_count, 1)

    def test_overview_abnormal_only_includes_explicit_skip_no_upload_and_failed_vehicles(self):
        success_vehicle = self._create_vehicle('all-success')
        skip_vehicle = self._create_vehicle('skip-only')
        no_upload_vehicle = self._create_vehicle('no-upload-only')
        failed_vehicle = self._create_vehicle('failed-only')

        success_cases = self._create_cases(success_vehicle, 2)
        skip_cases = self._create_cases(skip_vehicle, 2)
        self._create_cases(no_upload_vehicle, 2)
        failed_cases = self._create_cases(failed_vehicle, 2)

        for index, case in enumerate(success_cases):
            self._report_result(success_vehicle, case, RESULT_SUCCESS, minutes_offset=index)

        self._report_result(skip_vehicle, skip_cases[0], RESULT_SUCCESS)
        self._report_result(skip_vehicle, skip_cases[1], RESULT_SKIP, minutes_offset=1)
        self._report_result(failed_vehicle, failed_cases[0], RESULT_SUCCESS)
        self._report_result(failed_vehicle, failed_cases[1], RESULT_FAILED, minutes_offset=1)

        overview = self._build_overview(abnormal_only=True)
        vehicle_codes = {item.vehicle_code for item in overview.items}

        self.assertSetEqual(
            vehicle_codes,
            {
                skip_vehicle.vehicle_code,
                no_upload_vehicle.vehicle_code,
                failed_vehicle.vehicle_code,
            },
        )
        self.assertEqual(overview.summary.vehicle_count, 3)
        self.assertEqual(overview.summary.abnormal_vehicle_count, 3)

    def test_derive_car_log_url_handles_valid_and_invalid_values(self):
        self.assertEqual(
            services.derive_car_log_url('https://example.com/logs/testcase.html'),
            'https://example.com/logs/',
        )
        self.assertIsNone(services.derive_car_log_url(''))
        self.assertIsNone(services.derive_car_log_url('   '))
        self.assertIsNone(services.derive_car_log_url('https://example.com/logs/index.html'))
        self.assertIsNone(services.derive_car_log_url('testcase.html'))

    def test_list_daily_results_derives_car_log_url_for_cockpit_result(self):
        vehicle = self._create_vehicle('car-log')
        case = self._create_cases(vehicle, 1)[0]
        self._report_result(
            vehicle,
            case,
            RESULT_SUCCESS,
            log_url='https://example.com/artifacts/testcase.html',
        )

        items = services.list_daily_results(vehicle.id, self.execute_date, DOMAIN_COCKPIT)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].log_url, 'https://example.com/artifacts/testcase.html')
        self.assertEqual(items[0].car_log_url, 'https://example.com/artifacts/')

    def test_vehicle_domain_report_supports_skip_and_row_errors(self):
        vehicle_platform = McuPlatform.objects.create(
            name='Vehicle Platform',
            version_code='vehicle-platform',
            domain=DOMAIN_VEHICLE,
            is_active=True,
        )
        vehicle = VehicleModel.objects.create(
            platform=vehicle_platform,
            name='Vehicle domain model',
            vehicle_code='VEH-VIU',
            cdc_platform='CDC',
            execution_machine='machine-viu',
            viu_codes=['viu0', 'viu1', 'viu2'],
            is_active=True,
        )
        case0 = AutoTestCase.objects.create(
            vehicle=vehicle,
            viu_code='viu0',
            case_no='CASE-001',
            case_name='Case 1',
            is_active=True,
        )
        case1 = AutoTestCase.objects.create(
            vehicle=vehicle,
            viu_code='viu1',
            case_no='CASE-001',
            case_name='Case 2',
            is_active=True,
        )
        AutoTestCase.objects.create(
            vehicle=vehicle,
            viu_code='viu0',
            case_no='CASE-002',
            case_name='Case 3',
            is_active=True,
        )

        payload = ReportDailyResultsIn(
            vehicle_code=vehicle.vehicle_code,
            execute_date=self.execute_date,
            results=[
                ReportResultItemIn(
                    viu_code='viu0',
                    case_no='CASE-001',
                    start_time=timezone.now(),
                    duration_seconds=60,
                    result=RESULT_SUCCESS,
                    log_url='https://example.com/viu0/testcase.html',
                ),
                ReportResultItemIn(
                    viu_code='viu1',
                    case_no='CASE-001',
                    start_time=timezone.now() + timedelta(minutes=1),
                    duration_seconds=0,
                    result=RESULT_SKIP,
                    log_url='https://example.com/viu1/testcase.html',
                ),
                ReportResultItemIn(
                    viu_code='viu2',
                    case_no='CASE-404',
                    start_time=timezone.now() + timedelta(minutes=2),
                    duration_seconds=30,
                    result=RESULT_SUCCESS,
                ),
            ],
        )

        result = services.report_daily_results(payload)
        self.assertEqual(result['created_count'], 2)
        self.assertEqual(result['ignored_count'], 1)
        self.assertEqual(len(result['errors']), 1)
        self.assertIn('未找到匹配用例', result['errors'][0].message)

        items = services.list_daily_results(
            vehicle.id,
            self.execute_date,
            DOMAIN_VEHICLE,
        )
        self.assertEqual(len(items), 2)
        self.assertEqual({item.viu_code for item in items}, {'viu0', 'viu1'})
        self.assertEqual({item.status for item in items}, {RESULT_SUCCESS, RESULT_SKIP})
        self.assertEqual(
            {item.viu_code: item.car_log_url for item in items},
            {
                'viu0': 'https://example.com/viu0/',
                'viu1': 'https://example.com/viu1/',
            },
        )

        summary = services.get_daily_summary(
            vehicle.id,
            self.execute_date,
            DOMAIN_VEHICLE,
        )
        self.assertEqual(summary.total_count, 2)
        self.assertEqual(summary.success_count, 1)
        self.assertEqual(summary.skip_count, 1)
        self.assertEqual(summary.failed_count, 0)

        overview = services.get_daily_overview(
            DailyOverviewQuery(
                execute_date=self.execute_date,
                domain=DOMAIN_VEHICLE,
            )
        )
        row = self._get_row(overview, vehicle)
        self.assertEqual(row.total_count, 2)
        self.assertEqual(row.success_count, 1)
        self.assertEqual(row.skip_count, 1)
        self.assertTrue(row.is_abnormal)

        self.assertEqual(case0.viu_code, 'viu0')
        self.assertEqual(case1.viu_code, 'viu1')

    def test_get_test_case_history_includes_car_log_url(self):
        vehicle = self._create_vehicle('history')
        case = self._create_cases(vehicle, 1)[0]
        result = self._report_result(
            vehicle,
            case,
            RESULT_FAILED,
            log_url='https://example.com/history/testcase.html',
        )

        history = services.get_test_case_history(str(case.id))

        self.assertEqual(history.total, 1)
        self.assertEqual(history.items[0].id, str(result.id))
        self.assertEqual(history.items[0].car_log_url, 'https://example.com/history/')

    def test_vehicle_domain_import_supports_duplicate_case_no_across_viu_codes(self):
        vehicle_platform = McuPlatform.objects.create(
            name='Vehicle Import Platform',
            version_code='vehicle-import-platform',
            domain=DOMAIN_VEHICLE,
            is_active=True,
        )
        vehicle = VehicleModel.objects.create(
            platform=vehicle_platform,
            name='Vehicle import model',
            vehicle_code='VEH-IMPORT',
            cdc_platform='CDC',
            execution_machine='machine-import',
            viu_codes=['viu0', 'viu1'],
            is_active=True,
        )

        payload = ImportCasePayload(
            vehicle_id=str(vehicle.id),
            rows=[
                ImportCaseRow(viu_code='viu0', case_no='CASE-001', case_name='Case A'),
                ImportCaseRow(viu_code='viu1', case_no='CASE-001', case_name='Case B'),
            ],
        )
        result = services.import_test_cases(None, payload)

        self.assertEqual(result.created_count, 2)
        self.assertEqual(result.updated_count, 0)
        self.assertEqual(result.ignored_count, 0)
        rows = services.list_test_cases(
            TestCaseFilter(domain=DOMAIN_VEHICLE, vehicle_id=str(vehicle.id))
        )
        self.assertEqual(len(rows), 2)
        self.assertEqual({item['viu_code'] for item in rows}, {'viu0', 'viu1'})
