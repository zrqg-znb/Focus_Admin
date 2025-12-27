from ninja import Router, UploadedFile, File
from ninja.pagination import paginate
from typing import List
from .schemas import (
    PerformanceIndicatorSchema, 
    PerformanceIndicatorCreateSchema, 
    PerformanceIndicatorUpdateSchema,
    PerformanceDataUploadSchema,
    PerformanceDataUploadResponse,
    PerformanceDataTrendSchema
)
from .models import PerformanceIndicator, PerformanceIndicatorData
from .services import upload_performance_data, import_indicators_service
from django.shortcuts import get_object_or_404
from common.fu_pagination import MyPagination
from common.fu_crud import create, delete, update, retrieve
from django.db.models import Q
import openpyxl
from io import BytesIO

router = Router()

# --- Indicator CRUD ---

@router.post("/indicators", response=PerformanceIndicatorSchema)
def create_indicator(request, payload: PerformanceIndicatorCreateSchema):
    return create(request, payload, PerformanceIndicator)

@router.delete("/indicators/{id}")
def delete_indicator(request, id: str):
    delete(id, PerformanceIndicator)
    return {"success": True}

@router.put("/indicators/{id}", response=PerformanceIndicatorSchema)
def update_indicator(request, id: str, payload: PerformanceIndicatorUpdateSchema):
    return update(request, id, payload, PerformanceIndicator)

@router.get("/indicators", response=List[PerformanceIndicatorSchema])
@paginate(MyPagination)
def list_indicators(request, search: str = None):
    qs = PerformanceIndicator.objects.all()
    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(code__icontains=search) | Q(module__icontains=search))
    return qs

@router.post("/indicators/import")
def import_indicators(request, file: UploadedFile = File(...)):
    # Read Excel file
    wb = openpyxl.load_workbook(filename=BytesIO(file.read()))
    ws = wb.active
    
    # Get headers from first row
    headers = [cell.value for cell in ws[1]]
    
    # Map headers to fields
    # Expected headers: "业务唯一标识", "指标名称", "所属模块", "所属项目", "芯片类型", etc.
    header_map = {
        "业务唯一标识": "code",
        "指标名称": "name",
        "所属模块": "module",
        "所属项目": "project",
        "芯片类型": "chip_type",
        "值类型": "value_type",
        "基线值": "baseline_value",
        "单位": "baseline_unit",
        "允许浮动范围": "fluctuation_range",
        "浮动方向": "fluctuation_direction",
        "责任人": "owner"
    }
    
    data_list = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        row_dict = {}
        for i, value in enumerate(row):
            if i < len(headers):
                header_name = headers[i]
                if header_name in header_map:
                    field_name = header_map[header_name]
                    row_dict[field_name] = value
        if row_dict:
            data_list.append(row_dict)
            
    result = import_indicators_service(data_list)
    return result

# --- Data Upload & Trend ---

@router.post("/data/upload", response=PerformanceDataUploadResponse)
def upload_data(request, payload: PerformanceDataUploadSchema):
    result = upload_performance_data(payload.dict())
    return result

@router.get("/data/trend", response=List[PerformanceDataTrendSchema])
def get_trend(request, indicator_id: str, days: int = 7):
    from datetime import timedelta, date
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    
    qs = PerformanceIndicatorData.objects.filter(
        indicator_id=indicator_id,
        date__gte=start_date,
        date__lte=end_date
    ).order_by('date')
    
    return list(qs)

# --- Dashboard Data ---

@router.get("/dashboard", response=List[dict]) # Simplified schema for dashboard table
@paginate(MyPagination)
def dashboard_data(request, project: str = None, module: str = None, chip_type: str = None, date: str = None):
    # This needs to return list of indicators with their data for a specific date (or latest)
    # The requirement says: Filters: Project, Module, Chip Type, Date.
    # Table: Indicator Name, Baseline, Current Value, Fluctuation.
    
    qs = PerformanceIndicator.objects.all()
    if project:
        qs = qs.filter(project=project)
    if module:
        qs = qs.filter(module=module)
    if chip_type:
        qs = qs.filter(chip_type=chip_type)
        
    # We need to attach data for the specific date
    from datetime import date as dt_date
    target_date = dt_date.today()
    if date:
        try:
            target_date = dt_date.fromisoformat(str(date))
        except ValueError:
            pass
            
    result = []
    # Prefetch data? 
    # Since we paginate indicators, we can just loop and query data (N+1 but limited by page size)
    # Or use Prefetch
    
    for indicator in qs:
        data_obj = PerformanceIndicatorData.objects.filter(indicator=indicator, date=target_date).first()
        
        row = {
            "id": indicator.id,
            "name": indicator.name,
            "code": indicator.code,
            "project": indicator.project,
            "module": indicator.module,
            "chip_type": indicator.chip_type,
            "baseline_value": indicator.baseline_value,
            "baseline_unit": indicator.baseline_unit,
            "fluctuation_range": indicator.fluctuation_range,
            "fluctuation_direction": indicator.fluctuation_direction,
            "current_value": data_obj.value if data_obj else None,
            "fluctuation_value": data_obj.fluctuation_value if data_obj else None,
            "data_date": data_obj.date if data_obj else None
        }
        result.append(row)
        
    return result
