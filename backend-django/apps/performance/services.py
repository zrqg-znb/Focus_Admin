from .models import PerformanceIndicator, PerformanceIndicatorData
from django.db import transaction
from typing import List, Dict, Any
from datetime import date

def upload_performance_data(payload: Dict[str, Any]) -> Dict[str, Any]:
    project = payload.get('project')
    module = payload.get('module')
    chip_type = payload.get('chip_type')
    test_date = payload.get('date')
    data_items = payload.get('data', [])
    
    success_count = 0
    errors = []
    
    with transaction.atomic():
        for item in data_items:
            code = item.get('code')
            name = item.get('name')
            value = item.get('value')
            
            indicator = None
            
            # 1. Try match by code
            if code:
                indicator = PerformanceIndicator.objects.filter(code=code).first()
            
            # 2. Try match by composite keys
            if not indicator and name:
                indicator = PerformanceIndicator.objects.filter(
                    project=project,
                    module=module,
                    chip_type=chip_type,
                    name=name
                ).first()
            
            if not indicator:
                identifier = code if code else name
                errors.append(f"Indicator not found: {identifier}")
                continue
            
            # Calculate fluctuation
            fluctuation_value = value - indicator.baseline_value
            
            PerformanceIndicatorData.objects.update_or_create(
                indicator=indicator,
                date=test_date,
                defaults={
                    'value': value,
                    'fluctuation_value': fluctuation_value
                }
            )
            success_count += 1
            
    return {"success_count": success_count, "errors": errors}

def import_indicators_service(data_list: List[Dict]) -> Dict[str, Any]:
    from core.user.user_model import User
    
    success_count = 0
    errors = []
    with transaction.atomic():
        for row in data_list:
            try:
                # Extract keys
                code = row.get('code')
                name = row.get('name')
                project = row.get('project')
                module = row.get('module')
                chip_type = row.get('chip_type')
                
                if not name or not project or not module or not chip_type:
                    errors.append(f"Missing required fields for row: {row}")
                    continue

                defaults = row.copy()
                if 'code' in defaults: del defaults['code']
                if 'name' in defaults: del defaults['name']
                if 'project' in defaults: del defaults['project']
                if 'module' in defaults: del defaults['module']
                if 'chip_type' in defaults: del defaults['chip_type']
                
                # Handle Owner field (username to user_id)
                owner_username = defaults.pop('owner', None)
                if owner_username:
                    owner_user = User.objects.filter(username=owner_username).first()
                    if owner_user:
                        defaults['owner'] = owner_user
                
                # Ensure value_type is valid
                if 'value_type' not in defaults:
                    defaults['value_type'] = 'avg'
                
                # Ensure fluctuation_direction is valid
                if 'fluctuation_direction' not in defaults:
                    defaults['fluctuation_direction'] = 'none'

                if code:
                    PerformanceIndicator.objects.update_or_create(
                        code=code,
                        defaults={
                            'name': name,
                            'project': project,
                            'module': module,
                            'chip_type': chip_type,
                            **defaults
                        }
                    )
                else:
                    PerformanceIndicator.objects.update_or_create(
                        project=project,
                        module=module,
                        chip_type=chip_type,
                        name=name,
                        defaults=defaults
                    )
                success_count += 1
            except Exception as e:
                errors.append(f"Error processing row {row}: {str(e)}")
    return {"success_count": success_count, "errors": errors}
