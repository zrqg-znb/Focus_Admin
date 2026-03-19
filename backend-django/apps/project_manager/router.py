from ninja import Router
from .project.project_api import router as project_router
from .milestone.milestone_api import router as milestone_router
from .iteration.iteration_api import router as iteration_router
from .code_quality.code_quality_api import router as code_quality_router
from .dts.dts_api import router as dts_router
from .hardware.hardware_api import router as hardware_router
from .report.report_api import router as report_router
from .requirement_board.requirement_board_api import router as requirement_board_router
from .requirement_workspace.requirement_workspace_api import (
    router as requirement_workspace_router,
)
from .sync_log_api import router as sync_log_router
from .dts_statistics.dts_statistics_api import router as dts_statistics_router

router = Router()

router.add_router("/projects", project_router)
router.add_router("/milestones", milestone_router)
router.add_router("/iterations", iteration_router)
router.add_router("/code_quality", code_quality_router)
router.add_router("/dts", dts_router)
router.add_router("/hardware", hardware_router)
router.add_router("/report", report_router)
router.add_router("/requirement-board", requirement_board_router)
router.add_router("/requirement-workspace", requirement_workspace_router)
router.add_router("/dts-statistics", dts_statistics_router)
router.add_router("/", sync_log_router)
