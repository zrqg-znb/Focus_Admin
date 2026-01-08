from ninja import Schema, ModelSchema, Field
from typing import List, Optional
from .project_model import Project

class ProjectCreateSchema(Schema):
    name: str = Field(..., description="项目名")
    domain: str = Field(..., description="项目领域")
    type: str = Field(..., description="项目类型")
    code: str = Field(..., description="项目编码")
    manager_ids: List[str] = Field(..., description="项目经理ID列表")
    is_closed: bool = Field(False, description="是否结项")
    repo_url: Optional[str] = Field(None, description="制品仓号/地址")
    remark: Optional[str] = Field(None, description="备注")
    enable_milestone: bool = Field(True, description="是否统计里程碑")
    enable_iteration: bool = Field(True, description="是否统计迭代数据")
    enable_quality: bool = Field(True, description="是否统计代码质量")
    design_id: Optional[str] = Field(None, description="迭代中台配置 id")
    sub_teams: Optional[List[str]] = Field(None, description="迭代责任团队")

class ProjectUpdateSchema(Schema):
    name: Optional[str] = None
    domain: Optional[str] = None
    type: Optional[str] = None
    code: Optional[str] = None
    manager_ids: Optional[List[str]] = None
    is_closed: Optional[bool] = None
    repo_url: Optional[str] = None
    remark: Optional[str] = None
    enable_milestone: Optional[bool] = None
    enable_iteration: Optional[bool] = None
    enable_quality: Optional[bool] = None
    design_id: Optional[str] = None
    sub_teams: Optional[List[str]] = None

class ProjectFilterSchema(Schema):
    keyword: Optional[str] = Field(None, description="搜索关键字(项目名/编码)")
    domain: Optional[str] = None
    type: Optional[str] = None
    manager_id: Optional[str] = Field(None, description="项目经理ID")
    is_closed: Optional[bool] = None
    enable_milestone: Optional[bool] = None
    enable_iteration: Optional[bool] = None
    enable_quality: Optional[bool] = None

class ProjectOut(ModelSchema):
    managers_info: List[dict] = Field([], description="项目经理详情")
    is_favorited: bool = Field(False, description="当前用户是否收藏")
    
    class Meta:
        model = Project
        fields = "__all__"
        exclude = ['managers', 'favorited_by']

    @staticmethod
    def resolve_managers_info(obj):
        return [{"id": m.id, "name": m.name or m.username} for m in obj.managers.all()]

    @staticmethod
    def resolve_is_favorited(obj, context):
        request = context.get('request')
        if request and request.auth:
            # 检查当前用户是否在 favorited_by 列表中
            # 注意：这里可能产生 N+1 查询，最好在 QuerySet 中 prefetch 或 annotate
            return obj.favorited_by.filter(id=request.auth.id).exists()
        return False

    class Config:
        from_attributes = True
