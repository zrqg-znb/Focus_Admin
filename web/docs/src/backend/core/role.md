# 角色管理

角色管理模块负责角色的定义和权限分配。

## 功能概述

- 角色列表查询
- 角色新增/编辑/删除
- 角色权限分配
- 角色菜单分配

## 数据模型

```python
class Role(CoreModel):
    """角色模型"""
    name = models.CharField(max_length=64, verbose_name="角色名称")
    code = models.CharField(max_length=64, unique=True, verbose_name="角色标识")
    sort = models.IntegerField(default=0, verbose_name="排序")
    status = models.BooleanField(default=True, verbose_name="状态")
    
    # 权限关联
    permissions = models.ManyToManyField('Permission', blank=True, verbose_name="权限")
    menus = models.ManyToManyField('Menu', blank=True, verbose_name="菜单")
    
    class Meta:
        db_table = 'sys_role'
        verbose_name = '角色'
```

## API 接口

### 角色列表

```
GET /api/role/list
```

### 新增角色

```
POST /api/role/add
```

**请求参数：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| name | string | 是 | 角色名称 |
| code | string | 是 | 角色标识 |
| sort | int | 否 | 排序 |
| permission_ids | array | 否 | 权限 ID 列表 |
| menu_ids | array | 否 | 菜单 ID 列表 |

### 编辑角色

```
PUT /api/role/edit/{id}
```

### 删除角色

```
DELETE /api/role/delete/{id}
```

### 分配权限

```
POST /api/role/assign-permissions/{id}
```

**请求参数：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| permission_ids | array | 是 | 权限 ID 列表 |

## 权限说明

| 权限标识 | 说明 |
| --- | --- |
| role:list | 角色列表 |
| role:add | 新增角色 |
| role:edit | 编辑角色 |
| role:delete | 删除角色 |
| role:assign | 分配权限 |
