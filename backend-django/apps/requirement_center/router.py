from ninja import Router

from .requirement.requirement_api import router as requirement_router

router = Router()
router.add_router("/requirements", requirement_router)
