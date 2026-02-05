import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "application.settings")

import django

django.setup()

from apps.code_scan.schemas import ShieldApplicationSchema


def main():
    obj = ShieldApplicationSchema.model_validate(
        {
            "id": "1",
            "result_id": "2",
            "applicant_id": "3",
            "approver_id": None,
            "reason": "r",
            "status": "Pending",
            "audit_comment": None,
            "applicant_name": "u",
            "approver_name": None,
            "sys_create_datetime": "2026-02-05 22:55:00",
        }
    )
    print(obj.model_dump())


if __name__ == "__main__":
    main()
