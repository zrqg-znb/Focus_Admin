export interface FocusDocLink {
  label: string;
  link: string;
}

export type FocusModuleGroup =
  | 'command'
  | 'delivery'
  | 'quality'
  | 'intelligence';

export interface FocusModuleMeta {
  slug: string;
  title: string;
  titleEn: string;
  aliases: string[];
  summary: string;
  tagline: string;
  highlights: string[];
  audience: string[];
  backendPrefixes: string[];
  frontendRoutes: string[];
  apiFiles: string[];
  viewDirs: string[];
  relatedDocs: FocusDocLink[];
  group: FocusModuleGroup;
  order: number;
}

export const focusModuleGroupLabels: Record<FocusModuleGroup, string> = {
  command: '统筹与协同',
  delivery: '交付与验证',
  intelligence: '智能审计',
  quality: '质量与性能',
};

export const focusModules: FocusModuleMeta[] = [
  {
    slug: 'dashboard',
    title: '工作台 / 仪表盘',
    titleEn: 'Dashboard',
    aliases: ['dashboard', 'workspace', 'analytics', '工作台', '仪表盘'],
    summary:
      '聚合项目、需求、质量、性能与风险信号，作为 Focus 的统一观测入口和日常操作起点。',
    tagline: '登录后的第一屏，负责把“当前最需要处理的事情”推到前面。',
    highlights: [
      '聚合项目、需求、性能与质量摘要，缩短角色切换成本',
      '工作台按项目与个人职责展示待办、风险与收藏视图',
      '为项目管理、性能监控和质量模块提供跨模块入口',
    ],
    audience: ['项目经理', '研发负责人', '测试负责人', '平台运营人员'],
    backendPrefixes: ['/api/dashboard'],
    frontendRoutes: ['/dashboard/analytics', '/dashboard/workspace'],
    apiFiles: ['web/apps/web-ele/src/api/dashboard.ts'],
    viewDirs: ['web/apps/web-ele/src/views/dashboard'],
    relatedDocs: [
      { label: '前端页面参考', link: '/frontend/views/dashboard' },
      { label: '系统架构', link: '/overview/architecture' },
    ],
    group: 'command',
    order: 1,
  },
  {
    slug: 'project-manager',
    title: '项目管理',
    titleEn: 'Project Manager',
    aliases: ['project-manager', 'project manager', '项目管理'],
    summary:
      '以项目为聚合根，管理里程碑、迭代、代码质量、DTS、周报和硬件配置等多条交付主线。',
    tagline: 'Focus 的核心业务域，用一套项目主数据把交付节奏和质量信号串起来。',
    highlights: [
      '项目、迭代、里程碑、报告等子域围绕项目主数据协同',
      '支持质量记录、DTS 统计、需求看板和硬件配置等扩展能力',
      '前端按子域拆分页面与 API 文件，方便渐进扩展',
    ],
    audience: ['项目经理', '交付经理', '开发经理', '质量负责人'],
    backendPrefixes: ['/api/project-manager'],
    frontendRoutes: [
      '/project-manager/project',
      '/project-manager/iteration',
      '/project-manager/milestone',
      '/project-manager/code-quality',
      '/project-manager/report',
    ],
    apiFiles: [
      'web/apps/web-ele/src/api/project-manager/project.ts',
      'web/apps/web-ele/src/api/project-manager/iteration.ts',
      'web/apps/web-ele/src/api/project-manager/milestone.ts',
      'web/apps/web-ele/src/api/project-manager/code_quality.ts',
      'web/apps/web-ele/src/api/project-manager/report.ts',
    ],
    viewDirs: ['web/apps/web-ele/src/views/project-manager'],
    relatedDocs: [
      { label: '后端技术参考', link: '/backend/apps/project-manager' },
      { label: '前端页面参考', link: '/frontend/views/project-manager' },
    ],
    group: 'command',
    order: 2,
  },
  {
    slug: 'performance',
    title: '性能监控',
    titleEn: 'Performance Monitor',
    aliases: ['performance', 'performance-monitor', '性能监控', '性能指标'],
    summary:
      '围绕指标定义、数据导入、趋势看板和风险记录，建立性能基线与异常处置闭环。',
    tagline: '这里的 performance 指性能监控，不是绩效管理。',
    highlights: [
      '支持指标树、芯片类型、项目与模块的多维筛选',
      '提供指标导入任务、数据上传、趋势分析与风险确认流程',
      '前端已拆出配置、看板与风险视图，适合持续演进',
    ],
    audience: ['性能测试工程师', '平台负责人', '项目经理'],
    backendPrefixes: ['/api/performance'],
    frontendRoutes: [
      '/performance/config',
      '/performance/dashboard',
      '/performance/risk',
    ],
    apiFiles: ['web/apps/web-ele/src/api/core/performance.ts'],
    viewDirs: ['web/apps/web-ele/src/views/performance'],
    relatedDocs: [
      { label: '后端技术参考', link: '/backend/apps/performance' },
      { label: '前端页面参考', link: '/frontend/views/performance' },
    ],
    group: 'quality',
    order: 4,
  },
  {
    slug: 'code-compliance',
    title: '代码合规',
    titleEn: 'Code Compliance',
    aliases: ['code-compliance', 'code compliance', '代码合规'],
    summary:
      '保留旧 Excel 风险台账，同时维护组织、代码库、分支和绑定关系，并通过数据湖同步识别漏合风险。',
    tagline:
      '先把代码库主数据看护起来，再用自动检测把主干和发布分支的 CR 差异照出来。',
    highlights: [
      '旧风险概览、详情和 Excel 上传入口继续保留',
      '新增代码库管理页，左侧组织树、右侧代码库列表',
      '新增分支管理页，支持分支 CRUD 和批量绑定代码库',
      '新增漏合风险页，支持手动同步、详情查看和状态处理',
      '代码仓类型来自 core 字典，责任领域绑定 core PL 组',
    ],
    audience: ['CIE', '代码治理负责人', '项目技术负责人'],
    backendPrefixes: ['/api/code-compliance'],
    frontendRoutes: [
      '/compliance/overview',
      '/compliance/detail',
      '/compliance/repository',
      '/compliance/branch',
      '/compliance/missing-merge',
    ],
    apiFiles: [
      'web/apps/web-ele/src/api/compliance/index.ts',
      'web/apps/web-ele/src/api/compliance/base.ts',
      'web/apps/web-ele/src/api/compliance/missing-merge.ts',
    ],
    viewDirs: ['web/apps/web-ele/src/views/compliance'],
    relatedDocs: [
      { label: '后端技术参考', link: '/backend/apps/code-compliance' },
      { label: '前端页面参考', link: '/frontend/views/code-compliance' },
    ],
    group: 'quality',
    order: 5,
  },
  {
    slug: 'code-scan',
    title: '代码扫描',
    titleEn: 'Code Scan',
    aliases: ['code-scan', 'code scan', '代码扫描'],
    summary:
      '负责扫描任务编排、项目配置、结果汇总和审计日志，是静态分析与任务执行的基础能力层。',
    tagline: '偏执行平台属性，承接“扫什么、怎么扫、扫完怎么看”的完整链路。',
    highlights: [
      '支持扫描项目、扫描任务、结果聚合与任务日志查询',
      '和 DeepAudit、代码合规模块共享扫描基础设施与项目配置',
      '前端按项目、任务、结果、审计等页面拆分，便于角色分工',
    ],
    audience: ['测试平台工程师', '安全工程师', '代码治理负责人'],
    backendPrefixes: ['/api/code-scan'],
    frontendRoutes: [
      '/code_scan/project',
      '/code_scan/audit',
      '/code_scan/result',
      '/code_scan/task-log',
    ],
    apiFiles: ['web/apps/web-ele/src/api/code_scan/index.ts'],
    viewDirs: ['web/apps/web-ele/src/views/code_scan'],
    relatedDocs: [
      { label: '后端技术参考', link: '/backend/apps/code-scan' },
      { label: '前端页面参考', link: '/frontend/views/code-scan' },
    ],
    group: 'quality',
    order: 6,
  },
  {
    slug: 'delivery-matrix',
    title: '交付矩阵',
    titleEn: 'Delivery Matrix',
    aliases: ['delivery-matrix', 'delivery matrix', '交付矩阵'],
    summary:
      '用统一矩阵视图管理项目交付项、状态和责任边界，突出阶段性交付风险与整体进度。',
    tagline: '适合横向看项目群交付状态，而不是只看单项目局部进展。',
    highlights: [
      '聚合交付维度、状态和责任信息，支持管理端总览',
      '强调横向对比和阶段卡点，便于管理视角快速发现异常',
      '通常与项目管理、集成报告等模块联动使用',
    ],
    audience: ['交付经理', '项目群管理者', '部门负责人'],
    backendPrefixes: ['/api/delivery-matrix'],
    frontendRoutes: ['/delivery-matrix/dashboard', '/delivery-matrix/admin'],
    apiFiles: ['web/apps/web-ele/src/api/delivery-matrix/index.ts'],
    viewDirs: ['web/apps/web-ele/src/views/delivery-matrix'],
    relatedDocs: [
      { label: '后端技术参考', link: '/backend/apps/delivery-matrix' },
      { label: '前端页面参考', link: '/frontend/views/delivery-matrix' },
    ],
    group: 'delivery',
    order: 7,
  },
  {
    slug: 'integration-report',
    title: '集成报告',
    titleEn: 'Integration Report',
    aliases: ['integration-report', 'integration report', '集成报告'],
    summary:
      '管理集成项目配置、采集任务、订阅状态和邮件投递历史，负责外部数据进入 Focus 的报告链路。',
    tagline: '把离散的集成数据转成可订阅、可追踪的项目报告服务。',
    highlights: [
      '支持配置初始化、模拟采集、历史查询与投递日志',
      '强调“配置 + 采集 + 通知”闭环，而非单次报表导出',
      '适合承接外部系统数据汇总与周期性播报场景',
    ],
    audience: ['项目 PMO', '集成负责人', '平台运营人员'],
    backendPrefixes: ['/api/integration-report'],
    frontendRoutes: [
      '/integration-report/config',
      '/integration-report/history',
      '/integration-report/subscription',
      '/integration-report/email-logs',
    ],
    apiFiles: ['web/apps/web-ele/src/api/integration-report/index.ts'],
    viewDirs: ['web/apps/web-ele/src/views/integration-report'],
    relatedDocs: [
      { label: '后端技术参考', link: '/backend/apps/integration-report' },
      { label: '前端页面参考', link: '/frontend/views/integration-report' },
    ],
    group: 'delivery',
    order: 7,
  },
  {
    slug: 'auto-test-report',
    title: '自动化测试报告',
    titleEn: 'Auto Test Report',
    aliases: ['auto-test-report', 'auto test report', '自动化测试报告'],
    summary:
      '用于管理自动化测试的座舱 / 车控双领域主数据、测试用例和日报结果，构建从平台配置到结果沉淀的测试报表链路。',
    tagline:
      '同一模块内切换座舱与车控视图，分别承接 MCU 平台与 VIU 维度的数据看护。',
    highlights: [
      '支持座舱 / 车控双领域切换，前端视图与路由状态保持同步',
      '车控车型可配置 VIU0~VIU4 的子集，用例与上报按 VIU 编号解析',
      '支持模板下载、批量导入、日报汇总和历史异常原因复用',
      '适合与集成报告、交付矩阵共同呈现验证状态',
    ],
    audience: ['测试经理', '自动化测试工程师', '验证负责人'],
    backendPrefixes: ['/api/auto-test-report'],
    frontendRoutes: [
      '/auto-test-report/vehicle-config',
      '/auto-test-report/test-cases',
      '/auto-test-report/daily-results',
    ],
    apiFiles: ['web/apps/web-ele/src/api/auto-test-report/index.ts'],
    viewDirs: ['web/apps/web-ele/src/views/auto-test-report'],
    relatedDocs: [
      { label: '后端技术参考', link: '/backend/apps/auto-test-report' },
      { label: '前端页面参考', link: '/frontend/views/auto-test-report' },
    ],
    group: 'delivery',
    order: 8,
  },
  {
    slug: 'failure-mode',
    title: '故障模式',
    titleEn: 'Failure Mode',
    aliases: ['failure-mode', 'failure mode', '故障模式'],
    summary:
      '围绕故障模式库、处理工作流、统计分析和基础配置，沉淀质量问题的知识资产与闭环流程。',
    tagline: '既是问题库，也是流程平台，强调从识别到处置再到统计复盘。',
    highlights: [
      '支持故障模式条目、任务流转、角色与产品线配置',
      '前端以抽屉、详情和统计看板支撑复杂信息维护',
      '可与项目管理、DeepAudit形成问题治理联动',
    ],
    audience: ['质量工程师', '测试负责人', '问题分析人员'],
    backendPrefixes: ['/api/failure-mode'],
    frontendRoutes: [
      '/failure-mode',
      '/failure-mode/workflow',
      '/failure-mode/statistics',
    ],
    apiFiles: [
      'web/apps/web-ele/src/api/failure_mode.ts',
      'web/apps/web-ele/src/api/failure_mode_workflow.ts',
    ],
    viewDirs: ['web/apps/web-ele/src/views/failure-mode'],
    relatedDocs: [
      { label: '后端技术参考', link: '/backend/apps/failure-mode' },
      { label: '前端页面参考', link: '/frontend/views/failure-mode' },
    ],
    group: 'delivery',
    order: 9,
  },
  {
    slug: 'deepaudit',
    title: 'DeepAudit 智能审计',
    titleEn: 'DeepAudit',
    aliases: ['deepaudit', 'deep audit', '智能审计', '大模型审计'],
    summary:
      '基于 LLM、RAG 和多智能体编排构建的智能审计系统，用于代码安全分析、漏洞解释和修复建议生成。',
    tagline: 'Focus 中最智能化的一块，连接扫描基础设施、知识库和流式任务执行。',
    highlights: [
      '覆盖项目配置、扫描任务、规则模板、知识库和 Agent 任务',
      '支持多模型接入、流式输出和结构化审计结果沉淀',
      '既是独立业务模块，也是平台级智能能力中心',
    ],
    audience: ['安全工程师', '架构师', '平台研发', '技术管理者'],
    backendPrefixes: ['/api/deepaudit'],
    frontendRoutes: ['/deepaudit/dashboard', '/deepaudit/project'],
    apiFiles: ['web/apps/web-deepaudit/src/shared/utils/apiInterceptor.ts'],
    viewDirs: ['web/apps/web-deepaudit/src'],
    relatedDocs: [
      {
        label: '使用指南（精简版）',
        link: '/modules/deepaudit-user-guide-quick',
      },
      { label: '使用指南（完整版）', link: '/modules/deepaudit-user-guide' },
      { label: '后端技术参考', link: '/backend/apps/deepaudit' },
      { label: '系统架构', link: '/overview/architecture' },
    ],
    group: 'intelligence',
    order: 11,
  },
].sort((left, right) => left.order - right.order);

export function getFocusModule(slug: string) {
  const module = focusModules.find((item) => item.slug === slug);

  if (!module) {
    throw new Error(`Unknown Focus module: ${slug}`);
  }

  return module;
}

export function getFocusModulesByGroup(group: FocusModuleGroup) {
  return focusModules.filter((item) => item.group === group);
}
