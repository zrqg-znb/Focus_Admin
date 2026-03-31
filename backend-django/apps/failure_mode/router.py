from ninja import Router

from .failure_mode_api import router as fm_router
from .failure_mode_workflow_api import router as fm_workflow_router

router = Router()
router.add_router('', fm_router)
router.add_router('/workflow', fm_workflow_router)

__all__ = ['router']

