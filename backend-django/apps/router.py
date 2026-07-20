from ninja import Router
from apps.failure_mode.router import router as failure_mode_router
from apps.performance.api import router as performance_router
from apps.project_manager.router import router as project_manager_router
from apps.dashboard.api import router as dashboard_router
from apps.integration_report.integration_api import router as integration_report_router
from apps.auto_test_report.router import router as auto_test_report_router
from apps.code_compliance.api import router as compliance_router
from apps.cmc_contribution.api import router as cmc_contribution_router
from apps.delivery_matrix.api import router as delivery_matrix_router
from apps.code_scan.api import router as code_scan_router
from apps.deepaudit.router import router as deepaudit_router
from apps.environment_management.api import router as environment_management_router
from apps.tools.router import router as tools_router

router = Router()

router.add_router("/failure-mode", failure_mode_router, tags=["Apps-FailureMode"])
router.add_router("/performance", performance_router, tags=["Apps-Performance"])
router.add_router("/project-manager", project_manager_router)
router.add_router("/dashboard", dashboard_router, tags=["Apps-Dashboard"])
router.add_router("/integration-report", integration_report_router, tags=["Apps-IntegrationReport"])
router.add_router("/auto-test-report", auto_test_report_router, tags=["Apps-AutoTestReport"])
router.add_router("/code-compliance", compliance_router, tags=["Apps-CodeCompliance"])
router.add_router("/cmc-contribution", cmc_contribution_router, tags=["Apps-CmcContribution"])
router.add_router("/delivery-matrix", delivery_matrix_router, tags=["Apps-DeliveryMatrix"])
router.add_router("/code-scan", code_scan_router, tags=["Apps-CodeScan"])
router.add_router("/deepaudit", deepaudit_router, tags=["Apps-DeepAudit"])
router.add_router("/environment-management", environment_management_router, tags=["Apps-EnvironmentManagement"])
router.add_router("/tools", tools_router, tags=["Apps-Tools"])
