from ninja import Router, File, UploadedFile
from typing import List, Optional
from django.http import HttpResponse
from datetime import datetime
from .schemas import ComplianceRecordSchema, ComplianceUpdateSchema, OverviewSummarySchema, DetailSummarySchema
from .services import get_post_stats, get_post_users_detail, get_user_records, update_branch_status
from .models import ComplianceRecord, ComplianceBranch
from core.user.user_model import User
import openpyxl

router = Router()

@router.get("/stats/post", response=OverviewSummarySchema)
def list_post_stats(request):
    """
    获取岗位维度的合规风险统计
    """
    data = get_post_stats()
    return data

@router.get("/stats/post/{post_id}/users", response=DetailSummarySchema)
def list_post_users(request, post_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None):
    """
    获取指定岗位下的用户风险详情
    """
    data = get_post_users_detail(post_id, start_date, end_date)
    return data

@router.get("/user/{user_id}/records", response=List[ComplianceRecordSchema])
def list_user_records(request, user_id: str):
    """
    获取用户的所有风险记录
    """
    data = get_user_records(user_id)
    return data

@router.put("/branch/{branch_id}")
def update_branch(request, branch_id: str, data: ComplianceUpdateSchema):
    """
    更新分支的处理状态
    """
    update_branch_status(branch_id, data.status, data.remark, user=request.auth)
    return {"msg": "操作成功"}

@router.post("/upload")
def upload_compliance_data(request, file: UploadedFile = File(...)):
    """
    批量上传合规风险数据
    """
    try:
        wb = openpyxl.load_workbook(file)
        ws = wb.active
        
        count = 0
        
        # Iterate rows, skipping header
        for row in ws.iter_rows(min_row=2, values_only=True):
            # Columns: ChangeId, Title, URL, User(Username/Email), Branches, Remark
            if not row or not row[0]:
                continue
                
            change_id = str(row[0]).strip()
            title = str(row[1]) if len(row) > 1 and row[1] else ""
            url = str(row[2]) if len(row) > 2 and row[2] else ""
            user_ident = str(row[3]).strip() if len(row) > 3 and row[3] else ""
            branches_str = str(row[4]) if len(row) > 4 and row[4] else ""
            remark = str(row[5]) if len(row) > 5 and row[5] else ""
            
            # Find User
            user = None
            if user_ident:
                user = User.objects.filter(username=user_ident).first()
                if not user:
                    user = User.objects.filter(email=user_ident).first()
            
            if not user:
                # If user not found, maybe create a dummy user or skip?
                # For now, skip if no user found, or assign to admin?
                # Or just don't assign user (nullable?) -> Model says user is required.
                # We skip.
                continue
                
            # Create/Update Record
            record, created = ComplianceRecord.objects.update_or_create(
                change_id=change_id,
                defaults={
                    'user': user,
                    'title': title,
                    'url': url,
                    'update_time': datetime.now(),
                    'remark': remark
                }
            )
            
            # Parse Branches
            if branches_str:
                # Support comma or newline separated
                branch_names = [b.strip() for b in branches_str.replace('\n', ',').split(',') if b.strip()]
                
                current_branches = {b.branch_name: b for b in record.branches.all()}
                
                for bn in branch_names:
                    if bn not in current_branches:
                        ComplianceBranch.objects.create(record=record, branch_name=bn)
            
            count += 1
            
        return {"msg": f"成功处理 {count} 条记录"}
        
    except Exception as e:
        return {"msg": f"上传失败: {str(e)}"}

@router.get("/template")
def get_upload_template(request):
    """
    获取上传模板
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["ChangeId", "Title", "URL", "User(Username/Email)", "Branches(comma separated)", "Remark"])
    
    # Add some example data
    ws.append(["I123456", "Fix NPE", "http://git/...", "zhangsan", "master, release-1.0", "Urgent"])
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=compliance_template.xlsx'
    wb.save(response)
    return response
