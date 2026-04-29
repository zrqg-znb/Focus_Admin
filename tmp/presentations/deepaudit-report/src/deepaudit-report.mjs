import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  Presentation,
  PresentationFile,
  row,
  column,
  layers,
  panel,
  text,
  shape,
  rule,
} from '/Users/zrq/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs';
import {
  paint,
  stroke,
  textStyle,
} from '/Users/zrq/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/presentation-jsx/index.mjs';

const WORKSPACE = '/Users/zrq/CodeSpace/PythonProjects/Focus_Admin/tmp/presentations/deepaudit-report';
const OUTPUT_DIR = path.join(WORKSPACE, 'output');
const SCRATCH_DIR = path.join(WORKSPACE, 'scratch');
const PREVIEW_DIR = path.join(SCRATCH_DIR, 'preview');
const PPTX_PATH = path.join(OUTPUT_DIR, 'output.pptx');

const W = 1280;
const H = 720;

const ASSETS = {
  home: await fs.readFile(path.join(SCRATCH_DIR, 'assets', 'deepaudit-home.png')),
  report: await fs.readFile(path.join(SCRATCH_DIR, 'assets', 'deepaudit-report.png')),
};

const FONT_SANS = '"PingFang SC"';
const FONT_MONO = '"Menlo"';

const C = {
  bg: '#0b0d12',
  bg2: '#101520',
  panel: '#121824',
  panel2: '#171d2a',
  line: '#273042',
  lineSoft: 'rgba(141,153,173,0.22)',
  text: '#f5f7fb',
  muted: '#a0a9ba',
  faint: '#6b7384',
  accent: '#ff6a2a',
  accentSoft: 'rgba(255,106,42,0.14)',
  accentLine: 'rgba(255,106,42,0.42)',
  accentGlow: 'rgba(255,106,42,0.18)',
  green: '#61d98f',
  cyan: '#5ccfe6',
  warm: '#f7c66b',
};

const S = {
  kicker: `font: 15px ${FONT_MONO}; weight: 700; color: ${C.accent}; wrap: none;`,
  coverLead: `font: 16px ${FONT_MONO}; weight: 700; color: ${C.accent}; wrap: none;`,
  coverTitleA: `font: 66px ${FONT_MONO}; weight: 700; color: ${C.accent}; wrap: none;`,
  coverTitleB: `font: 54px ${FONT_SANS}; weight: 700; color: ${C.text}; wrap: none;`,
  coverSubtitle: `font: 22px ${FONT_SANS}; weight: 500; color: ${C.muted};`,
  coverMeta: `font: 15px ${FONT_MONO}; weight: 700; color: ${C.muted}; wrap: none;`,
  title: `font: 46px ${FONT_SANS}; weight: 700; color: ${C.text};`,
  titleSmall: `font: 38px ${FONT_SANS}; weight: 700; color: ${C.text};`,
  subtitle: `font: 19px ${FONT_SANS}; weight: 500; color: ${C.muted};`,
  body: `font: 17px ${FONT_SANS}; weight: 500; color: ${C.text};`,
  bodyMuted: `font: 17px ${FONT_SANS}; weight: 500; color: ${C.muted};`,
  bodySmall: `font: 15px ${FONT_SANS}; weight: 500; color: ${C.muted};`,
  mono: `font: 15px ${FONT_MONO}; weight: 500; color: ${C.text}; wrap: none;`,
  monoMuted: `font: 15px ${FONT_MONO}; weight: 500; color: ${C.muted}; wrap: none;`,
  monoTiny: `font: 13px ${FONT_MONO}; weight: 500; color: ${C.muted}; wrap: none;`,
  stageNum: `font: 32px ${FONT_MONO}; weight: 700; color: ${C.accent}; wrap: none;`,
  stageTitle: `font: 26px ${FONT_SANS}; weight: 700; color: ${C.text};`,
  sectionTiny: `font: 14px ${FONT_MONO}; weight: 700; color: ${C.accent}; wrap: none;`,
  sectionLarge: `font: 44px ${FONT_SANS}; weight: 700; color: ${C.text};`,
  metricValue: `font: 40px ${FONT_MONO}; weight: 700; color: ${C.text}; wrap: none;`,
  metricLabel: `font: 16px ${FONT_SANS}; weight: 500; color: ${C.muted};`,
  routePath: `font: 15px ${FONT_MONO}; weight: 700; color: ${C.text}; wrap: none;`,
  routeDesc: `font: 14px ${FONT_SANS}; weight: 500; color: ${C.muted};`,
  note: `font: 14px ${FONT_SANS}; weight: 500; color: ${C.muted};`,
  callout: `font: 18px ${FONT_SANS}; weight: 600; color: ${C.text};`,
  calloutMuted: `font: 16px ${FONT_SANS}; weight: 500; color: ${C.muted};`,
};

function tx(value, style, opts = {}) {
  return text(value, { ...opts, style: textStyle(style) });
}

function slug(label) {
  return String(label)
    .trim()
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 64) || 'item';
}

function notes(slide, content) {
  if (slide?.speakerNotes?.setText) {
    slide.speakerNotes.setText(content);
  }
}

function bullet(textValue, detail = '', accent = C.accent) {
  const parts = [
    shape({
      name: `bullet-dot-${slug(textValue)}`,
      geometry: 'ellipse',
      width: 8,
      height: 8,
      fill: paint(accent),
      line: stroke('none'),
    }),
    column({ name: `bullet-copy-${slug(textValue)}`, gap: 4, width: 'fill' }, [
      tx(textValue, S.body, { name: `bullet-title-${slug(textValue)}`, width: 'fill' }),
      detail ? tx(detail, S.bodySmall, { name: `bullet-detail-${slug(textValue)}`, width: 'fill' }) : null,
    ].filter(Boolean)),
  ];

  return row({ name: `bullet-row-${slug(textValue)}`, gap: 12, align: 'start', width: 'fill' }, parts);
}

function chip(label, { accent = false } = {}) {
  const fillColor = accent ? C.accentSoft : 'rgba(255,255,255,0.04)';
  const lineColor = accent ? C.accentLine : 'rgba(255,255,255,0.10)';
  const textColor = accent ? C.accent : C.text;
  return panel(
    {
      name: `chip-${slug(label)}`,
      padding: [7, 12],
      fill: paint(fillColor),
      line: stroke(`1px ${lineColor}`),
      align: 'center',
      justify: 'center',
    },
    tx(label, `font: 14px ${FONT_MONO}; weight: 700; color: ${textColor}; wrap: none;`, { name: `chip-text-${slug(label)}` })
  );
}

function chipGrid(rows, { gap = 8, rowGap = 8, name = 'chip-grid' } = {}) {
  return column(
    { name, gap: rowGap, width: 'fill', align: 'start' },
    rows.map((labels, idx) =>
      row(
        { name: `${name}-row-${idx + 1}`, gap, width: 'fill', align: 'start' },
        labels.map((item) => (typeof item === 'string' ? chip(item) : chip(item.label, item.options)))
      )
    )
  );
}

function sectionHeader(kicker, title, subtitleText = '') {
  return column({ name: `header-${slug(title)}`, gap: 10, width: 'fill' }, [
    tx(kicker, S.kicker, { name: `header-kicker-${slug(title)}` }),
    tx(title, S.title, { name: `header-title-${slug(title)}`, width: 'fill' }),
    subtitleText ? tx(subtitleText, S.subtitle, { name: `header-subtitle-${slug(title)}`, width: 'fill' }) : null,
  ].filter(Boolean));
}

function stageColumn(num, title, details) {
  return column({ name: `stage-${num}-${slug(title)}`, gap: 10, width: 262, align: 'start' }, [
    tx(num, S.stageNum, { name: `stage-num-${num}` }),
    tx(title, S.stageTitle, { name: `stage-title-${slug(title)}` }),
    rule({ name: `stage-rule-${slug(title)}`, width: 160, weight: 2, stroke: C.accentLine }),
    ...details.map((detail, idx) => bullet(detail.title, detail.desc, detail.accent || C.accent)),
  ]);
}

function flowNode(title, subtitle, label, accent = false) {
  return panel(
    {
      name: `flow-node-${slug(title)}`,
      width: 176,
      padding: [14, 14, 16, 14],
      fill: paint(accent ? 'rgba(255,106,42,0.10)' : 'rgba(255,255,255,0.03)'),
      line: stroke(`1px ${accent ? 'rgba(255,106,42,0.35)' : 'rgba(255,255,255,0.12)'}`),
      align: 'start',
      justify: 'start',
    },
    column({ name: `flow-node-copy-${slug(title)}`, gap: 6, width: 'fill' }, [
      tx(label, `font: 13px ${FONT_MONO}; weight: 700; color: ${accent ? C.accent : C.muted}; wrap: none;`, { name: `flow-node-label-${slug(title)}` }),
      tx(title, `font: 23px ${FONT_SANS}; weight: 700; color: ${C.text};`, { name: `flow-node-title-${slug(title)}` }),
      tx(subtitle, `font: 14px ${FONT_SANS}; weight: 500; color: ${C.muted};`, { name: `flow-node-subtitle-${slug(title)}` }),
    ])
  );
}

function headingUnderline(width = 160) {
  return rule({ name: 'heading-underline', width, weight: 2, stroke: C.accentLine });
}

function metricPlaceholder(label) {
  return column({ name: `metric-${slug(label)}`, gap: 8, width: 164, align: 'start' }, [
    tx('—', S.metricValue, { name: `metric-value-${slug(label)}` }),
    tx(label, S.metricLabel, { name: `metric-label-${slug(label)}` }),
    tx('待补真实值', S.monoTiny, { name: `metric-note-${slug(label)}` }),
  ]);
}

function routeItem(pathText, descText) {
  return column({ name: `route-${slug(pathText)}`, gap: 4, width: 'fill', align: 'start' }, [
    tx(pathText, S.routePath, { name: `route-path-${slug(pathText)}` }),
    tx(descText, S.routeDesc, { name: `route-desc-${slug(pathText)}` }),
  ]);
}

function apiItem(pathText, descText) {
  return column({ name: `api-${slug(pathText)}`, gap: 4, width: 'fill' }, [
    tx(pathText, S.routePath, { name: `api-path-${slug(pathText)}` }),
    tx(descText, S.routeDesc, { name: `api-desc-${slug(pathText)}` }),
  ]);
}

function buildCover(slide) {
  slide.background.fill = paint(C.bg);
  slide.images.add({
    blob: ASSETS.home,
    contentType: 'image/png',
    position: { left: 0, top: 0, width: W, height: H },
    fit: 'cover',
  });
  slide.compose(
    layers({ name: 'cover-root', width: W, height: H, alignItems: 'stretch', justifyItems: 'stretch' }, [
      shape({
        name: 'cover-scrim',
        geometry: 'rect',
        width: 520,
        height: H,
        fill: paint('rgba(7,9,14,0.80)'),
        line: stroke('none'),
      }),
      shape({
        name: 'cover-glow',
        geometry: 'ellipse',
        width: 340,
        height: 340,
        fill: paint(C.accentGlow),
        line: stroke('none'),
      }),
      column({
        name: 'cover-copy',
        width: 460,
        gap: 18,
        padding: [72, 0, 60, 66],
        align: 'start',
        justify: 'start',
      }, [
        tx('部门汇报 · 15 分钟', S.coverLead, { name: 'cover-lead' }),
        tx('DeepAudit', S.coverTitleA, { name: 'cover-title-a' }),
        tx('智能审计平台', S.coverTitleB, { name: 'cover-title-b' }),
        tx('LLM + RAG + 多智能体，把“项目接入 → 分析 → 验证 → 报告”做成闭环', S.coverSubtitle, { name: 'cover-subtitle', width: 420 }),
        headingUnderline(180),
        row({ name: 'cover-tags', gap: 10, width: 'fill', align: 'start' }, [
          chip('项目演示', { accent: true }),
          chip('架构设计'),
          chip('实现方法'),
        ]),
        tx('Focus 平台内的独立智能审计子系统', S.coverMeta, { name: 'cover-meta' }),
      ]),
    ])
  );
  notes(slide, `今天我汇报的是 DeepAudit 智能审计平台。先给一个结论：它已经不是单点扫描工具，而是一套把“项目接入、分析、验证、报告交付”串成闭环的审计平台。

今天我会从四个部分展开：为什么要做、现在已经做成了什么、背后的架构和实现方法，以及现场怎么演示。整场汇报我会尽量少讲概念，多讲结果和能力，也会把现场演示和技术实现对应起来，方便大家更直观地看到 DeepAudit 已经具备的完整链路。`);
}

function buildWhy(slide) {
  slide.background.fill = paint(C.bg);
  slide.compose(
    column({ name: 'why-root', width: W, height: H, padding: 56, gap: 16, align: 'start' }, [
      sectionHeader('WHY DEEPAUDIT', '为什么要做 DeepAudit', '传统扫描能找问题，但很难解释、很难验证、也很难形成可复用的交付。'),
      headingUnderline(220),
      row({ name: 'why-body', width: 'fill', gap: 34, align: 'start' }, [
        column({ name: 'why-left', width: 380, gap: 18, align: 'start' }, [
          tx('定位不是“再做一个扫描器”，而是把审计变成一套可运行的工作台。', S.body, { name: 'why-statement', width: 360 }),
          rule({ name: 'why-rule', width: 160, weight: 2, stroke: C.accentLine }),
          bullet('规则固定', '只能覆盖已知模式，面对复杂业务和组合风险时容易失焦。'),
          bullet('解释弱', '发现结果碎片化，难以让领导和研发快速判断优先级。', C.warm),
          bullet('验证弱', '缺少动态验证、PoC 和回放，结论往往停留在“发现”而不是“落地”。', C.green),
        ]),
        column({ name: 'why-right', width: 'fill', gap: 10, align: 'start' }, [
          tx('DeepAudit 的目标', S.sectionTiny, { name: 'why-target-kicker' }),
          tx('把“项目接入 → 分析 → 验证 → 报告”串成闭环。', S.titleSmall, { name: 'why-target-title', width: 640 }),
          tx('它不是单点工具，而是面向部门内部审计流程的智能审计工作台。', S.subtitle, { name: 'why-target-subtitle', width: 640 }),
          row({ name: 'why-compare', gap: 12, width: 'fill', align: 'start' }, [
            column({ name: 'why-compare-left', gap: 8, width: 282, align: 'start' }, [
              tx('传统方式', S.coverMeta, { name: 'why-trad' }),
              bullet('扫描结果多', '但上下文弱。'),
              bullet('问题能发现', '但无法统一解释。'),
              bullet('报告能导出', '但不能形成审计闭环。'),
            ]),
            column({ name: 'why-compare-right', gap: 8, width: 282, align: 'start' }, [
              tx('DeepAudit', S.coverMeta, { name: 'why-deepaudit' }),
              bullet('接入与权限统一', '仓库 / ZIP / 成员 / 回收站 / 角色一体化。', C.accent),
              bullet('分析过程可观测', 'thinking、tool、finding、checkpoint 全程回传。', C.green),
              bullet('动态沙箱验证', 'LLM 生成 PoC 并在隔离环境中验证，降低误报。', C.warm),
              bullet('结果可交付', '报告页、PDF / JSON 导出、Dashboard 可直接演示。', C.cyan),
            ]),
          ]),
        ]),
      ]),
    ])
  );
  notes(slide, `我们之所以做 DeepAudit，核心原因是传统扫描工具虽然能发现问题，但普遍存在三个短板：第一，结果解释弱，很多时候只能告诉你“有问题”，但不能很好地说明“为什么是问题”；第二，验证弱，很多发现停留在静态扫描层面，缺少动态验证和上下文判断；第三，交付弱，结果往往碎片化，难以直接形成标准化报告，也不利于复盘和沉淀。

所以 DeepAudit 的定位不是“再做一个扫描器”，而是把审计升级成一个可运行、可追踪、可复用的工作台。它要解决的不是单次发现，而是把项目接入之后的分析、验证和报告形成一个完整闭环，让审计结果真正能用于汇报、留档和后续治理。换句话说，DeepAudit 的价值不是多扫几个漏洞，而是把安全审计从“工具输出”变成“流程化交付”。`);
}

function buildPanorama(slide) {
  slide.background.fill = paint(C.bg);
  slide.compose(
    column({ name: 'panorama-root', width: W, height: H, padding: 56, gap: 18, align: 'start' }, [
      sectionHeader('FEATURE PANORAMA', '现有功能与对象分工', '已经形成“接入—分析—治理—交付”的完整链路，并围绕项目、任务、策略、知识和报告对象化管理。'),
      headingUnderline(240),
      row({ name: 'panorama-stages', width: 'fill', gap: 18, align: 'start' }, [
        stageColumn('01', '项目接入', [
          { title: '仓库 / ZIP / 分支', desc: '兼容仓库拉取和离线包导入，统一代码上下文。', accent: C.accent },
          { title: '成员 / 权限', desc: '项目拥有者、成员角色和页面级访问码一起控制可见性。', accent: C.warm },
          { title: '回收站 / 工作区', desc: '项目可恢复，运行时 workspace 独立准备和清理。', accent: C.green },
        ]),
        stageColumn('02', '审计能力', [
          { title: '传统扫描', desc: '仓库扫描、ZIP 扫描、即时分析三条入口并行。', accent: C.accent },
          { title: 'Agent 审计', desc: '多智能体推理、事件流、检查点和恢复机制一体化。', accent: C.cyan },
          { title: '结果聚合', desc: '问题、Finding、摘要和报告统一收束。', accent: C.warm },
        ]),
        stageColumn('03', '策略治理', [
          { title: '规则集 / 规则', desc: '规则粒度、适用范围和命中策略可配置。', accent: C.accent },
          { title: '提示词模板', desc: '把模型交互方式固化成可复用模板。', accent: C.green },
          { title: 'RAG / 系统配置', desc: '知识库、LLM、Embedding、SSH 和系统参数统一治理。', accent: C.cyan },
        ]),
        stageColumn('04', '结果交付', [
          { title: 'Dashboard', desc: '总览、最近项目、任务统计和运行状态。', accent: C.accent },
          { title: '任务详情', desc: '问题定位、过程回放、阶段结果统一查看。', accent: C.green },
          { title: 'PDF / JSON', desc: '输出标准化报告，适合汇报、留档和复盘。', accent: C.warm },
        ]),
      ]),
      column({ name: 'panorama-model', width: 'fill', gap: 12, align: 'start' }, [
        tx('对象模型与主链', S.sectionTiny, { name: 'panorama-model-kicker' }),
        row({ name: 'panorama-model-flow', gap: 10, width: 'fill', align: 'center' }, [
          chip('AuditProject', { accent: true }),
          tx('→', `font: 22px ${FONT_MONO}; weight: 700; color: ${C.accent}; wrap: none;`, { name: 'panorama-arrow-1' }),
          chip('AuditTask / AgentTask'),
          tx('→', `font: 22px ${FONT_MONO}; weight: 700; color: ${C.accent}; wrap: none;`, { name: 'panorama-arrow-2' }),
          chip('AuditIssue / AgentFinding'),
          tx('→', `font: 22px ${FONT_MONO}; weight: 700; color: ${C.accent}; wrap: none;`, { name: 'panorama-arrow-3' }),
          chip('AuditArtifact / Report'),
        ]),
        row({ name: 'panorama-support', gap: 8, width: 'fill', align: 'start' }, [
          chip('AuditRuleSet', { accent: true }),
          chip('PromptTemplate'),
          chip('RAG / Knowledge'),
          chip('AuditUserConfig'),
          chip('AuditSshCredential'),
        ]),
        tx('项目是上下文根对象，任务、策略、知识和报告都围绕它展开。', S.bodySmall, { name: 'panorama-note', width: 980 }),
      ]),
    ])
  );
  notes(slide, `这一页我想重点说明，DeepAudit 现在已经不是一些零散功能点，而是形成了“接入—分析—治理—交付”的完整链路。

在项目接入层面，我们支持仓库、ZIP、分支、成员、回收站等对象，项目的权限和上下文都已经可以统一管理；在审计能力层面，既支持传统扫描，也支持 Agent 审计和即时分析；在策略治理层面，规则集、提示词模板、RAG 知识库和系统配置都已经对象化管理；在结果交付层面，Dashboard、任务详情、PDF 和 JSON 报告也已经串通。

如果把它抽象成对象模型，可以理解为以 AuditProject 作为上下文根对象，下面挂着 AuditTask、AgentTask、AgentFinding、AuditArtifact、Report 这些核心对象。这样做的好处是，项目、任务、策略、知识和报告都围绕同一个主链来组织，既便于追踪，也便于回放和复用。`);
}

function buildAgentArchitecture(slide) {
  slide.background.fill = paint(C.bg);
  slide.compose(
    column({ name: 'agent-arch-root', width: W, height: H, padding: 56, gap: 18, align: 'start' }, [
      sectionHeader('MULTI-AGENT', '多智能体编排架构', '基于 LLM 的 ReAct 循环，实现动态策略适应与子领域专业化。'),
      headingUnderline(220),
      row({ name: 'agent-arch-body', width: 'fill', gap: 24, align: 'start' }, [
        column({ name: 'agent-orch', width: 350, gap: 12, align: 'start' }, [
          tx('核心大脑', S.sectionTiny),
          tx('Orchestrator 编排器', S.titleSmall),
          bullet('自主决策', 'LLM 作为系统大脑，不再是固定的规则流，而是动态调度。', C.accent),
          bullet('ReAct 循环', 'Thought (思考) → Action (派发/工具) → Observation (观察反馈)。', C.warm),
          bullet('任务交接', '通过 TaskHandoff 协议，在不同 Agent 间传递上下文与高优区域。', C.green),
        ]),
        column({ name: 'agent-subs', width: 380, gap: 12, align: 'start' }, [
          tx('专业子 Agent', S.sectionTiny),
          tx('领域专家分离', S.titleSmall),
          bullet('Recon Agent (侦察)', '收集项目结构、识别技术栈和定位高危入口点。', C.cyan),
          bullet('Analysis Agent (分析)', '挂载 SmartScan、Semgrep 等工具，进行深度漏洞挖掘。', C.accent),
          bullet('Verification Agent (验证)', '负责减少误报，生成 PoC 并在隔离沙箱中验证可利用性。', C.green),
        ]),
        column({ name: 'agent-flow', width: 'fill', gap: 12, align: 'start' }, [
          tx('动态任务流', S.sectionTiny),
          panel(
            {
              width: 'fill',
              padding: 16,
              fill: paint('rgba(255,255,255,0.03)'),
              line: stroke('1px rgba(255,255,255,0.12)'),
            },
            column({ gap: 10, width: 'fill' }, [
              tx('LLM Output 示例', S.monoMuted),
              tx('Thought: 这是一个 Django 项目，我应该先派发 Recon。', S.bodySmall),
              tx('Action: dispatch_agent', S.kicker),
              tx('Action Input: {"agent": "recon"}', S.bodySmall),
            ])
          ),
          tx('通过熔断器(Circuit Breaker)和重试机制保证协作的健壮性。', S.bodyMuted, { width: 300 }),
        ]),
      ]),
    ])
  );
  notes(slide, `这一页讲的是多智能体编排架构。DeepAudit 不是让一个大模型一把梭，而是让 Orchestrator 先做规划，再把任务拆给不同角色的 Agent 去执行。

Orchestrator 的职责是判断当前审计阶段应该先做什么，再决定是走侦察、分析还是验证。它采用的不是静态流程图，而是基于 ReAct 的循环决策：先思考，再调用工具或派发子任务，再根据观察结果继续收敛。这样做的好处是，面对不同项目、不同代码结构、不同风险类型时，系统可以动态调整策略，而不是被固定规则限制住。

下面这三个子 Agent 的分工也很清晰：Recon 负责识别项目结构、技术栈和高危入口；Analysis 负责结合工具和上下文做深层漏洞挖掘；Verification 负责减少误报，并在必要时做更进一步的验证。它们之间不是并列摆设，而是通过 TaskHandoff 协议传递上下文、证据和高优先级区域。

所以这一页的核心信息是：DeepAudit 的智能不是“一个模型说了算”，而是“编排、分工、交接、验证”共同形成的。`);
}

function buildSandboxAndTools(slide) {
  slide.background.fill = paint(C.bg);
  slide.compose(
    column({ name: 'sandbox-root', width: W, height: H, padding: 56, gap: 18, align: 'start' }, [
      sectionHeader('TOOLS & SANDBOX', '安全工具生态与沙箱验证', '集成 20+ 专业分析工具，结合隔离沙箱完成“发现到验证”的闭环。'),
      headingUnderline(240),
      row({ name: 'sandbox-body', width: 'fill', gap: 24, align: 'start' }, [
        column({ name: 'tools-col', width: 450, gap: 12, align: 'start' }, [
          tx('安全工具生态', S.sectionTiny),
          tx('内置与外部工具链', S.titleSmall),
          bullet('智能分析工具', 'SmartScanTool (推荐首选) / DataFlowAnalysisTool。', C.accent),
          bullet('外部扫描器', 'Semgrep (多语言), Bandit (Python), Gitleaks (密钥检测)。', C.cyan),
          bullet('后备方案', '工具超时或失败时(如 120s 限制)，自动降级至 PatternMatchTool。', C.warm),
          bullet('AST 语义解析', 'Tree-sitter 保留完整的函数/类语义，配合 ChromaDB 构建向量。', C.green),
        ]),
        column({ name: 'sandbox-col', width: 'fill', gap: 12, align: 'start' }, [
          tx('沙箱验证层', S.sectionTiny),
          tx('从发现到确认', S.titleSmall),
          bullet('PoC 自动生成', 'LLM 根据漏洞上下文，自动编写概念验证（Exploit/PoC）代码。', C.green),
          bullet('Docker 隔离执行', '限制网络出站、内存(512MB)、CPU，通过 seccomp 限制系统调用。', C.accent),
          bullet('置信度打分', '根据沙箱执行的 Observation，动态计算漏洞的可利用性与置信度。', C.warm),
          panel(
            {
              width: 'fill',
              padding: 16,
              fill: paint('rgba(255,106,42,0.05)'),
              line: stroke('1px rgba(255,106,42,0.2)'),
            },
            tx('验证结果使得安全报告的准确率大幅提升，真正做到“可解释、可验证”。', S.calloutMuted)
          ),
        ]),
      ]),
    ])
  );
  notes(slide, `这一页继续讲工具链和沙箱验证。DeepAudit 的思路不是只依赖模型，而是先把专业工具链接进来，用工具负责事实面的覆盖，再由模型负责解释和收敛。

工具层里，像 Semgrep、Bandit、Gitleaks、OSV-Scanner 这些外部工具先承担广覆盖扫描；同时我们也保留 AST 和代码语义能力，帮助模型更准确地理解函数、类、调用链和数据流。这样做的好处是，模型不会只看到文本片段，而是能拿到更完整的上下文。

更关键的是验证层。对于有条件进一步确认的漏洞，DeepAudit 会把上下文交给沙箱环境，自动生成 PoC 或验证逻辑，再在隔离环境中执行。这样就能把“疑似问题”往“可利用问题”推进，减少传统静态扫描里最常见的误报和歧义。

所以这一页想强调的是：DeepAudit 不是只会发现问题，而是尽量把问题确认到可解释、可验证的程度。`);
}

function buildArchitecture(slide) {
  slide.background.fill = paint(C.bg);
  slide.compose(
    column({ name: 'arch-root', width: W, height: H, padding: 56, gap: 18, align: 'start' }, [
      sectionHeader('ARCHITECTURE', '架构设计', '独立前端 + Django Ninja 后端聚合 + Celery / Redis / Channels 实时链路。'),
      headingUnderline(200),
      column({ name: 'arch-body', width: 'fill', gap: 18, align: 'start' }, [
        row({ name: 'arch-flow', width: 'fill', gap: 12, align: 'start' }, [
          flowNode('用户 / 领导', '看 Dashboard、任务、报告和演示结果。', '1', false),
          tx('→', `font: 28px ${FONT_MONO}; weight: 700; color: ${C.accent}; wrap: none;`, { name: 'arch-arrow-1', width: 24 }),
          flowNode('独立前端', '/deepaudit-app/，页面级权限控制。', '2', true),
          tx('→', `font: 28px ${FONT_MONO}; weight: 700; color: ${C.accent}; wrap: none;`, { name: 'arch-arrow-2', width: 24 }),
          flowNode('API 聚合', '/api/deepaudit/*，按业务域拆分。', '3', false),
          tx('→', `font: 28px ${FONT_MONO}; weight: 700; color: ${C.accent}; wrap: none;`, { name: 'arch-arrow-3', width: 24 }),
          flowNode('Worker', 'Celery + AgentRunner 执行长任务。', '4', false),
          tx('→', `font: 28px ${FONT_MONO}; weight: 700; color: ${C.accent}; wrap: none;`, { name: 'arch-arrow-4', width: 24 }),
          flowNode('SSE / WS', '事件流回传到前端实时渲染。', '5', true),
        ]),
        row({ name: 'arch-runtime', width: 'fill', gap: 24, align: 'start' }, [
          column({ name: 'arch-runtime-left', width: 520, gap: 10, align: 'start' }, [
            tx('运行支撑层', S.sectionTiny, { name: 'arch-support-kicker' }),
            chipGrid([
              ['ASGI', 'Celery', 'Redis', 'Channels'],
              ['Nginx', 'Workspace', 'RAG', 'Reports'],
            ], { name: 'arch-support-chips' }),
            tx('前端只关心事件流；后端把“执行”和“回传”拆开，保证长任务能持续可观测。', S.bodyMuted, { name: 'arch-summary', width: 500 }),
          ]),
          column({ name: 'arch-runtime-right', width: 'fill', gap: 12, align: 'start' }, [
            tx('后端子域', S.sectionTiny, { name: 'arch-domain-kicker' }),
            chipGrid([
              ['project', 'scan_task', 'agent_task', 'rag'],
              ['audit_rule', 'prompt_template', 'user_config', 'dashboard'],
            ], { name: 'arch-domain-chips' }),
            tx('这些子域分别负责项目、传统扫描、Agent 审计、策略、知识和结果交付。', S.bodySmall, { name: 'arch-domain-note', width: 540 }),
            tx('核心对象', S.sectionTiny, { name: 'arch-entity-kicker' }),
            chipGrid([
              ['AuditProject', 'AuditTask', 'AgentTask', 'AgentCheckpoint'],
              ['AgentEvent', 'AgentFinding', 'AuditRuleSet', 'PromptTemplate'],
            ], { name: 'arch-entity-chips' }),
          ]),
        ]),
        tx('入口 `/deepaudit-app/` 对接 Focus 主平台 token；SSE `/stream` 与 WebSocket `/ws/` 都依赖 ASGI + Redis + Nginx 的同一条链路。', S.bodySmall, { name: 'arch-note', width: 1080 }),
      ]),
    ])
  );
  notes(slide, `架构上，DeepAudit 采用的是独立前端加后端聚合服务的方式。前端是单独的 /deepaudit-app/，主要负责交互、展示和实时渲染；后端统一挂在 /api/deepaudit/*，按业务域拆分，不是一个大接口包打天下；长任务则交给 Celery 和 AgentRunner 去执行，实时结果再通过 SSE 和 WebSocket 回传到前端。

这里最关键的不是“接口多不多”，而是“执行”和“回传”被拆开了。这样长任务就不会把页面卡死，前端也能持续看到过程，而不是只能等一个最终结果。整条链路里，ASGI、Redis、Channels 和 Nginx 都不是背景板，而是整个实时链路成立的基础。

从运行方式上看，我们其实是把 DeepAudit 做成了一个可观测的异步系统：用户看到的是界面，系统内部跑的是任务编排、状态传递和事件流推送。这样既能支撑现场演示，也能支撑后续正式部署。`);
}

function buildImplementation(slide) {
  slide.background.fill = paint(C.bg);
  slide.compose(
    column({ name: 'impl-root', width: W, height: H, padding: 56, gap: 18, align: 'start' }, [
      sectionHeader('IMPLEMENTATION', '实现方法与关键技术', '先工具、再推理；先收敛、再验证；先回传、再报告。'),
      headingUnderline(230),
      row({ name: 'impl-body', width: 'fill', gap: 24, align: 'start' }, [
        column({ name: 'impl-exec', width: 330, gap: 12, align: 'start' }, [
          tx('执行链', S.sectionTiny, { name: 'impl-exec-kicker' }),
          tx('任务入口与运行时', S.titleSmall, { name: 'impl-exec-title' }),
          bullet('任务入口分域', 'project_services、scan_task_services、agent_task_services 分别处理项目、传统扫描和 Agent 审计。', C.accent),
          bullet('工作区准备', 'runtime.py + storage.py 负责 workspace、git worktree、ZIP、SSH 和目录清理。', C.warm),
          bullet('结果输出', 'reporting.py 生成 PDF / JSON，AgentCheckpoint 支持恢复和重跑。', C.green),
        ]),
        column({ name: 'impl-orch', width: 360, gap: 12, align: 'start' }, [
          tx('遥测与健壮性', S.sectionTiny, { name: 'impl-orch-kicker' }),
          tx('分布式追踪与熔断', S.titleSmall, { name: 'impl-orch-title' }),
          bullet('Event Manager', '内存队列 + SSE 异步迭代，实现高并发下的低延迟事件分发。', C.accent),
          panel(
            {
              name: 'impl-orch-panel',
              width: 'fill',
              padding: [14, 14, 14, 14],
              fill: paint('rgba(255,255,255,0.03)'),
              line: stroke('1px rgba(255,255,255,0.12)'),
              align: 'start',
              justify: 'start',
            },
            column({ name: 'impl-orch-tree', gap: 8, width: 'fill' }, [
              tx('Circuit Breaker (熔断器)', `font: 16px ${FONT_MONO}; weight: 700; color: ${C.accent}; wrap: none;`, { name: 'impl-orch-tree-title' }),
              tx('CLOSED → OPEN → HALF_OPEN → CLOSED', `font: 14px ${FONT_MONO}; weight: 700; color: ${C.text}; wrap: none;`, { name: 'impl-orch-tree-body' }),
              tx('失败阈值 5 次，恢复超时 30s，防止级联故障。', S.bodySmall, { name: 'impl-orch-tree-note' }),
            ])
          ),
          bullet('分布式追踪 (Tracer)', '记录执行时间、Token使用量和关联ID，构建完整的追踪树。', C.cyan),
          bullet('速率限制 (Rate Limiter)', '基于令牌桶算法，平滑控制 LLM 和外部工具的并发请求频率。', C.green),
        ]),
        column({ name: 'impl-realtime', width: 380, gap: 12, align: 'start' }, [
          tx('实时层', S.sectionTiny, { name: 'impl-realtime-kicker' }),
          tx('可观测 + 可恢复', S.titleSmall, { name: 'impl-realtime-title' }),
          bullet('流式事件', 'thinking、tool_call、node_start、phase_start、finding、heartbeat、task_end 持续回传。', C.accent),
          bullet('前端重连', 'fetch + ReadableStream + afterSequence 续传，配合 heartbeat 和指数退避重连。', C.green),
          bullet('任务恢复', 'checkpoint、snapshot、workspace 缓存让长任务中断后仍能恢复。', C.cyan),
          tx('SSE 负责主链流式输出，WebSocket 负责任务事件推送，两者共同支撑现场演示。', S.bodySmall, { name: 'impl-realtime-note', width: 360 }),
        ]),
      ]),
      tx('核心思路是“工具覆盖 + 模型解释 + 检查点恢复 + 事件流回传”，而不是只给一个静态最终结果。', S.bodySmall, { name: 'impl-note', width: 1080 }),
    ])
  );
  notes(slide, `实现方法上，DeepAudit 的核心思路可以概括成一句话：先工具、再推理；先收敛、再验证；先回传、再报告。

在任务入口层，我们把项目任务、传统扫描任务和 Agent 审计任务分成不同的服务域来处理，避免一套逻辑覆盖所有场景。工作区准备阶段会统一处理 workspace、git worktree、ZIP、SSH 和目录清理，这样不管是仓库、压缩包还是远程访问，都能进入同一条分析链。

在编排层，Orchestrator 负责先决定审计范围，再调度 recon、analysis、verification、reporting 这些阶段。这里不是一上来就让模型直接下结论，而是先让工具跑起来，再让模型做语义收敛和解释。像 Semgrep、Bandit、Gitleaks、OSV-Scanner 这些外部工具，会先帮我们把事实面的问题筛出来；随后模型再结合上下文做归因、解释和建议。

在实时层，我们把 thinking、tool_call、finding、checkpoint 这些中间状态都持续回传出来，前端也支持断点续传和重连。这样一来，DeepAudit 展示给领导的不是一个静态终稿，而是一个过程可见、结果可复核、任务可恢复的审计系统。`);
}

function buildKnowledge(slide) {
  slide.background.fill = paint(C.bg);
  slide.compose(
    column({ name: 'knowledge-root', width: W, height: H, padding: 56, gap: 16, align: 'start' }, [
      sectionHeader('RAG & KNOWLEDGE', '知识库与模型配置', '把通用漏洞知识、项目专项知识和用户级模型配置拆开，避免经验散落。'),
      headingUnderline(240),
      row({ name: 'knowledge-body', width: 'fill', gap: 24, align: 'start' }, [
        column({ name: 'knowledge-layer', width: 330, gap: 12, align: 'start' }, [
          tx('知识分层', S.sectionTiny, { name: 'knowledge-layer-kicker' }),
          tx('共享基线 + 项目专项', S.titleSmall, { name: 'knowledge-layer-title' }),
          bullet('共享基线知识', 'vulnerabilities / frameworks 继续维护在内置模块里，适合通用漏洞模式和长期稳定规则。', C.accent),
          bullet('项目 / 团队知识', 'custom 条目写入 media/deepaudit/knowledge/*.json，适合误报边界、内部规范和项目坑点。', C.warm),
          bullet('项目 RAG', '项目代码索引面向事实，负责“当前仓库里有什么”。', C.green),
        ]),
        column({ name: 'knowledge-schema', width: 360, gap: 12, align: 'start' }, [
          tx('条目规范', S.sectionTiny, { name: 'knowledge-schema-kicker' }),
          tx('id 是真正的模块名', S.titleSmall, { name: 'knowledge-schema-title' }),
          bullet('命名规则', '推荐使用 custom_<name>_<topic>、team_<domain>_<topic>、proj_<project>_<topic>。', C.accent),
          bullet('字段结构', 'id / title / content / category / tags 为基础字段，必要时再加 severity、cwe_ids、owasp_ids。', C.cyan),
          bullet('内容模板', '场景 / 风险模式 / 检测信号 / 误报边界 / 修复建议 / 最小示例。', C.green),
        ]),
        column({ name: 'knowledge-llm', width: 'fill', gap: 12, align: 'start' }, [
          tx('私有模型与运行参数', S.sectionTiny, { name: 'knowledge-llm-kicker' }),
          tx('LLM / Embedding / 缓存', S.titleSmall, { name: 'knowledge-llm-title' }),
          bullet('内网网关', 'LLM_BASE_URL 和 EMBEDDING_BASE_URL 都应指向内网地址，避免生产流量出网。', C.accent),
          bullet('超时控制', 'LLM_FIRST_TOKEN_TIMEOUT 与 LLM_STREAM_TIMEOUT 保障首包和持续流式输出。', C.warm),
          bullet('离线缓存', 'DEEPAUDIT_TIKTOKEN_MODE=local，TIKTOKEN_CACHE_DIR 需被 Django 与 Celery 同时读取。', C.green),
          bullet('用户级覆盖', 'deepaudit_user_config 里的 LLM / Embedding 配置可以覆盖系统默认值，密钥入库前加密。', C.cyan),
          tx('一句话：知识库负责经验，项目 RAG 负责事实，两个一起用才完整。', S.bodySmall, { name: 'knowledge-callout-lite', width: 380 }),
        ]),
      ]),
    ])
  );
  notes(slide, `这一页的重点是：我们把“经验”和“事实”分开管理了。

通用漏洞知识、项目专项知识和项目代码 RAG 三层分别承担不同职责。共享基线知识负责通用漏洞模式和长期稳定规则；项目专项知识负责团队经验、误报边界和内部规范；项目 RAG 则负责把当前仓库里的事实找出来，也就是“这个项目现在到底有什么”。这样设计之后，DeepAudit 就不会把知识、规则和项目上下文混在一起，减少经验散落和重复维护。

在配置上，LLM 和 Embedding 都可以通过内网网关访问，LLM_BASE_URL 和 EMBEDDING_BASE_URL 都可以指向受控地址，避免生产流量直接出网；首 token 超时和流式超时也都有独立控制；tiktoken 还能走本地缓存，保证离线或内网环境也能稳定运行。同时，用户级配置还能覆盖系统默认值，这样不同团队、不同模型策略都能按自己的方式接入。

所以这部分的本质是：知识库负责经验，RAG 负责事实，模型配置负责边界。三者一起，DeepAudit 才能稳定地做出可解释、可控的审计结果。`);
}

function buildDemo(slide) {
  slide.background.fill = paint(C.bg);
  slide.compose(
    column({ name: 'demo-root', width: W, height: H, padding: 56, gap: 16, align: 'start' }, [
      sectionHeader('LIVE DEMO', '项目演示：推荐现场操作顺序', '现场演示以 live demo 为主，截图作为兜底；优先展示闭环，而不是逐个点按钮。'),
      headingUnderline(260),
      row({ name: 'demo-body', width: 'fill', gap: 28, align: 'start' }, [
        column({ name: 'demo-left', width: 380, gap: 14, align: 'start' }, [
          tx('建议按这个顺序走，领导只需要先看到结果，再看到过程。', S.body, { name: 'demo-statement', width: 350 }),
          bullet('1. Dashboard', '先展示总览、最近项目、任务、规则 / 模板统计。', C.accent),
          bullet('2. 项目管理', '再看仓库 / ZIP、分支、成员、项目详情。', C.warm),
          bullet('3. Agent 审计', '重点看实时事件流、任务树、Finding、Checkpoint。', C.green),
          bullet('4. 报告页', '最后打开任务报告，展示问题定位和 PDF / JSON 导出。', C.cyan),
          bullet('5. 截图兜底', '如果实时流不稳，直接切报告页截图，不影响主结论。', C.accent),
        ]),
        column({ name: 'demo-right', width: 'fill', gap: 10, align: 'start' }, [
          tx('报告页 / 兜底截图', S.sectionTiny, { name: 'demo-image-kicker' }),
          panel({
            name: 'demo-image-panel',
            width: 'fill',
            height: 430,
            padding: 14,
            fill: paint('#0f1218'),
            line: stroke('1px #263041'),
            align: 'start',
            justify: 'start',
          }),
        ]),
      ]),
    ])
  );
  slide.images.add({
    blob: ASSETS.report,
    contentType: 'image/png',
    position: { left: 553, top: 189, width: 574, height: 484 },
    fit: 'contain',
  });
  notes(slide, `这一页我建议按固定顺序演示，这样领导能先看到结果，再看到过程。

第一步先看 Dashboard，让大家先建立整体印象：总览、最近项目、任务数量、规则和模板统计都能一眼看到。第二步进入项目管理，看看仓库、ZIP、分支、成员和项目详情，确认项目接入本身是完整的。第三步打开一个 Agent 审计任务，重点看实时事件流、任务树、Finding 和 Checkpoint，让大家看到它不是一次性出结果，而是边分析边回传。第四步打开报告页，展示问题定位、修复建议，以及 PDF / JSON 的导出。

如果现场实时流比较稳定，就尽量让大家看到完整过程；如果实时流临时不稳定，也不要硬撑，直接切到报告页或截图兜底，因为今天要证明的不是某个按钮，而是“项目接入 + 分析 + 报告”这条主线已经跑通。演示时我会特别强调：DeepAudit 的价值不是把页面点一遍，而是把一个项目从接入到交付的闭环完整跑出来。`);
}

function buildResults(slide) {
  slide.background.fill = paint(C.bg);
  slide.compose(
    column({ name: 'results-root', width: W, height: H, padding: 56, gap: 18, align: 'start' }, [
      sectionHeader('MILESTONE', '阶段成果与下一步', '当前成果已经形成闭环，下一步重点放在知识、规则、监控和真实指标沉淀。'),
      headingUnderline(240),
      row({ name: 'results-body', width: 'fill', gap: 24, align: 'start' }, [
        column({ name: 'results-left', width: 350, gap: 12, align: 'start' }, [
          tx('已经跑通', S.sectionTiny, { name: 'results-left-kicker' }),
          tx('DeepAudit 主线闭环已成立。', S.titleSmall, { name: 'results-left-title', width: 'fill' }),
          bullet('项目接入', '仓库 / ZIP / 分支 / 成员 / 回收站都已可用。', C.accent),
          bullet('智能分析', '多智能体 + 外部工具优先 + RAG 形成稳定分析链。', C.green),
          bullet('实时回传', 'SSE / WebSocket / heartbeat / reconnect 已接通。', C.cyan),
          bullet('报告交付', '任务详情、问题定位、PDF / JSON 导出闭环完整。', C.warm),
        ]),
        column({ name: 'results-right', width: 350, gap: 12, align: 'start' }, [
          tx('下一步', S.sectionTiny, { name: 'results-right-kicker' }),
          tx('把平台化能力沉淀成可持续运营能力。', S.titleSmall, { name: 'results-right-title', width: 'fill' }),
          bullet('知识库', '补充真实场景、误报边界和修复建议。', C.accent),
          bullet('规则覆盖', '扩充语言、框架和项目类型，减少人工补充。', C.green),
          bullet('部署与监控', '完善 ASGI / Redis / Nginx / 日志和告警。', C.cyan),
          bullet('真实指标', '现场前补真实值，不在 PPT 里硬编数字。', C.warm),
        ]),
        column({ name: 'results-metrics', width: 'fill', gap: 14, align: 'start' }, [
          tx('预留指标位', S.sectionTiny, { name: 'results-metrics-kicker' }),
          column({ name: 'results-metric-grid', gap: 12, width: 'fill', align: 'start' }, [
            row({ name: 'results-metric-row-1', gap: 12, width: 'fill', align: 'start' }, [
              metricPlaceholder('审计任务数'),
              metricPlaceholder('有效发现数'),
            ]),
            row({ name: 'results-metric-row-2', gap: 12, width: 'fill', align: 'start' }, [
              metricPlaceholder('报告导出数'),
              metricPlaceholder('知识库条目数'),
            ]),
          ]),
          tx('这些位置保留给现场前补充的真实运行数据。', S.bodySmall, { name: 'results-metrics-note', width: 460 }),
          tx('推荐的后续路线', S.sectionTiny, { name: 'results-roadmap-kicker' }),
          chipGrid([
            ['知识库沉淀', '规则覆盖'],
            ['部署监控', '指标运营'],
          ], { name: 'results-roadmap' }),
        ]),
      ]),
    ])
  );
  notes(slide, `这一页我想传达两个信息。第一，DeepAudit 的主线闭环已经成型，项目接入、智能分析、实时回传和报告交付都已经跑通；第二，现在已经不是“有没有”的问题，而是“怎么持续运营、怎么沉淀价值”的问题。

所以接下来我们的重点会放在四件事上：一是继续补充知识库，把更多真实场景、误报边界和修复建议沉淀进去；二是扩展规则覆盖，让更多语言、框架和项目类型都能更稳定地支持；三是完善部署监控，把 ASGI、Redis、Nginx 和日志告警这些基础设施补齐；四是补真实运营指标。

这页里预留的几个指标位，比如审计任务数、有效发现数、报告导出数、知识库条目数，建议现场前再补真实数据，避免在 PPT 里硬编数字。所以这一页的结论很简单：平台已经跑通，下一步是把能力沉淀成可持续运营的能力。`);
}

function buildAppendixApis(slide) {
  slide.background.fill = paint(C.bg);
  slide.compose(
    column({ name: 'appendix-api-root', width: W, height: H, padding: 56, gap: 18, align: 'start' }, [
      sectionHeader('APPENDIX', '核心 API 与页面映射', '这页给领导和现场问答做技术备份：页面怎么进，接口怎么挂。'),
      headingUnderline(230),
      row({ name: 'appendix-api-body', width: 'fill', gap: 28, align: 'start' }, [
        column({ name: 'appendix-pages', width: 390, gap: 12, align: 'start' }, [
          tx('前端页面', S.sectionTiny, { name: 'appendix-pages-kicker' }),
          tx('独立路由入口', S.titleSmall, { name: 'appendix-pages-title' }),
          routeItem('/   Agent审计', '核心工作台，创建并观察 Agent 任务。'),
          routeItem('/dashboard   仪表盘', '总览、最近项目、任务与统计。'),
          routeItem('/projects   项目管理', '仓库 / ZIP、成员、项目详情。'),
          routeItem('/instant-analysis   即时分析', '快速分析，不走完整任务链。'),
          routeItem('/audit-tasks   传统任务', '仓库扫描、ZIP 扫描、任务详情。'),
          routeItem('/audit-rules / prompts / admin / recycle-bin', '策略治理与回收站。'),
        ]),
        column({ name: 'appendix-apis', width: 'fill', gap: 12, align: 'start' }, [
          tx('后端接口', S.sectionTiny, { name: 'appendix-apis-kicker' }),
          tx('按业务域拆分，不是单一大接口。', S.titleSmall, { name: 'appendix-apis-title' }),
          apiItem('/api/deepaudit/projects / members', '项目、成员、owner、回收站。'),
          apiItem('/api/deepaudit/scan/*', '仓库扫描、ZIP 扫描、即时分析。'),
          apiItem('/api/deepaudit/agent-tasks', 'Agent 任务、Finding、Checkpoint、摘要。'),
          apiItem('/api/deepaudit/rules / prompts / settings / ssh-keys / rag / data-tools', '规则、提示词、配置、知识检索与数据导出。'),
          apiItem('/api/deepaudit/dashboard / reports/*', '看板摘要与 JSON / PDF 导出。'),
          tx('前端实现：agentStream.ts / useResilientStream.ts / focusAdapter.ts；实时链路：SSE + WebSocket。', S.bodySmall, { name: 'appendix-api-stream-note', width: 760 }),
        ]),
      ]),
    ])
  );
  notes(slide, `这页主要是给领导和现场问答做技术备份，方便快速对上“页面怎么进、接口怎么挂”。

前端这边，/ 是 Agent 审计工作台，/dashboard 是仪表盘，/projects 是项目管理，/instant-analysis 是即时分析，/audit-tasks 是传统任务，/audit-rules、/prompts、/admin、/recycle-bin 则对应策略治理和回收站。这样做的好处是，页面和业务域是一一对应的，不会混在一起。

后端这边，接口按业务域拆分：项目、成员、扫描、Agent 任务、规则、提示词、配置、RAG、数据工具、看板和报告都各有入口，不是单一大接口。前端实时链路则由 agentStream.ts、useResilientStream.ts 和相关适配层一起支撑，整体通过 SSE 和 WebSocket 回传。

如果现场有人问“为什么要这么拆”，你可以直接回答：因为这样更利于维护、更利于扩展，也更利于把一个大平台拆成清晰的业务边界。`);
}

function buildAppendixOps(slide) {
  slide.background.fill = paint(C.bg);
  slide.compose(
    column({ name: 'appendix-ops-root', width: W, height: H, padding: 56, gap: 18, align: 'start' }, [
      sectionHeader('APPENDIX', '演示兜底与部署', '现场如果实时流不稳，先保主线，再切截图兜底。'),
      headingUnderline(230),
      row({ name: 'appendix-ops-body', width: 'fill', gap: 24, align: 'start' }, [
        column({ name: 'ops-left', width: 350, gap: 12, align: 'start' }, [
          tx('演示兜底', S.sectionTiny, { name: 'ops-left-kicker' }),
          tx('先保主线', S.titleSmall, { name: 'ops-left-title', width: 'fill' }),
          bullet('优先路径', 'Dashboard → 项目管理 → Agent 审计 → 报告页。', C.accent),
          bullet('备用素材', 'home / report 两张截图已准备好。', C.warm),
          bullet('节奏控制', '流卡住就切报告页，主结论不受影响。', C.green),
          panel(
            {
              name: 'ops-callout',
              width: 'fill',
              padding: [14, 14, 14, 14],
              fill: paint('rgba(255,106,42,0.10)'),
              line: stroke('1px rgba(255,106,42,0.30)'),
              align: 'start',
              justify: 'start',
            },
            column({ name: 'ops-callout-copy', gap: 5, width: 'fill' }, [
              tx('一句话原则', S.sectionTiny, { name: 'ops-callout-kicker' }),
              tx('只要“项目接入 + 分析 + 报告”能跑通，主线就成立。', S.callout, { name: 'ops-callout-title', width: 380 }),
              tx('实时链路是加分项；不稳时，用截图保住理解路径。', S.calloutMuted, { name: 'ops-callout-subtitle', width: 380 }),
            ])
          ),
        ]),
        column({ name: 'ops-middle', width: 400, gap: 12, align: 'start' }, [
          tx('运行前提', S.sectionTiny, { name: 'ops-middle-kicker' }),
          tx('先看依赖', S.titleSmall, { name: 'ops-middle-title', width: 'fill' }),
          bullet('ASGI / Celery', '长任务、SSE 和 WebSocket 都依赖异步执行。', C.accent),
          bullet('Redis + Channels', 'group 状态、队列和推送都靠它。', C.cyan),
          bullet('Nginx 代理', '/basic-api/api、/ws/、stream 要转发且 stream 不能缓冲。', C.green),
          bullet('tiktoken / LLM', '内网网关、离线缓存和首包超时都要预先处理。', C.warm),
        ]),
        column({ name: 'ops-right', width: 'fill', gap: 12, align: 'start' }, [
          tx('常见故障信号', S.sectionTiny, { name: 'ops-right-kicker' }),
          tx('先查代理和 worker', S.titleSmall, { name: 'ops-right-title', width: 'fill' }),
          bullet('页面能打开，但流不刷新', '优先查 SSE / WS / buffering 与 Nginx 配置。', C.accent),
          bullet('接口 401 / 404', '先看 token、baseURL、/basic-api/api 是否对齐。', C.warm),
          bullet('日志有任务，UI 没事件', '常见是 Redis、Channels 或 DeepAudit worker 未就绪。', C.green),
          chipGrid([
            ['ENABLE_SCHEDULER=false', 'REDIS DB 隔离'],
            ['deepaudit-local.sh', 'warm_tiktoken_cache.py'],
          ], { name: 'ops-chips' }),
        ]),
      ]),
    ])
  );
  notes(slide, `这页是现场兜底说明，主要解决两个问题：如果实时流不稳怎么办，以及正式演示前要先确认哪些基础依赖。

第一，演示时如果 SSE 或 WebSocket 不稳定，我们就先保主线，再切截图兜底。只要“项目接入 + 分析 + 报告”能跑通，主线就成立，实时流是加分项，不是唯一证明方式。第二，部署前要先确认 ASGI、Celery、Redis、Channels、Nginx 这些基础依赖都正常，特别是流式输出不要被代理缓冲。

常见故障可以这么排查：如果页面能打开但不刷新，优先查 SSE、WebSocket、buffering 和 Nginx 配置；如果接口返回 401 或 404，先看 token、baseURL 和 /basic-api/api 是否对齐；如果日志里有任务但 UI 没事件，通常是 Redis、Channels 或 worker 没起来。

所以现场演示的原则很简单：先保主线，再看细节；先看结果，再解释过程。最后就可以进入 Q&A。`);
}

function buildDeck() {
  const presentation = Presentation.create();
  const slides = [
    buildCover,
    buildWhy,
    buildPanorama,
    buildArchitecture,
    buildAgentArchitecture,
    buildImplementation,
    buildSandboxAndTools,
    buildKnowledge,
    buildDemo,
    buildResults,
    buildAppendixApis,
    buildAppendixOps,
  ];

  for (const builder of slides) {
    const slide = presentation.slides.add({ width: W, height: H });
    builder(slide);
  }

  return presentation;
}

async function exportDeck(presentation) {
  await fs.mkdir(OUTPUT_DIR, { recursive: true });
  await fs.mkdir(PREVIEW_DIR, { recursive: true });

  const pptxBlob = await PresentationFile.exportPptx(presentation);
  await pptxBlob.save(PPTX_PATH);

  const previewPaths = [];
  for (let i = 0; i < presentation.slides.count; i += 1) {
    const slide = presentation.slides.getItem(i);
    const blob = await slide.export({ format: 'png' });
    const png = Buffer.from(await blob.arrayBuffer());
    const fileName = `slide-${String(i + 1).padStart(2, '0')}.png`;
    const outPath = path.join(PREVIEW_DIR, fileName);
    await fs.writeFile(outPath, png);
    previewPaths.push(outPath);
  }

  return { pptxPath: PPTX_PATH, previewPaths };
}

async function main() {
  const presentation = buildDeck();
  const result = await exportDeck(presentation);
  console.log(JSON.stringify(result, null, 2));
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  await main();
}

export { buildDeck, exportDeck, main, W, H, PPTX_PATH, PREVIEW_DIR };
