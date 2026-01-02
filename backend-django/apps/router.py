from ninja import Router
from apps.performance.api import router as performance_router
from apps.project_manager.router import router as project_manager_router

router = Router()

router.add_router("/performance", performance_router, tags=["Apps-Performance"])
router.add_router("/project-manager", project_manager_router)
