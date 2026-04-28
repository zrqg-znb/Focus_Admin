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
  notes(slide, '今天我汇报 DeepAudit 智能审计平台。先给结论：它已经不是单点扫描，而是从项目接入、分析、验证到报告的完整闭环。后面我按价值、架构、实现和演示四部分展开。');
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
  notes(slide, '这一页先讲为什么要做。传统扫描能发现问题，但解释、验证和交付都偏弱，所以我们把目标放在审计工作台，而不是另一个扫描器。');
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
  notes(slide, '这一页汇总现有能力。重点不是页面多少，而是已经把项目接入、审计能力、策略治理和结果交付串成了一条完整链路。');
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
  notes(slide, '这里详细介绍多智能体架构。核心是 Orchestrator 通过 ReAct 循环进行决策。Recon、Analysis、Verification 各司其职。');
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
          tx('从“发现”到“确认”', S.titleSmall),
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
  notes(slide, '这一页补充工具链和沙箱。AST 提供精准的上下文，外部工具提供覆盖面，而沙箱让我们能运行 PoC 确认漏洞，这是区别于传统 SAST 的关键。');
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
  notes(slide, '这一页讲架构。我会重点强调前后端分离、业务域拆分，以及 SSE / WebSocket 为什么必须和 ASGI、Redis、Nginx 一起看。');
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
  notes(slide, '这一页讲实现方法。核心思路是工具先行、模型编排、检查点恢复、事件流回传，说明 DeepAudit 不是只给一个最终结论。');
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
  notes(slide, '这一页讲知识库和模型配置。重点是把通用知识、项目知识和用户级模型配置拆开，确保经验能沉淀、模型能管控。');
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
  notes(slide, '这一页是现场演示节奏说明。按 Dashboard、项目、Agent、报告页的顺序走，让领导先看到闭环，再看过程。');
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
  notes(slide, '这一页讲阶段成果和下一步。当前闭环已经跑通，接下来要把知识库、规则覆盖、部署监控和运营指标补齐。');
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
  notes(slide, '这一页是技术备份，用来回答页面和接口怎么对应，重点看前端路由、后端分域和实时链路文件。');
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
  notes(slide, '这一页是兜底说明，尤其是当实时流不稳定时，如何保住演示主线，以及部署前要先确认哪些基础依赖。');
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
