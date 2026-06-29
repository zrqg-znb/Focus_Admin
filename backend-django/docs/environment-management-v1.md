# 环境管理模块 v1 设计文档

## 背景与目标

环境管理模块用于统一维护部门测试环境执行机和远程环境。平台用户可以查看环境信息；环境用户可以收藏、占用、排队和释放环境；环境管理员维护环境配置、测试设备类型树和环境操作公告。

当前版本的核心目标：

- 管理端维护环境基础信息：IP、账号、加密密码、BOMID、环境资产编号、领域、分类、项目、车型、配置情况、货架位置、备注和环境测试设备实例。
- 管理端测试设备管理 Tab 维护“测试设备类型树 + 具体测试设备主数据”。
- 管理端环境表单先选择已有测试设备，再填写该环境下这台设备的资产编号和备注。
- 用户端提供列表和平铺视图，默认展示全部环境，支持收藏优先排序，并把查询入口收敛到表头筛选。
- 用户端新增环境详情抽屉，用于展示配置情况、货架位置、环境资产编号、备注和设备实例明细。
- 环境使用流程支持占用、释放、排队、取消排队、查看队列和分页查看占用记录。
- 前端暂时隐藏插队按钮，后端插队接口和逻辑保留，便于后续恢复。
- 后端提供队列变化通知占位，用于后续公司内网按 username 发送“位置前进”和“轮到自己”消息。
- 密码只允许在管理端写入并加密保存，环境列表和详情接口不返回密码；账号对所有可访问用户可见。
- Windows RDP 入口使用 `focus-rdp://open?host=IP`，且只在占用成功后触发，不在列表或卡片中常驻展示。

## 角色与权限

本模块当前只设计三类角色：

- 平台用户：系统已有默认角色。可以进入用户端查看环境列表、详情、队列和记录；不能收藏、占用、排队、释放或打开 RDP；不能查看密码，因为后端不会返回密码字段。
- 环境用户：系统角色编码 `environment_user`。可以进入用户端，查看账号，收藏环境，占用、排队、取消排队、释放自己的占用，并在占用成功后通过 Focus RDP 启动器打开远程桌面。
- 环境管理员：系统角色编码 `env_admin`。拥有模块最高权限，可以进入用户端和管理端，维护环境配置、设备类型、公告配置，并释放任意环境。

初始化命令：

```bash
python manage.py init_environment_management
```

该命令会创建菜单、接口权限、`environment_user` 和 `env_admin`，并尝试给系统已有默认角色绑定用户端只读菜单和只读接口。如果系统默认角色名称后续改变，需要同步更新初始化命令。

## 数据模型

后端模块位置：`backend-django/apps/environment_management/`

- `TestEnvironment`：环境主表，保存环境配置、状态、当前占用人和占用开始时间。
- `TestEnvironment.bomid`：环境 BOMID，用于用户端列表快速识别。
- `TestEnvironment.asset_number`：环境执行机或环境本体资产编号，不等同于测试外设资产编号。
- `EnvironmentDeviceType`：测试设备类型树，支持多级分类。
- `EnvironmentTestDevice`：测试设备主数据，挂在某个设备类型下，由管理端测试设备管理 Tab 维护。
- `EnvironmentDeviceBinding`：环境测试设备实例，表示某个环境实际拥有的一项测试外设。字段包含环境、测试设备主数据、冗余设备类型和设备名称、环境内设备资产编号、备注和排序。
- `TestEnvironment.devices`：旧版环境与测试设备主数据的多对多绑定关系，保留兼容，新前端不再写入。
- `EnvironmentFavorite`：用户收藏表，用户与环境唯一关联。
- `EnvironmentQueue`：等待队列表，按 `position` 和 `requested_at` 排序，`queue_type` 区分普通排队和插队。
- `EnvironmentRecord`：操作记录表，记录占用、释放、排队、取消排队、插队和管理员配置变更。
- `EnvironmentAnnouncement`：环境操作公告配置，保存标题、富文本内容和启用状态。

密码字段只存 `password_encrypted`，使用 `apps.deepaudit.encryption` 的 Fernet 实现，密钥来源是 `DJANGO_SECRET_KEY`。更换生产密钥会影响历史密码解密，必须谨慎。当前接口安全边界是：密码可以写入和加密保存，但不会通过环境列表、详情或用户端接口返回。

## 字段与迁移记录

- `device_material` 已废弃，不再作为环境文本字段使用。
- 旧版 `asset_number` 曾被移除，本轮重新新增为环境本体资产编号。
- `config` JSON 已改为 `config_description` 文本描述。
- 新增 `remark` 作为环境备注。
- 新增 `bomid` 作为环境主表字段。
- 新增 `EnvironmentDeviceBinding` 作为环境设备实例表。
- 迁移会把旧 `TestEnvironment.devices` 多对多绑定转换成环境设备实例：测试设备取旧设备主数据，设备类型和设备名称冗余保存，设备资产编号为空，备注取旧设备备注。
- `/devices` 和 `/device-options` 仍是正式能力，管理端用它们维护和选择测试设备主数据。
- 新环境创建/更新接口使用 `devices: EnvironmentDeviceInput[]`。为短期兼容，后端仍接受旧 `device_ids` 并转换为设备实例。

## 业务规则

- 无人占用且队列为空时，环境用户申请占用会直接成功。前端在空闲状态下只展示“占用”按钮，不展示排队入口。
- 环境已被占用时，其他环境用户不能直接占用，需要排队。
- 普通排队进入队尾。
- 插队进入已有插队用户之后、普通排队用户之前，但不会抢占当前占用人。当前前端隐藏插队按钮，后端能力保留。
- 同一用户不能在同一环境重复排队。
- 当前占用人不能再排队。
- 释放环境后只将环境置为空闲，并提示队首用户可以手动占用；系统不会自动转交给队首。
- 如果队列存在，只有队首用户可以在空闲时占用。
- 平台默认用户只能查看列表、详情、队列和记录，所有使用动作会被后端拒绝。
- 测试设备类型删除前必须确认没有子类型、旧测试设备主数据和环境设备实例引用。
- 环境设备实例必须选择已有测试设备；设备资产编号和备注均非必填。
- 用户端测试设备列只显示设备实例的 `device_name`，不显示类型路径、资产编号和备注；完整信息进入详情抽屉。
- 用户端列表展示账号和 BOMID，不展示密码、配置情况和货架位置；配置情况和货架位置进入详情抽屉。
- 用户端收藏置顶必须在数据库分页前全局生效，排序规则为：当前用户已收藏优先、空闲优先、环境排序值倒序、IP 正序。
- RDP 只能在占用接口成功后由前端触发；列表和平铺卡片不再常驻 RDP 控制台按钮。
- 队列重排必须使用不带 `select_related('user')` 的独立查询，避免 Django 抛出 `deferred and traversed using select_related` 错误。
- 事务内锁定等待队列时必须使用独立查询，不复用展示用的 `_waiting_queues()`。
- 如果环境操作公告启用，用户端占用和排队前会弹窗要求确认。释放环境只使用标准文本二次确认。
- 队列通知当前只覆盖两类正向变化：等待用户位置前进、环境空闲且用户成为队首可手动占用。插队导致其他用户后移时不发送通知。
- 队列通知使用 `send_environment_queue_notification_by_username(username, title, content, payload)` 作为占位接口，本地仅写日志；公司内网接入真实消息系统时替换该函数内部实现即可。
- 队列通知是业务旁路：通过事务提交后回调触发，且发送异常只记录日志，不回滚占用、释放、取消排队等主流程。
- 队列通知 payload 只包含环境 ID、IP、项目、车型、队列位置、事件和是否可占用，不允许携带账号、密码、RDP 凭据或加密密码字段。
- 裸 `rdp://IP` 在 Windows/浏览器中没有默认协议处理器，前端主入口必须使用 `focus-rdp://open?host=IP`。
- RDP 打开逻辑只捕获浏览器同步抛出的协议异常，不使用 `setTimeout + document.hidden` 推断失败。
- 占用记录必须按 `page/pageSize` 后端分页获取，前端记录弹窗翻页时重新请求接口。
- 环境列表和测试设备列表的筛选统一走服务端查询，前端不基于当前页做本地过滤，避免跨页数据缺失。
- 表头筛选多选值以逗号字符串提交，例如 `domains=cockpit,vehicle`；后端统一解析、去空和去重。
- 下拉筛选选项由 `GET /filter-options` 聚合返回，返回值不包含密码、RDP 启动地址等敏感字段。
- 自动释放由服务函数 `auto_release_all_occupied_environments()` 提供给定时任务管理模块直接 import 调用，不暴露 HTTP API。该函数只释放占用中的环境，保留等待队列，记录 `auto_release/自动释放` 操作，操作人为空表示系统操作，并通知队首用户可手动占用。

## API

后端路由前缀：`/api/environment-management`

- `GET /environments`：环境列表，返回账号、BOMID、环境资产编号、设备实例、队列状态、收藏状态和 RDP 启动 URL；不返回密码。
  - 兼容旧查询：`domain`、`category`、`project_name`、`vehicle_model`、`keyword`、`favorite_only`。
  - 表头筛选查询：`domains`、`categories`、`statuses`、`favorite_state`、`queue_state`、`device_ids`、`ip_address`、`account`、`bomid`、`project_name`、`vehicle_model`、`device_keyword`、`current_user_name`、`asset_number`、`config_description`、`remark`、`shelf_location`、`updated_start`、`updated_end`。
- `POST /environments`、`PUT /environments/{id}`、`DELETE /environments/{id}`：管理端 CRUD，仅环境管理员可用。
- `POST|DELETE /environments/{id}/favorite`：收藏或取消收藏。
- `POST /environments/{id}/occupy`：占用，仅环境用户和管理员可用；成功后前端才触发 RDP。
- `POST /environments/{id}/release`：释放，当前占用环境用户或管理员可用。
- `POST /environments/{id}/queue`：排队，仅环境用户和管理员可用。
- `POST /environments/{id}/jump-queue`：插队接口保留，当前前端隐藏。
- `DELETE /environments/{id}/queue/me`：取消自己的排队。
- `GET /environments/{id}/queue`：查看队列。
- `GET /environments/{id}/records`：查看操作记录，支持 `page` 和 `pageSize` 分页参数。
- `GET /device-types`、`POST /device-types`、`PUT /device-types/{id}`、`DELETE /device-types/{id}`：测试设备类型树管理，仅环境管理员可用。
- `GET /devices`、`POST /devices`、`PUT /devices/{id}`、`DELETE /devices/{id}`：测试设备主数据管理接口，仅环境管理员可用。
  - `GET /devices` 兼容旧查询 `device_type_id`、`keyword`、`active_only`。
  - 表头筛选查询：`device_type_ids`、`name`、`type_keyword`、`is_active_values`、`remark`。
- `GET /device-options`：测试设备级联选项，类型节点作为路径容器，具体设备叶子用于环境实例选择。
- `GET /filter-options`：环境管理筛选选项，返回领域、分类、状态、收藏状态、排队状态、项目、车型、测试设备级联树、占用人、设备类型、设备启用状态等选项。
- `GET /announcement`：读取环境操作公告。
- `PUT /announcement`：保存环境操作公告，仅环境管理员可用。

内部定时任务接口：

```python
from apps.environment_management.services import auto_release_all_occupied_environments

result = auto_release_all_occupied_environments()
# result: {"released_count": 2, "environment_ids": ["..."]}
```

该函数用于每日凌晨自动释放仍处于占用状态的环境，不取消排队、不自动转交，通知失败不会回滚释放结果。

`EnvironmentIn.devices` 示例：

```json
[
  {
    "device_id": "测试设备ID",
    "asset_number": "DEV-ASSET-001",
    "remark": "接在 1 号工位",
    "sort": 0
  }
]
```

`EnvironmentOut.devices` 返回设备实例明细；`device_display` 仅由测试设备名称拼接，不包含类型路径和资产编号。

## 前端页面

- `/environment-management/admin`：管理端。
  - 使用 Tab 分为“环境管理”“测试设备管理”“公告配置”。
  - 环境管理使用 `zq-table`，表格列定义放在 `admin/data.ts`。
  - 环境管理表格不再使用顶部搜索表单；IP、账号、BOMID、领域、分类、项目、车型、测试设备、配置情况、环境资产编号、备注、货架位置、状态、占用人和更新时间都通过表头筛选触发服务端分页查询。
  - 项目、车型、占用人使用关键词模糊搜索；测试设备使用多级级联多选，最终按具体测试设备 ID 查询。
  - 环境表单支持维护 BOMID、环境资产编号和测试设备实例列表。
  - 测试设备管理 Tab 左侧维护类型树，右侧维护该类型下的具体测试设备主数据。
  - 测试设备表格同样使用表头筛选；左侧类型树点击是快捷筛选，和表头“类型路径”等条件共同生效。
  - 公告配置支持标题、启用开关和富文本内容。
- `/environment-management/user`：用户端。
  - 列表模式使用 `zq-table`，表格列定义放在 `user/data.ts`。
  - 列表模式下收藏、IP、账号、BOMID、领域、分类、项目、车型、测试设备、占用情况、占用人和排队状态都在表头筛选；顶部只保留刷新、视图切换和清空筛选等工具。
  - 项目、车型、占用人使用关键词模糊搜索；测试设备使用多级级联多选，避免大量设备平铺造成选择困难。
  - 平铺模式没有表头，使用工具栏“筛选”按钮打开同一套筛选条件，和列表模式共享筛选状态。
  - 平铺模式使用宽卡片布局，聚焦 IP、状态、占用人、排队人数、项目车型、BOMID、设备名称和关键操作。
  - 账号列只显示账号；密码不显示且后端不下发。
  - 操作列包含占用、释放、排队、取消排队、详情、队列和记录。插队按钮隐藏。
  - 详情抽屉封装在 `user/components/EnvironmentDetailDrawer.vue`，使用 `ZqDrawer`。抽屉内设备明细是当前 DTO 的静态详情矩阵，不做分页 CRUD，因此允许使用小型 Element Plus 表格作为 zq-table 例外。
  - 占用成功后调用 `openRdp(result.environment)`，使用 `rdp_launcher_url` 打开 Focus RDP 协议。

## RDP 客户端安装

- 前端提供脚本 `/tools/focus-rdp/install-focus-rdp-protocol.ps1`。
- Windows 用户首次运行该脚本后，会在当前用户注册 `focus-rdp` URL Protocol。
- 协议处理器会校验 `host` 只包含主机名/IP 允许字符，然后执行 `mstsc.exe /v:<host>`。
- 协议处理器不读取、不保存、不传递环境账号密码；RDP 凭据仍由用户在 Windows 远程桌面客户端中手动输入。
- 如果点击占用后浏览器提示没有注册 handler，需要重新运行安装脚本或检查 `HKCU\Software\Classes\focus-rdp` 注册项。

## 后续维护约定

后续任何环境管理模块改动都需要同步更新本文档，至少补充：

- 角色或权限变化。
- 队列、占用、释放规则变化。
- 数据模型字段或迁移变化。
- API 入参、出参或安全策略变化。
- 前端用户交互变化。
