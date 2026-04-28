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
  notes(slide, '开场先给结论：DeepAudit 已经从单点功能变成完整平台。本次汇报按价值、架构、实现、演示四个层次展开。');
}

function buildWhy(slide) {
  slide.background.fill = paint(C.bg);
  slide.compose(
    column({ name: 'why-root', width: W, height: H, padding: [42, 60, 48, 60], gap: 20, align: 'start' }, [
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
        column({ name: 'why-right', width: 'fill', gap: 18, align: 'start' }, [
          tx('DeepAudit 的目标', S.sectionTiny, { name: 'why-target-kicker' }),
          tx('把“项目接入 → 分析 → 验证 → 报告”串成闭环。', S.titleSmall, { name: 'why-target-title', width: 640 }),
          tx('它不是单点工具，而是面向部门内部审计流程的智能审计工作台。', S.subtitle, { name: 'why-target-subtitle', width: 640 }),
          row({ name: 'why-compare', gap: 18, width: 'fill', align: 'start' }, [
            column({ name: 'why-compare-left', gap: 10, width: 282, align: 'start' }, [
              tx('传统方式', S.coverMeta, { name: 'why-trad' }),
              bullet('扫描结果多', '但上下文弱。'),
              bullet('问题能发现', '但无法统一解释。'),
              bullet('报告能导出', '但不能形成审计闭环。'),
            ]),
            column({ name: 'why-compare-right', gap: 10, width: 282, align: 'start' }, [
              tx('DeepAudit', S.coverMeta, { name: 'why-deepaudit' }),
              bullet('接入与权限统一', '仓库 / ZIP / 成员 / 回收站 / 角色一体化。', C.accent),
              bullet('分析过程可观测', 'thinking、tool、finding、checkpoint 全程回传。', C.green),
              bullet('结果可交付', '报告页、PDF / JSON 导出、Dashboard 可直接演示。', C.cyan),
            ]),
          ]),
        ]),
      ]),
    ])
  );
  notes(slide, '这一页先让领导理解：DeepAudit 解决的不是单次扫描，而是审计闭环。强调价值点：解释、验证、交付。');
}

function buildPanorama(slide) {
  slide.background.fill = paint(C.bg);
  slide.compose(
    column({ name: 'panorama-root', width: W, height: H, padding: [42, 60, 40, 60], gap: 18, align: 'start' }, [
      sectionHeader('FEATURE PANORAMA', '现有功能全景', '已经形成“接入—分析—治理—交付”的完整链路。'),
      headingUnderline(210),
      row({ name: 'panorama-stages', width: 'fill', gap: 20, align: 'start' }, [
        stageColumn('01', '项目接入', [
          { title: '仓库 / ZIP', desc: '支持两种接入方式，兼容已有代码库和离线包。', accent: C.accent },
          { title: '分支 / 成员', desc: '项目上下文与成员角色绑定，便于协作审计。', accent: C.warm },
          { title: '回收站 / 权限', desc: '有恢复路径，也有页面级访问码控制。', accent: C.green },
        ]),
        stageColumn('02', '审计能力', [
          { title: '传统扫描', desc: '仓库扫描、ZIP 扫描、即时分析。', accent: C.accent },
          { title: 'Agent 审计', desc: '多智能体推理、事件流、检查点和恢复。', accent: C.cyan },
          { title: '结果聚合', desc: '问题、Finding、摘要统一呈现。', accent: C.warm },
        ]),
        stageColumn('03', '策略治理', [
          { title: '规则集 / 规则', desc: '管理审计策略和检测粒度。', accent: C.accent },
          { title: '提示词模板', desc: '统一模型交互方式，沉淀可复用模板。', accent: C.green },
          { title: 'RAG / 系统配置', desc: '知识库、LLM、Embedding、SSH 配置都可治理。', accent: C.cyan },
        ]),
        stageColumn('04', '结果交付', [
          { title: 'Dashboard', desc: '看总览、最近项目、任务统计与运行状态。', accent: C.accent },
          { title: '任务详情', desc: '问题定位、过程回放、阶段结果统一查看。', accent: C.green },
          { title: 'PDF / JSON', desc: '导出标准化报告，适合对内汇报和留档。', accent: C.warm },
        ]),
      ]),
      row({ name: 'panorama-footer', gap: 10, width: 'fill', align: 'start' }, [
        chip('接入'), chip('分析'), chip('治理'), chip('交付'), chip('闭环', { accent: true }),
      ]),
    ])
  );
  notes(slide, '这一页强调功能全景，不展开代码细节。重点收束到四段链路：接入、分析、治理、交付。');
}

function buildArchitecture(slide) {
  slide.background.fill = paint(C.bg);
  slide.compose(
    column({ name: 'arch-root', width: W, height: H, padding: [42, 60, 40, 60], gap: 20, align: 'start' }, [
      sectionHeader('ARCHITECTURE', '架构设计', '独立前端 + Django Ninja 后端聚合 + Celery / Redis / Channels 实时链路。'),
      headingUnderline(190),
      column({ name: 'arch-body', width: 'fill', gap: 20, align: 'start' }, [
        row({ name: 'arch-flow', width: 'fill', gap: 14, align: 'start' }, [
          flowNode('用户 / 领导', '查看任务、报告、演示结果。', '1', false),
          tx('→', `font: 28px ${FONT_MONO}; weight: 700; color: ${C.accent}; wrap: none;`, { name: 'arch-arrow-1', width: 28 }),
          flowNode('独立前端', '/deepaudit-app/，React 应用。', '2', true),
          tx('→', `font: 28px ${FONT_MONO}; weight: 700; color: ${C.accent}; wrap: none;`, { name: 'arch-arrow-2', width: 28 }),
          flowNode('API 聚合', '/api/deepaudit/*，统一路由入口。', '3', false),
          tx('→', `font: 28px ${FONT_MONO}; weight: 700; color: ${C.accent}; wrap: none;`, { name: 'arch-arrow-3', width: 28 }),
          flowNode('Worker', 'Celery + AgentRunner 执行分析任务。', '4', false),
          tx('→', `font: 28px ${FONT_MONO}; weight: 700; color: ${C.accent}; wrap: none;`, { name: 'arch-arrow-4', width: 28 }),
          flowNode('SSE / WS', '事件流回传到前端实时渲染。', '5', true),
        ]),
        column({ name: 'arch-support', width: 'fill', gap: 10, align: 'start' }, [
          tx('运行支撑层', S.sectionTiny, { name: 'arch-support-kicker' }),
          chipGrid([
            ['ASGI', 'Celery', 'Redis', 'Channels'],
            ['Nginx', 'Workspace', 'RAG', 'Reports'],
          ], { name: 'arch-support-chips' }),
          tx('前端只关心事件流；后端把“执行”和“回传”拆开，保证长任务能持续可观测。', S.bodyMuted, { name: 'arch-summary', width: 1080 }),
        ]),
        row({ name: 'arch-bottom', gap: 16, width: 'fill', align: 'start' }, [
          column({ name: 'arch-bottom-left', gap: 8, width: 330 }, [
            tx('前端入口', S.sectionTiny, { name: 'arch-fe-kicker' }),
            tx('/deepaudit-app/', S.mono, { name: 'arch-fe-path' }),
            tx('页面级权限码控制，接入 Focus 主平台 token。', S.bodySmall, { name: 'arch-fe-note', width: 320 }),
          ]),
          column({ name: 'arch-bottom-right', gap: 8, width: 430 }, [
            tx('实时接口', S.sectionTiny, { name: 'arch-api-kicker' }),
            tx('/api/deepaudit/agent-tasks/{id}/stream  +  /ws/deepaudit/tasks/{id}/', S.monoMuted, { name: 'arch-api-path', width: 420 }),
            tx('SSE 用于连续流式输出，WebSocket 用于任务事件推送。', S.bodySmall, { name: 'arch-api-note', width: 420 }),
          ]),
        ]),
      ]),
    ])
  );
  notes(slide, '这一页把系统拆成一条清晰链路：前端、API、worker、实时回传，再加上运行支撑层。强调它不是普通 CRUD。');
}

function buildImplementation(slide) {
  slide.background.fill = paint(C.bg);
  slide.compose(
    column({ name: 'impl-root', width: W, height: H, padding: [42, 60, 40, 60], gap: 18, align: 'start' }, [
      sectionHeader('IMPLEMENTATION', '实现方法与关键技术', '先工具、再推理；先收敛、再验证；先回传、再报告。'),
      headingUnderline(220),
      row({ name: 'impl-body', width: 'fill', gap: 28, align: 'start' }, [
        column({ name: 'impl-tools', width: 310, gap: 12, align: 'start' }, [
          tx('工具层', S.sectionTiny, { name: 'impl-tools-kicker' }),
          tx('外部工具优先', S.titleSmall, { name: 'impl-tools-title' }),
          bullet('先扫再解释', 'semgrep / bandit / gitleaks / npm_audit / safety / kunlun 先做覆盖。', C.accent),
          bullet('风险聚焦', 'smart_scan、quick_audit 先圈高风险文件，再进入深审。', C.warm),
          bullet('动态验证', 'run_code、extract_function、sandbox harness 负责验证与 PoC。', C.green),
          chipGrid([
            ['semgrep_scan', 'bandit_scan'],
            ['gitleaks_scan', 'npm_audit'],
            ['safety_scan', 'kunlun_scan'],
          ], { name: 'impl-tool-chips' }),
        ]),
        column({ name: 'impl-orch', width: 360, gap: 12, align: 'start' }, [
          tx('编排层', S.sectionTiny, { name: 'impl-orch-kicker' }),
          tx('多智能体编排', S.titleSmall, { name: 'impl-orch-title' }),
          bullet('Orchestrator 是大脑', '负责规划、调度、收敛。', C.accent),
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
              tx('Orchestrator', `font: 18px ${FONT_MONO}; weight: 700; color: ${C.accent}; wrap: none;`, { name: 'impl-orch-tree-title' }),
              tx('↳ recon   ↳ analysis   ↳ verification', `font: 17px ${FONT_MONO}; weight: 700; color: ${C.text}; wrap: none;`, { name: 'impl-orch-tree-body' }),
              tx('recon / analysis / verification 各司其职。', S.bodySmall, { name: 'impl-orch-tree-note' }),
            ])
          ),
        ]),
        column({ name: 'impl-realtime', width: 360, gap: 12, align: 'start' }, [
          tx('体验层', S.sectionTiny, { name: 'impl-realtime-kicker' }),
          tx('实时可观测 + 可恢复', S.titleSmall, { name: 'impl-realtime-title' }),
          bullet('流式事件', 'thinking / tool_call / finding / checkpoint / task_end 全程回传。', C.accent),
          bullet('前端重连', 'ReadableStream + 断线重连 + heartbeat，避免界面卡死。', C.green),
          bullet('任务恢复', 'checkpoint、snapshot、workspace 缓存让长任务可中断可恢复。', C.cyan),
          chipGrid([
            ['thinking', 'tool_call', 'finding'],
            ['checkpoint', 'heartbeat', 'reconnect'],
          ], { name: 'impl-realtime-chips' }),
          tx('知识增强由 RAG + Prompt Template + Rule Set 共同提供，保证可复用和可沉淀。', S.bodySmall, { name: 'impl-realtime-note', width: 330 }),
        ]),
      ]),
    ])
  );
  notes(slide, '这一页讲实现方法：先工具，再编排，再实时回传。强调 Orchestrator、三阶段 Agent、事件流与恢复。');
}

function buildDemo(slide) {
  slide.background.fill = paint(C.bg);
  slide.compose(
    column({ name: 'demo-root', width: W, height: H, padding: [42, 60, 20, 60], gap: 16, align: 'start' }, [
      sectionHeader('LIVE DEMO', '项目演示：推荐现场操作顺序', '现场演示以 live demo 为主，截图作为兜底。'),
      headingUnderline(240),
      row({ name: 'demo-body', width: 'fill', gap: 30, align: 'start' }, [
        column({ name: 'demo-left', width: 370, gap: 14, align: 'start' }, [
          tx('建议按这个顺序走，领导只需要先看到结论，再看到过程。', S.body, { name: 'demo-statement', width: 350 }),
          bullet('1. Dashboard', '先展示总览、最近项目、任务、规则 / 模板统计。', C.accent),
          bullet('2. 项目管理', '再看仓库 / ZIP、分支、成员、项目详情。', C.warm),
          bullet('3. Agent 审计', '现场看实时事件流、任务树、Finding、Checkpoint。', C.green),
          bullet('4. 报告页', '最后打开任务报告，展示问题定位和 PDF / JSON 导出。', C.cyan),
          bullet('5. 截图兜底', '若网络、鉴权或流式输出不稳，直接切备用图，不影响主结论。', C.accent),
          chipGrid([
            ['实时事件流', '任务树', 'Finding'],
            ['Checkpoint', 'PDF / JSON'],
          ], { name: 'demo-tags' }),
        ]),
        column({ name: 'demo-right', width: 'fill', gap: 10, align: 'start' }, [
          tx('报告页 / 兜底截图', S.sectionTiny, { name: 'demo-image-kicker' }),
          panel({
            name: 'demo-image-panel',
            width: 'fill',
            height: 512,
            padding: 16,
            fill: paint('#0f1218'),
            line: stroke('1px #263041'),
            align: 'start',
            justify: 'start',
          }),
          chipGrid([
            ['问题定位', '修复建议'],
            ['PDF 导出', 'JSON 导出'],
          ], { name: 'demo-image-notes' }),
        ]),
      ]),
    ])
  );
  slide.images.add({
    blob: ASSETS.report,
    contentType: 'image/png',
    position: { left: 555, top: 191, width: 570, height: 480 },
    fit: 'contain',
  });
  notes(slide, '现场演示先 Dashboard，再项目管理，再 Agent 审计，最后回到报告页。若实时流不稳定，就直接使用报告页截图兜底。');
}

function buildResults(slide) {
  slide.background.fill = paint(C.bg);
  slide.compose(
    column({ name: 'results-root', width: W, height: H, padding: [42, 60, 36, 60], gap: 18, align: 'start' }, [
      sectionHeader('MILESTONE', '阶段成果与下一步', '当前成果已经形成闭环，下一步重点放在知识、规则、监控和真实指标沉淀。'),
      headingUnderline(230),
      row({ name: 'results-body', width: 'fill', gap: 28, align: 'start' }, [
        column({ name: 'results-left', width: 360, gap: 12, align: 'start' }, [
          tx('已经跑通', S.sectionTiny, { name: 'results-left-kicker' }),
          tx('DeepAudit 主线闭环已成立。', S.titleSmall, { name: 'results-left-title', width: 'fill' }),
          bullet('项目接入', '仓库 / ZIP / 分支 / 成员 / 回收站。', C.accent),
          bullet('智能分析', '多智能体 + 外部工具优先 + RAG。', C.green),
          bullet('实时回传', 'SSE / WebSocket / heartbeat / reconnect。', C.cyan),
          bullet('报告交付', '任务详情、问题定位、PDF / JSON 导出。', C.warm),
        ]),
        column({ name: 'results-right', width: 360, gap: 12, align: 'start' }, [
          tx('下一步', S.sectionTiny, { name: 'results-right-kicker' }),
          tx('把平台化能力沉淀成可持续运营能力。', S.titleSmall, { name: 'results-right-title', width: 'fill' }),
          bullet('知识库', '补充真实场景、误报边界和修复建议。', C.accent),
          bullet('规则覆盖', '扩充语言、框架和项目类型。', C.green),
          bullet('部署与监控', '完善 ASGI / Redis / Nginx / 日志监控。', C.cyan),
          bullet('真实指标', '留出运营位，现场前补真实值，不硬编数字。', C.warm),
        ]),
        column({ name: 'results-metrics', width: 'fill', gap: 16, align: 'start' }, [
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
        ]),
      ]),
    ])
  );
  notes(slide, '这一页先说结论：闭环已跑通。再说下一步：知识库、规则覆盖、监控和真实指标。');
}

function buildAppendixApis(slide) {
  slide.background.fill = paint(C.bg);
  slide.compose(
    column({ name: 'appendix-api-root', width: W, height: H, padding: [42, 60, 38, 60], gap: 18, align: 'start' }, [
      sectionHeader('APPENDIX', '核心 API 与页面映射', '这页给领导和现场问答做技术备份：页面怎么进，接口怎么挂。'),
      headingUnderline(210),
      row({ name: 'appendix-api-body', width: 'fill', gap: 32, align: 'start' }, [
        column({ name: 'appendix-pages', width: 420, gap: 12, align: 'start' }, [
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
          apiItem('/api/deepaudit/rules / prompts / settings / ssh-keys', '规则、提示词、配置与凭据。'),
          apiItem('/api/deepaudit/rag / data-tools', '知识检索、索引与数据导出。'),
          apiItem('/api/deepaudit/dashboard / reports/*', '看板摘要与 JSON / PDF 导出。'),
          panel(
            {
              name: 'appendix-stream-panel',
              width: 'fill',
              padding: [14, 14, 14, 14],
              fill: paint('rgba(255,255,255,0.03)'),
              line: stroke('1px rgba(255,255,255,0.12)'),
              align: 'start',
              justify: 'start',
            },
            column({ name: 'appendix-stream-copy', gap: 6, width: 'fill' }, [
              tx('实时链路', S.sectionTiny, { name: 'appendix-stream-kicker' }),
              tx('/api/deepaudit/agent-tasks/{id}/stream  +  /ws/deepaudit/tasks/{id}/', S.monoMuted, { name: 'appendix-stream-path', width: 660 }),
              tx('SSE 负责流式输出，WebSocket 负责任务事件推送。', S.bodySmall, { name: 'appendix-stream-note' }),
            ])
          ),
        ]),
      ]),
    ])
  );
  notes(slide, '这页放技术备份：页面入口、API 分域、实时链路。领导若追问，直接切到这页。');
}

function buildAppendixOps(slide) {
  slide.background.fill = paint(C.bg);
  slide.compose(
    column({ name: 'appendix-ops-root', width: W, height: H, padding: [42, 60, 38, 60], gap: 18, align: 'start' }, [
      sectionHeader('APPENDIX', '演示兜底与部署', '现场如果实时流不稳，先保主线，再切截图兜底。'),
      headingUnderline(230),
      row({ name: 'appendix-ops-body', width: 'fill', gap: 28, align: 'start' }, [
        column({ name: 'ops-left', width: 330, gap: 12, align: 'start' }, [
          tx('演示兜底', S.sectionTiny, { name: 'ops-left-kicker' }),
          tx('先保主线', S.titleSmall, { name: 'ops-left-title', width: 'fill' }),
          bullet('优先路径', 'Dashboard → 项目管理 → Agent 审计 → 报告页。', C.accent),
          bullet('备用素材', 'home / report 两张截图已准备好。', C.warm),
          bullet('节奏控制', '流卡住就切报告页。', C.green),
        ]),
        column({ name: 'ops-middle', width: 360, gap: 12, align: 'start' }, [
          tx('链路前提', S.sectionTiny, { name: 'ops-middle-kicker' }),
          tx('先看依赖', S.titleSmall, { name: 'ops-middle-title', width: 'fill' }),
          bullet('ASGI / Celery', '长任务和连接都依赖异步执行。', C.accent),
          bullet('Redis + Channels', 'group 状态和推送都靠它。', C.cyan),
          bullet('Nginx 代理', '/basic-api/api、/ws/、stream 要转发。', C.green),
          bullet('缓存 / 工作区', 'workspace / reports / knowledge / ssh 可用。', C.warm),
        ]),
        column({ name: 'ops-right', width: 'fill', gap: 12, align: 'start' }, [
          tx('常见故障信号', S.sectionTiny, { name: 'ops-right-kicker' }),
          tx('先查代理和 worker', S.titleSmall, { name: 'ops-right-title', width: 'fill' }),
          bullet('页面能打开，但流不刷新', '优先查 SSE / WS / 缓冲与代理。', C.accent),
          bullet('接口 401 / 404', '先看 token、baseURL、/basic-api/api 是否对齐。', C.warm),
          bullet('日志有任务，UI 没事件', '常见是 Redis、Channels 或后端 worker 未就绪。', C.green),
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
      ]),
    ])
  );
  notes(slide, '这页是现场保护网。它告诉大家：真正要保的是闭环主线，实时链路和截图是兜底。');
}

function buildDeck() {
  const presentation = Presentation.create();
  const slides = [
    buildCover,
    buildWhy,
    buildPanorama,
    buildArchitecture,
    buildImplementation,
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
