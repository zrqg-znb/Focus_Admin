from ninja import Router

from .agent_skills.api import router as agent_skills_router

router = Router(tags=['Tools'])
router.add_router('/agent-skills', agent_skills_router)
