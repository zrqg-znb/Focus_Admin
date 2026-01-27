from ninja import Router
from apps.performance.api import router as performance_router
from apps.project_manager.router import router as project_manager_router
from apps.dashboard.api import router as dashboard_router
from apps.integration_report.integration_api import router as integration_report_router
from apps.code_compliance.api import router as compliance_router
from apps.delivery_matrix.api import router as delivery_matrix_router

router = Router()

router.add_router("/performance", performance_router, tags=["Apps-Performance"])
router.add_router("/project-manager", project_manager_router)
router.add_router("/dashboard", dashboard_router, tags=["Apps-Dashboard"])
router.add_router("/integration-report", integration_report_router, tags=["Apps-IntegrationReport"])
router.add_router("/code-compliance", compliance_router, tags=["Apps-CodeCompliance"])
router.add_router("/delivery-matrix", delivery_matrix_router, tags=["Apps-DeliveryMatrix"])
