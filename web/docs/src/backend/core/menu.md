# 菜单管理

菜单管理模块负责系统菜单的配置和管理。

## 功能概述

- 菜单树形结构管理
- 动态路由配置
- 菜单图标配置
- 菜单权限关联

## 数据模型

```python
class Menu(CoreModel):
    """菜单模型"""
    name = models.CharField(max_length=64, verbose_name="菜单名称")
    code = models.CharField(max_length=64, verbose_name="菜单标识")
    icon = models.CharField(max_length=64, blank=True, null=True, verbose_name="图标")
    path = models.CharField(max_length=255, blank=True, null=True, verbose_name="路由路径")
    component = models.CharField(max_length=255, blank=True, null=True, verbose_name="组件路径")
    redirect = models.CharField(max_length=255, blank=True, null=True, verbose_name="重定向")
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    sort = models.IntegerField(default=0, verbose_name="排序")
    type = models.IntegerField(choices=((1, '目录'), (2, '菜单'), (3, '按钮')), default=2)
    visible = models.BooleanField(default=True, verbose_name="是否显示")
    status = models.BooleanField(default=True, verbose_name="状态")
    
    class Meta:
        db_table = 'sys_menu'
        verbose_name = '菜单'
```

## API 接口

### 菜单树

```
GET /api/menu/tree
```

**响应示例：**

```json
{
  "code": 200,
  "data": [
    {
      "id": 1,
      "name": "系统管理",
      "code": "system",
      "icon": "setting",
      "path": "/system",
      "children": [
        {
          "id": 2,
          "name": "用户管理",
          "code": "user",
          "icon": "user",
          "path": "/system/user",
          "component": "views/system/user/index.vue"
        }
      ]
    }
  ]
}
```

### 用户菜单

```
GET /api/menu/user-menus
```

返回当前登录用户有权限访问的菜单列表。

## 前端路由生成

菜单数据会转换为 Vue Router 的路由配置：

```typescript
// 菜单转路由
function generateRoutes(menus: Menu[]): RouteRecordRaw[] {
  return menus.map(menu => ({
    path: menu.path,
    name: menu.code,
    component: () => import(`@/${menu.component}`),
    meta: {
      title: menu.name,
      icon: menu.icon
    },
    children: menu.children ? generateRoutes(menu.children) : []
  }))
}
```
