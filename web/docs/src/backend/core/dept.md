# 部门管理

部门管理模块负责组织架构的管理。

## 功能概述

- 部门树形结构管理
- 部门层级关系
- 部门用户关联

## 数据模型

```python
class Dept(CoreModel):
    """部门模型"""
    name = models.CharField(max_length=64, verbose_name="部门名称")
    code = models.CharField(max_length=64, unique=True, verbose_name="部门编码")
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    sort = models.IntegerField(default=0, verbose_name="排序")
    leader = models.CharField(max_length=64, blank=True, null=True, verbose_name="负责人")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="联系电话")
    email = models.EmailField(blank=True, null=True, verbose_name="邮箱")
    status = models.BooleanField(default=True, verbose_name="状态")
    
    class Meta:
        db_table = 'sys_dept'
        verbose_name = '部门'
```

## API 接口

### 部门树

```
GET /api/dept/tree
```

**响应示例：**

```json
{
  "code": 200,
  "data": [
    {
      "id": 1,
      "name": "总公司",
      "code": "HQ",
      "children": [
        {
          "id": 2,
          "name": "研发部",
          "code": "RD",
          "leader": "张三"
        },
        {
          "id": 3,
          "name": "市场部",
          "code": "MKT",
          "leader": "李四"
        }
      ]
    }
  ]
}
```

### 新增部门

```
POST /api/dept/add
```

**请求参数：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| name | string | 是 | 部门名称 |
| code | string | 是 | 部门编码 |
| parent_id | int | 否 | 上级部门 ID |
| leader | string | 否 | 负责人 |
| sort | int | 否 | 排序 |

### 编辑部门

```
PUT /api/dept/edit/{id}
```

### 删除部门

```
DELETE /api/dept/delete/{id}
```

::: warning 注意
删除部门时，如果部门下有子部门或用户，需要先处理关联数据。
:::

## 数据权限

部门可用于数据权限控制，实现不同部门只能查看本部门数据的功能。

```python
def get_dept_data_scope(user):
    """获取用户数据权限范围"""
    # 获取用户所在部门及下级部门
    dept_ids = get_dept_and_children(user.dept_id)
    return dept_ids
```
