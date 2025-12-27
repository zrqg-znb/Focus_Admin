from ninja import Router
from apps.performance.api import router as performance_router

router = Router()

router.add_router("/performance", performance_router, tags=["Apps-Performance"])
