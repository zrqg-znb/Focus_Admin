#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Department Sync Service
Syncs department information from external source (Mocked)
"""
import logging
from typing import Dict, Optional
from django.db import transaction
from core.dept.dept_model import Dept
from core.user.user_model import User

logger = logging.getLogger(__name__)

def mock_get_user_dept_info(username: str) -> Dict:
    """
    Mock API response for user department info
    """
    # This is the structure provided by user
    return {
        "l0_dept_code": "022471",
        "l0_name": "11",
        "l1_dept_code": "048459",
        "l1_name": "22",
        "l2_dept_code": "068620",
        "l2_name": "33",
        "l3_dept_code": "068647",
        "l3_name": "44",
        "l4_dept_code": "069507",
        "l4_name": "55",
        "orgainzation_manager": "张瑞清"
    }

@transaction.atomic
def sync_user_dept_info(user: User) -> None:
    """
    Sync user department info from remote source
    """
    if not user.username:
        logger.warning(f"User {user.id} has no username, skipping dept sync")
        return

    try:
        # 1. Get info (Mock)
        # In real scenario, this would call an external API
        dept_info = mock_get_user_dept_info(user.username)
        if not dept_info:
            return

        # 2. Process departments
        parent = None
        last_valid_dept = None
        
        # Iterate levels 0 to 4
        for i in range(5):
            code_key = f"l{i}_dept_code"
            name_key = f"l{i}_name"
            
            code = dept_info.get(code_key)
            name = dept_info.get(name_key)
            
            if not code or not code.strip():
                # If current level is empty, we stop going deeper
                break
                
            code = code.strip()
            name = name.strip() if name else f"Dept-{code}"
            
            # Find or create Dept
            dept = Dept.objects.filter(code=code).first()
            if not dept:
                dept = Dept.objects.create(
                    code=code,
                    name=name,
                    parent=parent,
                    level=i,
                    status=True
                )
            else:
                # Update name if changed (optional)
                updated = False
                if dept.name != name:
                    dept.name = name
                    updated = True
                if dept.parent != parent:
                    dept.parent = parent
                    updated = True
                if dept.level != i:
                    dept.level = i
                    updated = True
                
                if updated:
                    dept.save()
            
            parent = dept
            last_valid_dept = dept

        # 3. Update User
        update_fields = []
        if last_valid_dept:
            if user.dept != last_valid_dept:
                user.dept = last_valid_dept
                update_fields.append('dept')
        
        # Sync manager
        org_manager = dept_info.get("orgainzation_manager")
        if org_manager and user.manager != org_manager:
            user.manager = org_manager
            update_fields.append('manager')
            
        if update_fields:
            user.save(update_fields=update_fields)
            logger.info(f"Updated user {user.username} info: {update_fields}")

    except Exception as e:
        logger.error(f"Error syncing department info for user {user.username}: {str(e)}")
