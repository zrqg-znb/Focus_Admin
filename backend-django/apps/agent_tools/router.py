from ninja import Router

from .skill_optimizer.api import router as skill_optimizer_router

router = Router(tags=['AgentTools'])
router.add_router('/skill-optimizer', skill_optimizer_router)
