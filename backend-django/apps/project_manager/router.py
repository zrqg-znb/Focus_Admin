from ninja import Router
from .project.project_api import router as project_router
from .milestone.milestone_api import router as milestone_router
from .iteration.iteration_api import router as iteration_router
from .code_quality.code_quality_api import router as code_quality_router
from .dts.dts_api import router as dts_router
from .report.report_api import router as report_router

router = Router()

router.add_router("/projects", project_router)
router.add_router("/milestones", milestone_router)
router.add_router("/iterations", iteration_router)
router.add_router("/code_quality", code_quality_router)
router.add_router("/dts", dts_router)
router.add_router("/report", report_router)
