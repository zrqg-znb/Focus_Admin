from ninja import Router

from .auto_test_report_api import report_router, router as auto_test_report_router


router = Router()
router.add_router('', auto_test_report_router)
router.add_router('/report', report_router)
