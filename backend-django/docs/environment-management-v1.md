# 环境管理模块 v1 设计文档

## 背景与目标

环境管理模块用于统一维护部门测试环境执行机和远程环境，让平台用户可以查看可用环境，让环境用户可以安全占用、排队、插队和释放环境，让环境管理员可以维护环境基础配置。

v1 的核心目标：

- 管理端维护环境基础信息：IP、账号、加密密码、领域、分类、项目、车型、测试设备、配置情况文本、货架位置和备注。
- 管理端提供测试设备管理能力，支持多级设备类型树和类型下设备 CRUD。
- 用户端提供列表和平铺视图，默认展示全部环境，支持收藏视图。
- 环境使用流程支持占用、释放、排队、插队、查看队列和占用记录。
- 密码明文只允许环境用户和环境管理员查看；平台默认用户只拿到脱敏字段。
- Windows RDP 入口只生成 `rdp://IP`，不传账号和密码。

## 角色与权限

本模块当前只设计三类角色：

- 平台用户：系统已有默认角色，通常为 `Role.name = 默认`。可以进入用户端查看环境列表、队列和记录，不能查看明文密码，不能收藏、占用、排队、插队、释放或打开 RDP。
- 环境用户：新增系统角色 `environment_user`。可以进入用户端，查看明文账号密码，收藏环境，占用、排队、插队、释放自己的占用，并打开 `rdp://IP`。
- 环境管理员：新增系统角色 `env_admin`。拥有模块最高权限，可以进入用户端和管理端，查看明文账号密码，维护环境配置，并释放任意环境。

初始化命令：

```bash
python manage.py init_environment_management
```

该命令会创建菜单、接口权限、`environment_user`、`env_admin`，并尝试给系统已有 `默认` 角色绑定用户端只读菜单和只读接口。如果系统默认角色名称后续改变，需要同步更新初始化命令。

## 数据模型

后端模块位置：`backend-django/apps/environment_management/`

- `TestEnvironment`：环境主表，保存环境配置、状态、当前占用人和占用开始时间。
- `EnvironmentDeviceType`：测试设备类型树，支持多级分类。
- `EnvironmentTestDevice`：测试设备主数据，挂在某一个设备类型下。
- `TestEnvironment.devices`：环境与测试设备的多对多绑定关系。
- `EnvironmentFavorite`：用户收藏表，用户与环境唯一关联。
- `EnvironmentQueue`：等待队列表，按 `position` 和 `requested_at` 排序，`queue_type` 区分普通排队和插队。
- `EnvironmentRecord`：操作记录表，记录占用、释放、排队、取消排队、插队和管理员配置变更。

密码字段只存 `password_encrypted`，使用 `apps.deepaudit.encryption` 的 Fernet 实现，密钥来源是 `DJANGO_SECRET_KEY`。更换生产密钥会影响历史密码解密，必须谨慎。

字段调整记录：

- `device_material` 已升级为测试设备主数据，不再作为环境文本字段使用。
- `asset_number` 已废弃，不再进入接口和页面。
- `config` JSON 已改为 `config_description` 文本描述。
- 新增 `remark` 作为环境备注。
- 迁移时旧 `config` 会序列化写入 `config_description`，旧 `device_material` 和 `asset_number` 会写入 `remark` 作为历史信息。

## 业务规则

- 无人占用且队列为空时，环境用户申请占用会直接成功。
- 环境已被占用时，其他环境用户不能直接占用，需要排队或插队。
- 普通排队进入队尾。
- 插队进入已有插队用户之后、普通排队用户之前，但不会抢占当前占用人。
- 同一用户不能在同一环境重复排队。
- 当前占用人不能再排队。
- 释放环境后只将环境置为空闲，并提示队首用户可以手动占用；系统不会自动转交给队首。
- 如果队列存在，只有队首用户可以在空闲时占用。
- 平台默认用户只能查看列表、队列和记录，所有使用动作会被后端拒绝。
- 测试设备类型删除前必须确认没有子类型和测试设备。
- 测试设备删除前必须确认没有被任何环境绑定。
- 队列重排必须使用不带 `select_related('user')` 的独立查询，避免 Django 抛出 `deferred and traversed using select_related` 错误。

## API 与前端页面

后端路由前缀：`/api/environment-management`

主要接口：

- `GET /environments`：环境列表，返回 `can_view_secret` 和 `can_use_environment`，前端据此控制展示与操作。
- `POST /environments`、`PUT /environments/{id}`、`DELETE /environments/{id}`：管理端 CRUD，仅环境管理员可用。
- `POST|DELETE /environments/{id}/favorite`：收藏/取消收藏，仅环境用户和管理员拥有接口权限。
- `POST /environments/{id}/occupy`：占用，仅环境用户和管理员可用。
- `POST /environments/{id}/release`：释放，当前占用环境用户或管理员可用。
- `POST /environments/{id}/queue`：排队，仅环境用户和管理员可用。
- `POST /environments/{id}/jump-queue`：插队，仅环境用户和管理员可用。
- `DELETE /environments/{id}/queue/me`：取消自己的排队。
- `GET /environments/{id}/queue`：查看队列。
- `GET /environments/{id}/records`：查看操作记录。
- `GET /device-types`、`POST /device-types`、`PUT /device-types/{id}`、`DELETE /device-types/{id}`：测试设备类型树管理，仅环境管理员可用。
- `GET /devices`、`POST /devices`、`PUT /devices/{id}`、`DELETE /devices/{id}`：测试设备管理，仅环境管理员可用。
- `GET /device-options`：环境表单的测试设备级联多选项，仅环境管理员可用。

前端页面：

- `/environment-management/user`：用户端，支持列表/平铺、全部/收藏、筛选、占用时长、队列和记录抽屉。
- `/environment-management/admin`：管理端，使用 Tab 分为“环境管理”和“测试设备管理”。环境管理使用 `zq-table` 和弹窗表单，测试设备管理使用左侧类型树和右侧设备列表。

## 后续维护约定

后续任何环境管理模块改动都需要同步更新本文档，至少补充：

- 角色或权限变化。
- 队列、占用、释放规则变化。
- 数据模型字段或迁移变化。
- API 入参、出参或安全策略变化。
- 前端用户交互变化。
