import { marked } from "marked";
import type { AgentFinding, AgentTask } from "@/shared/api/agentTasks";

export interface ReportExportOptions {
	includeCodeSnippets: boolean;
	includeRemediation: boolean;
	includeMetadata: boolean;
	compactMode: boolean;
}

export const DEFAULT_REPORT_EXPORT_OPTIONS: ReportExportOptions = {
	includeCodeSnippets: true,
	includeRemediation: true,
	includeMetadata: true,
	compactMode: false,
};

type ReportTone = "neutral" | "success" | "warning" | "danger" | "info";

interface ReportMetricCard {
	label: string;
	value: string;
	detail?: string;
	tone: ReportTone;
}

interface ReportInfoCard {
	label: string;
	value: string;
	detail?: string;
}

interface ReportInfoGroup {
	title: string;
	cards: ReportInfoCard[];
}

interface ReportDistributionItem {
	label: string;
	count: number;
	percent: number;
	tone: ReportTone;
}

interface ReportTocEntry {
	id: string;
	label: string;
	level: number;
	fixed: boolean;
}

interface ReportFindingCard {
	id: string;
	severity: string;
	severityLabel: string;
	title: string;
	location: string;
	description: string;
	suggestion: string;
	codeSnippet: string;
	aiExplanation: string;
	isVerified: boolean;
}

export interface AgentAuditReportModel {
	title: string;
	subtitle: string;
	generatedAt: string;
	statusLabel: string;
	statusTone: ReportTone;
	scoreLabel: string;
	scoreValue: number;
	scoreTone: ReportTone;
	heroBadges: Array<{ label: string; tone: ReportTone }>;
	summaryCards: ReportMetricCard[];
	summaryBullets: Array<{ tone: ReportTone; text: string }>;
	sidebarGroups: ReportInfoGroup[];
	severityDistribution: ReportDistributionItem[];
	typeDistribution: ReportDistributionItem[];
	recommendations: Array<{ tone: ReportTone; text: string }>;
	topFindings: ReportFindingCard[];
	tocEntries: ReportTocEntry[];
	bodyHtml: string;
	hasBodyHeadings: boolean;
	includeMetadata: boolean;
	includeCodeSnippets: boolean;
	includeRemediation: boolean;
	compactMode: boolean;
}

const SCORE_LABELS: Array<{ min: number; label: string; tone: ReportTone }> = [
	{ min: 90, label: "优秀", tone: "success" },
	{ min: 80, label: "良好", tone: "success" },
	{ min: 70, label: "关注", tone: "warning" },
	{ min: 60, label: "偏高", tone: "warning" },
	{ min: 0, label: "高风险", tone: "danger" },
];

const STATUS_LABELS: Record<string, { label: string; tone: ReportTone }> = {
	pending: { label: "待开始", tone: "info" },
	initializing: { label: "初始化中", tone: "info" },
	running: { label: "进行中", tone: "info" },
	planning: { label: "规划中", tone: "info" },
	indexing: { label: "索引中", tone: "info" },
	analyzing: { label: "分析中", tone: "info" },
	verifying: { label: "验证中", tone: "warning" },
	reporting: { label: "报告生成中", tone: "warning" },
	completed: { label: "已完成", tone: "success" },
	failed: { label: "失败", tone: "danger" },
	cancelled: { label: "已取消", tone: "warning" },
};

const PHASE_LABELS: Record<string, string> = {
	planning: "规划阶段",
	indexing: "索引阶段",
	reconnaissance: "侦察阶段",
	analysis: "分析阶段",
	verification: "验证阶段",
	reporting: "报告阶段",
};

const SEVERITY_LABELS: Record<string, { label: string; tone: ReportTone }> = {
	critical: { label: "严重", tone: "danger" },
	high: { label: "高危", tone: "danger" },
	medium: { label: "中危", tone: "warning" },
	low: { label: "低危", tone: "info" },
	info: { label: "信息", tone: "neutral" },
	unknown: { label: "未知", tone: "neutral" },
};

const SEVERITY_THEME: Record<
	string,
	{ color: string; soft: string; border: string }
> = {
	critical: { color: "#b42318", soft: "#fef3f2", border: "#fca5a5" },
	high: { color: "#c2410c", soft: "#fff7ed", border: "#fdba74" },
	medium: { color: "#b45309", soft: "#fffbeb", border: "#fcd34d" },
	low: { color: "#0369a1", soft: "#f0f9ff", border: "#7dd3fc" },
	info: { color: "#475569", soft: "#f8fafc", border: "#cbd5e1" },
	unknown: { color: "#475569", soft: "#f8fafc", border: "#cbd5e1" },
};

const TONE_THEME: Record<
	ReportTone,
	{ color: string; soft: string; border: string }
> = {
	neutral: { color: "#334155", soft: "#f8fafc", border: "#dbe2ea" },
	success: { color: "#047857", soft: "#ecfdf5", border: "#a7f3d0" },
	warning: { color: "#b45309", soft: "#fffbeb", border: "#fcd34d" },
	danger: { color: "#b42318", soft: "#fef3f2", border: "#fda29b" },
	info: { color: "#2563eb", soft: "#eff6ff", border: "#bfdbfe" },
};

const FIXED_TOC_ENTRIES: Array<{
	id: string;
	label: string;
	level: number;
	fixed: true;
}> = [
	{ id: "summary", label: "摘要", level: 1, fixed: true },
	{ id: "report-body", label: "正文", level: 1, fixed: true },
];

export function serializeReportExportOptions(
	options: ReportExportOptions,
): string {
	return JSON.stringify({
		includeCodeSnippets: options.includeCodeSnippets,
		includeRemediation: options.includeRemediation,
		includeMetadata: options.includeMetadata,
		compactMode: options.compactMode,
	});
}

function normalizeOptions(
	options?: Partial<ReportExportOptions>,
): ReportExportOptions {
	return {
		...DEFAULT_REPORT_EXPORT_OPTIONS,
		...options,
	};
}

function escapeHtml(value: string): string {
	return value
		.replace(/&/g, "&amp;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;")
		.replace(/\"/g, "&quot;")
		.replace(/'/g, "&#39;");
}

function stripMarkdownInline(value: string): string {
	return value
		.replace(/<[^>]*>/g, "")
		.replace(/`([^`]+)`/g, "$1")
		.replace(/!\[([^\]]*)\]\([^)]*\)/g, "$1")
		.replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
		.replace(/[\*_~]/g, "")
		.replace(/\s+/g, " ")
		.trim();
}

function slugifyHeading(value: string): string {
	const normalized = stripMarkdownInline(value)
		.normalize("NFKC")
		.toLowerCase()
		.replace(/[^\p{L}\p{N}]+/gu, "-")
		.replace(/^-+|-+$/g, "");

	return normalized || "section";
}

function uniqueId(base: string, usedIds: Set<string>): string {
	let candidate = base;
	let counter = 2;

	while (usedIds.has(candidate)) {
		candidate = `${base}-${counter}`;
		counter += 1;
	}

	usedIds.add(candidate);
	return candidate;
}

function truncateText(value: string, maxLength: number): string {
	if (value.length <= maxLength) {
		return value;
	}
	return `${value.slice(0, Math.max(0, maxLength - 1)).trimEnd()}…`;
}

function truncateMultiline(
	value: string,
	maxLines: number,
	maxLength: number,
): string {
	const limitedLength = truncateText(value, maxLength);
	const lines = limitedLength.split(/\r?\n/);
	if (lines.length <= maxLines) {
		return limitedLength;
	}
	return `${lines.slice(0, maxLines).join("\n")}\n…`;
}

function stripCodeBlocksFromHtml(html: string): string {
	if (!html.trim()) {
		return html;
	}

	if (typeof document === "undefined") {
		return html.replace(/<pre\b[^>]*>[\s\S]*?<\/pre>/gi, "");
	}

	const wrapper = document.createElement("template");
	wrapper.innerHTML = html;
	wrapper.content.querySelectorAll("pre").forEach((node) => node.remove());
	return wrapper.innerHTML;
}

function formatDateTime(value?: string | null): string {
	if (!value) {
		return "—";
	}

	const date = new Date(value);
	if (Number.isNaN(date.getTime())) {
		return value;
	}

	const pad = (n: number) => String(n).padStart(2, "0");
	return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function formatDuration(totalMs: number): string {
	if (!Number.isFinite(totalMs) || totalMs <= 0) {
		return "—";
	}

	const totalSeconds = Math.max(0, Math.round(totalMs / 1000));
	const hours = Math.floor(totalSeconds / 3600);
	const minutes = Math.floor((totalSeconds % 3600) / 60);
	const seconds = totalSeconds % 60;

	if (hours > 0) {
		return `${hours}h ${minutes}m ${seconds}s`;
	}
	if (minutes > 0) {
		return `${minutes}m ${seconds}s`;
	}
	return `${seconds}s`;
}

function formatRatio(numerator: number, denominator: number): string {
	if (
		!Number.isFinite(numerator) ||
		!Number.isFinite(denominator) ||
		denominator <= 0
	) {
		return "—";
	}
	return `${numerator}/${denominator}`;
}

function formatPercent(numerator: number, denominator: number): string {
	if (
		!Number.isFinite(numerator) ||
		!Number.isFinite(denominator) ||
		denominator <= 0
	) {
		return "0%";
	}
	return `${Math.round((numerator / denominator) * 100)}%`;
}

function normalizeSeverity(value: string | null | undefined): string {
	const severity = String(value || "")
		.trim()
		.toLowerCase();
	return severity && severity in SEVERITY_LABELS ? severity : "unknown";
}

function getScoreMeta(score: number): { label: string; tone: ReportTone } {
	return (
		SCORE_LABELS.find((item) => score >= item.min) ||
		SCORE_LABELS[SCORE_LABELS.length - 1]
	);
}

function formatStatus(value?: string | null): {
	label: string;
	tone: ReportTone;
} {
	const key = String(value || "")
		.trim()
		.toLowerCase();
	return (
		STATUS_LABELS[key] || {
			label: key ? key.toUpperCase() : "未知",
			tone: "neutral",
		}
	);
}

function formatPhase(value?: string | null): string {
	const key = String(value || "")
		.trim()
		.toLowerCase();
	return PHASE_LABELS[key] || (key ? key : "—");
}

function formatSeverityLabel(value?: string | null): {
	label: string;
	tone: ReportTone;
} {
	const key = normalizeSeverity(value);
	return SEVERITY_LABELS[key];
}

function getSeverityTheme(value?: string | null): {
	color: string;
	soft: string;
	border: string;
} {
	const key = normalizeSeverity(value);
	return SEVERITY_THEME[key];
}

function humanizeIdentifier(value: string): string {
	const cleaned = String(value || "")
		.replace(/[_-]+/g, " ")
		.trim();
	if (!cleaned) {
		return "未知类型";
	}

	return cleaned
		.split(/\s+/)
		.map((part) =>
			part ? `${part.charAt(0).toUpperCase()}${part.slice(1)}` : part,
		)
		.join(" ");
}

function getTaskDurationMs(task: AgentTask): number {
	const startedAt = task.started_at ? new Date(task.started_at).getTime() : NaN;
	const completedAt = task.completed_at
		? new Date(task.completed_at).getTime()
		: NaN;
	const now = Date.now();

	if (Number.isFinite(startedAt)) {
		if (Number.isFinite(completedAt)) {
			return Math.max(0, completedAt - startedAt);
		}
		if (
			STATUS_LABELS[String(task.status || "").toLowerCase()]?.label === "进行中"
		) {
			return Math.max(0, now - startedAt);
		}
	}

	return 0;
}

function getCoverageLabel(task: AgentTask): string {
	const analyzedFiles = Number(
		task.analyzed_files || task.resolved_file_count || task.indexed_files || 0,
	);
	const totalFiles = Number(task.total_files || 0);

	if (analyzedFiles <= 0 && totalFiles <= 0) {
		return "—";
	}

	if (totalFiles > 0) {
		return `${analyzedFiles}/${totalFiles}`;
	}

	return `${analyzedFiles}`;
}

function buildSeverityCounts(
	findings: AgentFinding[],
	task: AgentTask,
): Record<string, number> {
	if (findings.length === 0) {
		return {
			critical: Number(task.critical_count || 0),
			high: Number(task.high_count || 0),
			medium: Number(task.medium_count || 0),
			low: Number(task.low_count || 0),
			info: 0,
			unknown: 0,
		};
	}

	const counts: Record<string, number> = {
		critical: 0,
		high: 0,
		medium: 0,
		low: 0,
		info: 0,
		unknown: 0,
	};

	for (const finding of findings) {
		const severity = normalizeSeverity(finding.severity);
		counts[severity] = (counts[severity] || 0) + 1;
	}

	return counts;
}

function buildTypeCounts(findings: AgentFinding[]): Record<string, number> {
	const counts: Record<string, number> = {};

	for (const finding of findings) {
		const rawType = String(
			finding.vulnerability_type || finding.title || "未知类型",
		).trim();
		const key = rawType || "未知类型";
		counts[key] = (counts[key] || 0) + 1;
	}

	return counts;
}

function buildDistributionItems(
	counts: Record<string, number>,
	order: string[],
	total: number,
	labels: Record<string, { label: string; tone: ReportTone }> = {},
): ReportDistributionItem[] {
	return order.map((key) => {
		const count = Number(counts[key] || 0);
		const meta = labels[key] || { label: key, tone: "neutral" as ReportTone };
		return {
			label: meta.label,
			count,
			percent: total > 0 ? Math.round((count / total) * 100) : 0,
			tone: meta.tone,
		};
	});
}

function buildTopTypes(
	findings: AgentFinding[],
	limit = 6,
): ReportDistributionItem[] {
	const counts = buildTypeCounts(findings);
	const entries = Object.entries(counts)
		.map(([label, count]) => ({ label: humanizeIdentifier(label), count }))
		.sort((a, b) => b.count - a.count || a.label.localeCompare(b.label));

	const top = entries.slice(0, limit);
	const remaining = entries
		.slice(limit)
		.reduce((sum, item) => sum + item.count, 0);
	if (remaining > 0) {
		top.push({ label: "其他", count: remaining });
	}

	const total = top.reduce((sum, item) => sum + item.count, 0);
	return top.map((item) => ({
		label: item.label,
		count: item.count,
		percent: total > 0 ? Math.round((item.count / total) * 100) : 0,
		tone: "neutral",
	}));
}

function extractMarkdownHeadings(
	markdown: string,
): Array<{ level: number; label: string; id: string }> {
	if (!markdown.trim()) {
		return [];
	}

	const headings: Array<{ level: number; label: string; id: string }> = [];
	const usedIds = new Set<string>(FIXED_TOC_ENTRIES.map((item) => item.id));
	const lines = markdown.split(/\r?\n/);
	let inFence = false;
	let fenceMarker = "";

	for (const rawLine of lines) {
		const line = rawLine.trimEnd();
		const fenceMatch = line.match(/^(\s*)(`{3,}|~{3,})/);
		if (fenceMatch) {
			const marker = fenceMatch[2];
			if (!inFence) {
				inFence = true;
				fenceMarker = marker[0];
			} else if (fenceMarker === marker[0]) {
				inFence = false;
				fenceMarker = "";
			}
			continue;
		}

		if (inFence) {
			continue;
		}

		const match = line.match(/^(#{1,6})\s+(.+?)\s*$/);
		if (!match) {
			continue;
		}

		const level = match[1].length;
		const label = stripMarkdownInline(match[2]);
		if (!label) {
			continue;
		}

		const id = uniqueId(slugifyHeading(label), usedIds);
		headings.push({ level, label, id });
	}

	return headings;
}

function injectHeadingAnchors(
	html: string,
	headings: Array<{ level: number; label: string; id: string }>,
): string {
	if (!html || headings.length === 0 || typeof document === "undefined") {
		return html;
	}

	const wrapper = document.createElement("template");
	wrapper.innerHTML = html;

	const headingNodes = wrapper.content.querySelectorAll(
		"h1, h2, h3, h4, h5, h6",
	);
	headingNodes.forEach((node, index) => {
		const heading = headings[index];
		if (!heading) {
			return;
		}

		node.id = heading.id;
	});

	wrapper.content.querySelectorAll("a").forEach((anchor) => {
		anchor.setAttribute("target", "_blank");
		anchor.setAttribute("rel", "noopener noreferrer");
	});

	return wrapper.innerHTML;
}

function buildFindingLocation(finding: AgentFinding): string {
	const filePath = String(finding.file_path || "").trim();
	const lineStart = finding.line_start ?? null;
	const lineEnd = finding.line_end ?? null;

	if (!filePath) {
		return lineStart != null ? `行 ${lineStart}` : "未提供位置";
	}

	if (lineStart != null && lineEnd != null && lineEnd !== lineStart) {
		return `${filePath}:${lineStart}-${lineEnd}`;
	}

	if (lineStart != null) {
		return `${filePath}:${lineStart}`;
	}

	return filePath;
}

function sortFindings(findings: AgentFinding[]): AgentFinding[] {
	const severityRank: Record<string, number> = {
		critical: 0,
		high: 1,
		medium: 2,
		low: 3,
		info: 4,
		unknown: 5,
	};

	return [...findings].sort((left, right) => {
		const leftSeverity = severityRank[normalizeSeverity(left.severity)] ?? 5;
		const rightSeverity = severityRank[normalizeSeverity(right.severity)] ?? 5;

		if (leftSeverity !== rightSeverity) {
			return leftSeverity - rightSeverity;
		}

		const leftLocation = buildFindingLocation(left);
		const rightLocation = buildFindingLocation(right);
		return leftLocation.localeCompare(rightLocation);
	});
}

function buildSummaryCards(
	task: AgentTask,
	findings: AgentFinding[],
	severityCounts: Record<string, number>,
): ReportMetricCard[] {
	const scoreValue = Number(task.security_score || 0);
	const scoreMeta = getScoreMeta(scoreValue);
	const totalFindings = findings.length || Number(task.findings_count || 0);
	const highRiskCount =
		Number(severityCounts.critical || 0) + Number(severityCounts.high || 0);
	const verifiedCount = findings.length
		? findings.filter((item) => item.is_verified).length
		: Number(task.verified_count || 0);
	const analyzedFiles = Number(
		task.analyzed_files || task.resolved_file_count || task.indexed_files || 0,
	);
	const totalFiles = Number(task.total_files || 0);

	return [
		{
			label: "安全评分",
			value: `${scoreValue.toFixed(0)}/100`,
			detail: scoreMeta.label,
			tone: scoreMeta.tone,
		},
		{
			label: "高优先级问题",
			value: `${highRiskCount}`,
			detail: `严重 ${Number(severityCounts.critical || 0)} · 高危 ${Number(severityCounts.high || 0)}`,
			tone: highRiskCount > 0 ? "danger" : "success",
		},
		{
			label: "文件覆盖",
			value: getCoverageLabel(task),
			detail:
				totalFiles > 0
					? `${formatPercent(analyzedFiles, totalFiles)} 覆盖`
					: "已覆盖文件数",
			tone: "info",
		},
		{
			label: "验证率",
			value: totalFindings > 0 ? `${verifiedCount}/${totalFindings}` : "—",
			detail:
				totalFindings > 0
					? `${formatPercent(verifiedCount, totalFindings)} 已验证`
					: "暂无发现",
			tone: verifiedCount > 0 ? "success" : "neutral",
		},
	];
}

function buildSummaryBullets(
	task: AgentTask,
	findings: AgentFinding[],
	severityCounts: Record<string, number>,
	scoreLabel: string,
	includeRemediation: boolean,
): Array<{ tone: ReportTone; text: string }> {
	const totalFindings = findings.length || Number(task.findings_count || 0);
	const highRiskCount =
		Number(severityCounts.critical || 0) + Number(severityCounts.high || 0);
	const verifiedCount = findings.length
		? findings.filter((item) => item.is_verified).length
		: Number(task.verified_count || 0);
	const falsePositiveCount = Number(task.false_positive_count || 0);
	const analyzedFiles = Number(
		task.analyzed_files || task.resolved_file_count || task.indexed_files || 0,
	);
	const totalFiles = Number(task.total_files || 0);
	const coverageLabel = getCoverageLabel(task);
	const duration = formatDuration(getTaskDurationMs(task));
	const elapsedLabel = duration === "—" ? "未记录耗时" : duration;

	if (totalFindings === 0) {
		const bullets: Array<{ tone: ReportTone; text: string }> = [
			{
				tone: "success",
				text: `本次审计未产出可展示的结构化问题项，当前安全评分 ${Number(task.security_score || 0).toFixed(0)}/100，整体风险偏低。`,
			},
			{
				tone: "info",
				text:
					totalFiles > 0
						? `审计覆盖 ${coverageLabel} 个文件（总计 ${totalFiles} 个），耗时 ${elapsedLabel}。`
						: `审计耗时 ${elapsedLabel}，当前尚未提供完整文件总量信息。`,
			},
		];

		if (includeRemediation) {
			bullets.push({
				tone: "warning",
				text: `建议在交付前复核覆盖范围与关键结论，确保后续补测或回归时可以快速定位。`,
			});
		}

		return bullets;
	}

	const bullets: Array<{ tone: ReportTone; text: string }> = [
		{
			tone: highRiskCount > 0 ? "danger" : "success",
			text: `本次审计共识别 ${totalFindings} 个问题，其中 ${Number(severityCounts.critical || 0)} 个严重、${Number(severityCounts.high || 0)} 个高危，安全评分 ${Number(task.security_score || 0).toFixed(0)}/100（${scoreLabel}）。`,
		},
		{
			tone: verifiedCount > 0 ? "success" : "info",
			text: `审计覆盖 ${coverageLabel} 个文件，累计 ${Number(task.tool_calls_count || 0)} 次工具调用、${Number(task.total_iterations || 0)} 次执行迭代，已验证 ${verifiedCount} 个问题${falsePositiveCount > 0 ? `，并标记 ${falsePositiveCount} 个误报` : ""}。`,
		},
		{
			tone: highRiskCount > 0 ? "warning" : "info",
			text:
			highRiskCount > 0
				? `建议优先处理 ${highRiskCount} 个高优先级问题，并对 ${Number(new Set(findings.map((item) => String(item.file_path || "").trim()).filter(Boolean)).size)} 个受影响文件进行回归验证。`
				: `当前未发现高优先级问题，建议继续关注修复建议的一致性和回归验证结果。`,
		},
	];

	return includeRemediation ? bullets : bullets.slice(0, 2);
}

function buildSidebarGroups(
	task: AgentTask,
	findings: AgentFinding[],
	severityCounts: Record<string, number>,
): ReportInfoGroup[] {
	const analyzedFiles = Number(
		task.analyzed_files || task.resolved_file_count || task.indexed_files || 0,
	);
	const totalFiles = Number(task.total_files || 0);
	const totalFindings = findings.length || Number(task.findings_count || 0);
	const scoreValue = Number(task.security_score || 0);

	return [
		{
			title: "任务信息",
			cards: [
				{ label: "任务 ID", value: task.id || "—" },
				{ label: "项目 ID", value: task.project_id || "—" },
				{
					label: "分支",
					value: task.branch_name || "—",
					detail: task.repository_type
						? `仓库类型：${task.repository_type}`
						: undefined,
				},
				{
					label: "状态",
					value: formatStatus(task.status).label,
					detail: formatPhase(task.current_phase),
				},
				{ label: "当前步骤", value: task.current_step || "—" },
				{
					label: "工作区来源",
					value: task.workspace_source || "—",
					detail: task.repository_signature || undefined,
				},
			],
		},
		{
			title: "执行统计",
			cards: [
				{ label: "开始时间", value: formatDateTime(task.started_at) },
				{ label: "完成时间", value: formatDateTime(task.completed_at) },
				{ label: "耗时", value: formatDuration(getTaskDurationMs(task)) },
				{
					label: "文件覆盖",
					value: getCoverageLabel(task),
					detail:
						totalFiles > 0
							? `${analyzedFiles}/${totalFiles} 已处理`
							: undefined,
				},
				{
					label: "问题总数",
					value: `${totalFindings || 0}`,
					detail:
						totalFindings > 0
							? `严重 ${Number(severityCounts.critical || 0)} · 高危 ${Number(severityCounts.high || 0)}`
							: "暂无发现",
				},
				{
					label: "安全评分",
					value: `${scoreValue.toFixed(0)}/100`,
					detail: getScoreMeta(scoreValue).label,
				},
				{
					label: "工具调用",
					value: `${Number(task.tool_calls_count || 0)}`,
					detail: `${Number(task.total_iterations || 0)} 次迭代`,
				},
				{
					label: "tokens",
					value: `${Number(task.tokens_used || 0)}`,
					detail: Number(task.tokens_used || 0) > 0 ? "累计消耗" : "暂无数据",
				},
			],
		},
	];
}

function buildTopFindings(
	findings: AgentFinding[],
	options: ReportExportOptions,
): ReportFindingCard[] {
	return sortFindings(findings)
		.slice(0, 5)
		.map((finding, index) => {
			const severityMeta = formatSeverityLabel(finding.severity);
			const title =
				String(
					finding.title || finding.vulnerability_type || `发现 ${index + 1}`,
				).trim() || `发现 ${index + 1}`;
			const description = String(
				finding.description || finding.ai_explanation || "暂无详细描述",
			).trim();
			const suggestion = String(
				finding.suggestion ||
					finding.fix_code ||
					finding.ai_explanation ||
					"暂无修复建议",
			).trim();
			const codeSnippet = options.includeCodeSnippets
				? truncateMultiline(String(finding.code_snippet || "").trim(), 14, 1200)
				: "";
			const aiExplanation = String(finding.ai_explanation || "").trim();

			return {
				id: String(finding.id || `finding-${index}`),
				severity: normalizeSeverity(finding.severity),
				severityLabel: severityMeta.label,
				title,
				location: buildFindingLocation(finding),
				description,
				suggestion,
				codeSnippet,
				aiExplanation,
				isVerified: Boolean(finding.is_verified),
			};
		});
}

function buildRecommendations(
	task: AgentTask,
	findings: AgentFinding[],
	severityCounts: Record<string, number>,
): Array<{ tone: ReportTone; text: string }> {
	const highRiskCount =
		Number(severityCounts.critical || 0) + Number(severityCounts.high || 0);
	const verifiedCount = findings.length
		? findings.filter((item) => item.is_verified).length
		: Number(task.verified_count || 0);
	const falsePositiveCount = Number(task.false_positive_count || 0);
	const affectedFilesCount = findings.length
		? new Set(
				findings
					.map((item) => String(item.file_path || "").trim())
					.filter(Boolean),
			).size
		: Number(task.files_with_findings || 0);
	const coverageLabel = getCoverageLabel(task);

	const items: Array<{ tone: ReportTone; text: string }> = [];

	if (highRiskCount > 0) {
		items.push({
			tone: "danger",
			text: `优先修复 ${highRiskCount} 个高优先级问题，并对相关文件进行回归验证。`,
		});
	}

	items.push({
		tone: "info",
		text: `结合问题项中的代码片段和修复建议，梳理可复用的整改模式，避免同类问题再次出现。`,
	});

	if (verifiedCount > 0 || falsePositiveCount > 0) {
		items.push({
			tone: "warning",
			text: `保留 ${verifiedCount} 个已验证问题和 ${falsePositiveCount} 个误报的处置记录，方便后续复盘和审计追踪。`,
		});
	}

	items.push({
		tone: "success",
		text:
			affectedFilesCount > 0
				? `当前命中覆盖 ${coverageLabel} 个文件，建议修复后重跑审计以确认相关文件全部回归通过。`
				: `建议在修复后重跑审计，确认覆盖范围内的核心路径已稳定通过。`,
	});

	return items.slice(0, 3);
}

function renderMetricCards(cards: ReportMetricCard[], compact = false): string {
	return cards
		.map((card) => {
			const theme = TONE_THEME[card.tone];
			return `
        <article class="summary-card ${compact ? "summary-card--compact" : ""}" data-tone="${card.tone}" style="--card-color:${theme.color};--card-soft:${theme.soft};--card-border:${theme.border};">
          <div class="summary-card__label">${escapeHtml(card.label)}</div>
          <div class="summary-card__value">${escapeHtml(card.value)}</div>
          ${card.detail ? `<div class="summary-card__detail">${escapeHtml(card.detail)}</div>` : ""}
        </article>
      `;
		})
		.join("");
}

function renderSummaryBullets(
	items: Array<{ tone: ReportTone; text: string }>,
): string {
	return items
		.map((item) => {
			const theme = TONE_THEME[item.tone];
			return `<li class="summary-bullet" style="--bullet-color:${theme.color};--bullet-soft:${theme.soft};">${escapeHtml(item.text)}</li>`;
		})
		.join("");
}

function renderInfoGroups(groups: ReportInfoGroup[]): string {
	return groups
		.map((group) => {
			return `
        <section class="sidebar-group">
          <div class="sidebar-group__title">${escapeHtml(group.title)}</div>
          <div class="sidebar-fact-list">
            ${group.cards
							.map((card) => {
								return `
                  <article class="sidebar-fact">
                    <div class="sidebar-fact__label">${escapeHtml(card.label)}</div>
                    <div class="sidebar-fact__value">${escapeHtml(card.value)}</div>
                    ${card.detail ? `<div class="sidebar-fact__detail">${escapeHtml(card.detail)}</div>` : ""}
                  </article>
                `;
							})
							.join("")}
          </div>
        </section>
      `;
		})
		.join("");
}

function renderDistributionBar(
	items: ReportDistributionItem[],
	prefix: string,
): string {
	const total = items.reduce((sum, item) => sum + item.count, 0);
	if (total <= 0) {
		return `<div class="distribution-empty">暂无数据</div>`;
	}

	return `
    <div class="distribution-bar ${prefix}">
      ${items
				.map((item) => {
					const theme = TONE_THEME[item.tone];
					return `<span class="distribution-bar__segment" style="width:${item.percent || 0}%;background:${theme.color};" title="${escapeHtml(item.label)}：${item.count}"></span>`;
				})
				.join("")}
    </div>
  `;
}

function renderDistributionLegend(items: ReportDistributionItem[]): string {
	return items
		.map((item) => {
			const theme = TONE_THEME[item.tone];
			return `
        <div class="legend-item">
          <span class="legend-item__dot" style="background:${theme.color};"></span>
          <span class="legend-item__label">${escapeHtml(item.label)}</span>
          <span class="legend-item__count">${item.count}</span>
        </div>
      `;
		})
		.join("");
}

function renderTypePills(items: ReportDistributionItem[]): string {
	if (items.length === 0) {
		return `<div class="distribution-empty">暂无数据</div>`;
	}

	return items
		.map((item) => {
			return `
        <div class="type-pill">
          <div class="type-pill__label">${escapeHtml(item.label)}</div>
          <div class="type-pill__meta">${item.count} · ${item.percent}%</div>
        </div>
      `;
		})
		.join("");
}

function renderRecommendations(
	items: Array<{ tone: ReportTone; text: string }>,
): string {
	return items
		.map((item) => {
			const theme = TONE_THEME[item.tone];
			return `
        <li class="recommendation-item" style="--recommendation-color:${theme.color};--recommendation-soft:${theme.soft};">
          ${escapeHtml(item.text)}
        </li>
      `;
		})
		.join("");
}

function renderToc(entries: ReportTocEntry[]): string {
	if (entries.length === 0) {
		return `<div class="distribution-empty">暂无目录</div>`;
	}

	return `
    <nav class="toc-list" aria-label="报告目录">
      ${entries
				.map((entry) => {
					return `
            <a class="toc-item toc-item--level-${Math.min(entry.level, 6)} ${entry.fixed ? "toc-item--fixed" : ""}" href="#${escapeHtml(entry.id)}">
              <span class="toc-item__bullet">${entry.fixed ? "•" : "◦"}</span>
              <span class="toc-item__label">${escapeHtml(entry.label)}</span>
            </a>
          `;
				})
				.join("")}
    </nav>
  `;
}

function renderFindings(
	findings: ReportFindingCard[],
	options: ReportExportOptions,
): string {
	if (findings.length === 0) {
		return `
      <div class="empty-state">
        <div class="empty-state__title">暂无可展示的问题项</div>
        <div class="empty-state__text">当前报告没有结构化问题项，说明本次审计未识别出可单独列出的 Findings。</div>
      </div>
    `;
	}

	return findings
		.map((finding) => {
			const theme = getSeverityTheme(finding.severity);
			return `
        <article class="finding-card" style="--finding-color:${theme.color};--finding-soft:${theme.soft};--finding-border:${theme.border};">
          <div class="finding-card__header">
            <div class="finding-card__badges">
              <span class="severity-badge">${escapeHtml(finding.severityLabel)}</span>
              ${finding.isVerified ? `<span class="verified-badge">已验证</span>` : ""}
            </div>
            <div class="finding-card__location">${escapeHtml(finding.location)}</div>
          </div>
          <h3 class="finding-card__title">${escapeHtml(finding.title)}</h3>
          <p class="finding-card__description">${escapeHtml(finding.description)}</p>
          ${
						options.includeRemediation && finding.suggestion
							? `
            <div class="finding-card__section">
              <div class="finding-card__section-title">修复建议</div>
              <div class="finding-card__section-text">${escapeHtml(finding.suggestion)}</div>
            </div>
          `
							: ""
					}
          ${
						finding.aiExplanation
							? `
            <details class="finding-card__details">
              <summary>分析说明</summary>
              <div class="finding-card__section-text">${escapeHtml(finding.aiExplanation)}</div>
            </details>
          `
							: ""
					}
          ${
						options.includeCodeSnippets && finding.codeSnippet
							? `
            <div class="finding-card__code-wrap">
              <div class="finding-card__section-title">代码片段</div>
              <pre class="finding-card__code"><code>${escapeHtml(finding.codeSnippet)}</code></pre>
            </div>
          `
							: ""
					}
        </article>
      `;
		})
		.join("");
}

function renderMarkdownBody(bodyHtml: string): string {
	if (!bodyHtml.trim()) {
		return `<div class="empty-state"><div class="empty-state__title">暂无正文内容</div><div class="empty-state__text">后端没有返回 markdown 报告正文。</div></div>`;
	}

	return `<article class="report-body markdown-body">${bodyHtml}</article>`;
}

function buildScoreMeter(
	scoreValue: number,
	scoreTone: ReportTone,
	scoreLabel: string,
): string {
	const percent = Math.max(0, Math.min(100, scoreValue));
	const theme = TONE_THEME[scoreTone];
	return `
    <div class="score-meter" style="--score:${percent};--score-color:${theme.color};--score-soft:${theme.soft};">
      <div class="score-meter__ring">
        <div class="score-meter__inner">
          <div class="score-meter__value">${percent.toFixed(0)}</div>
          <div class="score-meter__label">${escapeHtml(scoreLabel)}</div>
        </div>
      </div>
    </div>
  `;
}

function buildBodyClass(options: ReportExportOptions): string {
	return ["report-shell", options.compactMode ? "report-shell--compact" : ""]
		.filter(Boolean)
		.join(" ");
}

function renderHtmlDocument(model: AgentAuditReportModel): string {
	const summaryBullets = renderSummaryBullets(model.summaryBullets);
	const toc = renderToc(model.tocEntries);
	const body = renderMarkdownBody(model.bodyHtml);

	return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="color-scheme" content="light">
  <meta name="theme-color" content="#f8fbff">
  <title>AgentAudit Report - ${escapeHtml(model.title)}</title>
  <style>
    :root {
      --page-bg: #eef2f7;
      --panel-bg: #ffffff;
      --panel-soft: #f8fbff;
      --panel-strong: #eef4fb;
      --border: #dbe2ea;
      --border-strong: #c9d5e3;
      --text-primary: #0f172a;
      --text-secondary: #475569;
      --text-muted: #64748b;
      --accent: #2563eb;
      --accent-soft: rgba(37, 99, 235, 0.1);
      --shadow: 0 18px 45px rgba(15, 23, 42, 0.08);
      --radius-xl: 20px;
      --radius-lg: 16px;
      --radius-md: 12px;
      --radius-sm: 10px;
      color-scheme: light;
    }

    * {
      box-sizing: border-box;
    }

    html {
      scroll-behavior: smooth;
      background: var(--page-bg);
    }

    body {
      margin: 0;
      font-family: Inter, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Helvetica Neue", Arial, sans-serif;
      background:
        radial-gradient(circle at top right, rgba(37, 99, 235, 0.12), transparent 26%),
        radial-gradient(circle at bottom left, rgba(14, 165, 233, 0.08), transparent 22%),
        linear-gradient(180deg, #f8fbff 0%, #eef2f7 100%);
      color: var(--text-secondary);
      line-height: 1.65;
      font-size: 14px;
    }

    a {
      color: var(--accent);
      text-decoration: none;
    }

    a:hover {
      text-decoration: underline;
    }

    .report-layout {
      max-width: 1320px;
      margin: 0 auto;
      display: grid;
      grid-template-columns: minmax(280px, 320px) minmax(0, 1fr);
      gap: 20px;
      align-items: start;
    }

    .report-sidebar {
      position: sticky;
      top: 24px;
      align-self: start;
      display: flex;
      flex-direction: column;
      gap: 14px;
      max-height: calc(100vh - 48px);
      overflow: auto;
      padding-right: 4px;
    }

    .report-main {
      min-width: 0;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .sidebar-panel,
    .report-header {
      background: rgba(255, 255, 255, 0.94);
      backdrop-filter: blur(12px);
      border: 1px solid rgba(219, 226, 234, 0.95);
      box-shadow: var(--shadow);
      border-radius: var(--radius-xl);
    }

    .sidebar-panel {
      padding: 16px;
      overflow-x: hidden;
    }

    .sidebar-panel__header {
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 12px;
    }

    .sidebar-panel__title {
      margin: 0;
      color: var(--text-primary);
      font-size: 15px;
      font-weight: 700;
    }

    .sidebar-panel__hint {
      color: var(--text-muted);
      font-size: 12px;
      white-space: nowrap;
    }

    .sidebar-brand {
      padding: 18px;
      background:
        radial-gradient(circle at top right, rgba(37, 99, 235, 0.12), transparent 24%),
        radial-gradient(circle at bottom left, rgba(14, 165, 233, 0.08), transparent 22%),
        rgba(255, 255, 255, 0.96);
    }

    .sidebar-brand__eyebrow {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 5px 10px;
      border-radius: 999px;
      background: #eff6ff;
      color: #1d4ed8;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }

    .sidebar-brand__title {
      margin: 12px 0 8px;
      color: var(--text-primary);
      font-size: 20px;
      line-height: 1.2;
      letter-spacing: -0.03em;
    }

    .sidebar-brand__subtitle {
      margin: 0;
      color: var(--text-secondary);
      font-size: 13px;
      line-height: 1.6;
    }

    .sidebar-brand__chips,
    .sidebar-brand__meta {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 12px;
    }

    .sidebar-brand__meta {
      color: var(--text-muted);
      font-size: 12px;
    }

    .sidebar-brand__score {
      margin-top: 14px;
    }

    .summary-grid--compact {
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
    }

    .summary-card--compact {
      padding: 12px;
      border-radius: 14px;
    }

    .summary-card--compact .summary-card__label {
      margin-bottom: 6px;
      font-size: 10px;
    }

    .summary-card--compact .summary-card__value {
      font-size: 20px;
    }

    .summary-card--compact .summary-card__detail {
      margin-top: 6px;
      font-size: 11px;
    }

    .sidebar-group {
      display: grid;
      gap: 10px;
      padding: 14px 0 0;
    }

    .sidebar-group + .sidebar-group {
      border-top: 1px solid #e2e8f0;
      padding-top: 14px;
    }

    .sidebar-group__title {
      color: var(--text-primary);
      font-size: 13px;
      font-weight: 700;
      letter-spacing: 0.04em;
    }

    .sidebar-fact-list {
      display: grid;
      gap: 8px;
    }

    .sidebar-fact {
      padding: 10px 12px;
      border-radius: 12px;
      border: 1px solid var(--border);
      background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
      min-width: 0;
    }

    .sidebar-fact__label {
      color: var(--text-muted);
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 4px;
      font-weight: 700;
    }

    .sidebar-fact__value {
      color: var(--text-primary);
      font-size: 13px;
      font-weight: 700;
      word-break: break-word;
    }

    .sidebar-fact__detail {
      margin-top: 4px;
      color: var(--text-muted);
      font-size: 11px;
      word-break: break-word;
    }

    .report-header {
      padding: 24px;
    }

    .report-header__eyebrow {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 12px;
      border-radius: 999px;
      background: #eff6ff;
      color: #1d4ed8;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      font-size: 11px;
    }

    .report-header__title {
      margin: 14px 0 10px;
      font-size: clamp(28px, 3vw, 40px);
      line-height: 1.12;
      color: var(--text-primary);
      letter-spacing: -0.03em;
    }

    .report-header__subtitle {
      margin: 0;
      max-width: 860px;
      font-size: 15px;
      color: var(--text-secondary);
    }

    .report-header__chips,
    .report-header__meta {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 14px;
    }

    .report-shell {
      min-height: 100vh;
      padding: 28px 18px 48px;
      color: var(--text-secondary);
    }

    .report-shell--compact {
      padding: 18px 14px 32px;
    }

    .report-page {
      max-width: 1160px;
      margin: 0 auto;
      display: flex;
      flex-direction: column;
      gap: 18px;
    }

    .report-hero,
    .report-section,
    .report-footer {
      background: rgba(255, 255, 255, 0.9);
      backdrop-filter: blur(12px);
      border: 1px solid rgba(219, 226, 234, 0.9);
      box-shadow: var(--shadow);
      border-radius: var(--radius-xl);
    }

    .report-hero {
      padding: 24px;
      position: relative;
      overflow: hidden;
    }

    .report-hero::before,
    .report-hero::after {
      content: "";
      position: absolute;
      border-radius: 999px;
      pointer-events: none;
      filter: blur(4px);
    }

    .report-hero::before {
      width: 220px;
      height: 220px;
      right: -60px;
      top: -70px;
      background: rgba(37, 99, 235, 0.1);
    }

    .report-hero::after {
      width: 160px;
      height: 160px;
      right: 140px;
      bottom: -60px;
      background: rgba(14, 165, 233, 0.08);
    }

    .hero-layout {
      position: relative;
      display: grid;
      grid-template-columns: minmax(0, 1.6fr) minmax(300px, 0.8fr);
      gap: 20px;
      align-items: center;
    }

    .hero-copy {
      min-width: 0;
    }

    .hero-eyebrow {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 12px;
      border-radius: 999px;
      background: #eff6ff;
      color: #1d4ed8;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      font-size: 11px;
    }

    .hero-title {
      margin: 14px 0 10px;
      font-size: clamp(28px, 3vw, 42px);
      line-height: 1.12;
      color: var(--text-primary);
      letter-spacing: -0.03em;
    }

    .hero-subtitle {
      margin: 0;
      max-width: 760px;
      font-size: 15px;
      color: var(--text-secondary);
    }

    .hero-badges,
    .hero-meta-strip {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 16px;
    }

    .hero-meta-strip {
      margin-top: 14px;
    }

    .meta-chip,
    .hero-chip,
    .severity-badge,
    .verified-badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 10px;
      border-radius: 999px;
      border: 1px solid var(--border);
      background: #ffffff;
      color: var(--text-secondary);
      font-size: 12px;
      font-weight: 600;
    }

    .hero-chip[data-tone="info"],
    .meta-chip,
    .summary-card[data-tone="info"] {
      background: #eff6ff;
      border-color: #bfdbfe;
      color: #1d4ed8;
    }

    .hero-chip[data-tone="success"],
    .summary-card[data-tone="success"] .summary-card__value,
    .summary-card[data-tone="success"] .summary-card__detail {
      color: #047857;
    }

    .hero-chip[data-tone="warning"] {
      background: #fffbeb;
      border-color: #fcd34d;
      color: #b45309;
    }

    .hero-chip[data-tone="danger"] {
      background: #fef2f2;
      border-color: #fca5a5;
      color: #b42318;
    }

    .hero-aside {
      display: flex;
      flex-direction: column;
      align-items: stretch;
      gap: 14px;
    }

    .score-meter {
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 10px;
      border-radius: 22px;
      background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
      border: 1px solid var(--border);
    }

    .score-meter__ring {
      width: 156px;
      height: 156px;
      border-radius: 50%;
      background: conic-gradient(var(--score-color) calc(var(--score) * 1%), #e2e8f0 0);
      padding: 12px;
      position: relative;
    }

    .score-meter__ring::after {
      content: "";
      position: absolute;
      inset: 12px;
      border-radius: 50%;
      background: #ffffff;
      border: 1px solid var(--border);
    }

    .score-meter__inner {
      position: absolute;
      inset: 12px;
      z-index: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 4px;
      border-radius: 50%;
      text-align: center;
    }

    .score-meter__value {
      font-size: 42px;
      line-height: 1;
      font-weight: 800;
      color: var(--score-color);
      letter-spacing: -0.05em;
    }

    .score-meter__label {
      font-size: 12px;
      color: var(--text-muted);
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }

    .hero-kpis {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
    }

    .hero-kpi {
      padding: 10px 12px;
      border-radius: 14px;
      border: 1px solid var(--border);
      background: #ffffff;
      text-align: center;
    }

    .hero-kpi__label {
      display: block;
      color: var(--text-muted);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 4px;
    }

    .hero-kpi__value {
      color: var(--text-primary);
      font-size: 18px;
      font-weight: 800;
      line-height: 1.1;
    }

    .report-section {
      padding: 20px;
    }

    .section-head {
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 14px;
    }

    .section-title {
      margin: 0;
      color: var(--text-primary);
      font-size: 20px;
      letter-spacing: -0.02em;
    }

    .section-subtitle {
      margin: 4px 0 0;
      color: var(--text-muted);
      font-size: 13px;
    }

    .section-kicker {
      color: var(--accent);
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      white-space: nowrap;
    }

    .summary-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
    }

    .summary-card {
      padding: 16px;
      border-radius: 16px;
      border: 1px solid var(--card-border, var(--border));
      background: linear-gradient(180deg, var(--card-soft, #ffffff) 0%, #ffffff 100%);
      min-width: 0;
    }

    .summary-card__label {
      color: var(--text-muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 8px;
      font-weight: 700;
    }

    .summary-card__value {
      color: var(--card-color, var(--text-primary));
      font-size: 28px;
      font-weight: 800;
      line-height: 1;
      letter-spacing: -0.03em;
    }

    .summary-card__detail {
      margin-top: 8px;
      color: var(--text-muted);
      font-size: 13px;
    }

    .summary-notes {
      margin-top: 14px;
      padding: 16px 18px;
      border-radius: 16px;
      border: 1px solid var(--border);
      background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
    }

    .summary-notes__title {
      margin: 0 0 10px;
      color: var(--text-primary);
      font-size: 15px;
    }

    .summary-notes__list {
      margin: 0;
      padding: 0;
      list-style: none;
      display: grid;
      gap: 10px;
    }

    .summary-bullet,
    .recommendation-item {
      position: relative;
      padding: 12px 14px 12px 16px;
      border-radius: 14px;
      border: 1px solid var(--bullet-soft, var(--border));
      background: linear-gradient(180deg, var(--bullet-soft, #f8fbff) 0%, #ffffff 100%);
      color: var(--text-secondary);
    }

    .summary-bullet::before,
    .recommendation-item::before {
      content: "";
      position: absolute;
      left: 0;
      top: 10px;
      bottom: 10px;
      width: 4px;
      border-radius: 999px;
      background: var(--bullet-color, var(--accent));
    }

    .section-grid {
      display: grid;
      gap: 14px;
    }

    .section-grid--two {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .info-group {
      padding: 16px;
      border-radius: 16px;
      border: 1px solid var(--border);
      background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
    }

    .info-group__title {
      margin-bottom: 12px;
      color: var(--text-primary);
      font-size: 15px;
      font-weight: 700;
    }

    .info-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
    }

    .info-card {
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid var(--border);
      background: #ffffff;
      min-width: 0;
    }

    .info-card__label {
      color: var(--text-muted);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 6px;
      font-weight: 700;
    }

    .info-card__value {
      color: var(--text-primary);
      font-size: 14px;
      font-weight: 700;
      word-break: break-word;
    }

    .info-card__detail {
      margin-top: 6px;
      color: var(--text-muted);
      font-size: 12px;
      word-break: break-word;
    }

    .panel {
      padding: 16px;
      border-radius: 16px;
      border: 1px solid var(--border);
      background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
    }

    .panel__head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 12px;
    }

    .panel__title {
      margin: 0;
      color: var(--text-primary);
      font-size: 15px;
      font-weight: 700;
    }

    .panel__meta {
      color: var(--text-muted);
      font-size: 12px;
      white-space: nowrap;
    }

    .distribution-bar {
      display: flex;
      overflow: hidden;
      height: 12px;
      border-radius: 999px;
      background: #e2e8f0;
    }

    .distribution-bar__segment {
      min-width: 2px;
    }

    .distribution-legend,
    .type-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 8px;
      margin-top: 12px;
    }

    .legend-item,
    .type-pill {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      padding: 10px 12px;
      border-radius: 12px;
      border: 1px solid var(--border);
      background: #ffffff;
      color: var(--text-secondary);
      min-width: 0;
    }

    .legend-item__label,
    .type-pill__label {
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      color: var(--text-primary);
      font-weight: 600;
    }

    .legend-item__count,
    .type-pill__meta {
      color: var(--text-muted);
      font-size: 12px;
      flex-shrink: 0;
    }

    .legend-item__dot {
      width: 10px;
      height: 10px;
      border-radius: 999px;
      flex-shrink: 0;
    }

    .distribution-empty,
    .empty-state {
      padding: 18px;
      border-radius: 16px;
      border: 1px dashed var(--border-strong);
      background: rgba(255, 255, 255, 0.8);
      color: var(--text-muted);
    }

    .empty-state__title {
      color: var(--text-primary);
      font-weight: 700;
      margin-bottom: 6px;
    }

    .empty-state__text {
      font-size: 13px;
    }

    .recommendation-list,
    .summary-notes__list {
      margin: 0;
      padding: 0;
      list-style: none;
      display: grid;
      gap: 10px;
    }

    .toc-list {
      display: grid;
      gap: 8px;
      width: 100%;
      min-width: 0;
    }

    .toc-item {
      display: flex;
      width: 100%;
      max-width: 100%;
      min-width: 0;
      align-items: center;
      gap: 10px;
      padding: 10px 12px;
      border-radius: 12px;
      border: 1px solid var(--border);
      background: #ffffff;
      color: var(--text-secondary);
      text-decoration: none;
    }

    .toc-item:hover {
      background: #f8fbff;
      text-decoration: none;
    }

    .toc-item--fixed {
      border-color: #bfdbfe;
      background: #eff6ff;
    }

    .toc-item--level-2 {
      padding-left: 24px;
    }

    .toc-item--level-3 {
      padding-left: 34px;
    }

    .toc-item--level-4 {
      padding-left: 44px;
    }

    .toc-item--level-5 {
      padding-left: 54px;
    }

    .toc-item--level-6 {
      padding-left: 64px;
    }

    .toc-item__bullet {
      color: var(--accent);
      font-weight: 800;
      flex-shrink: 0;
    }

    .toc-item__label {
      flex: 1 1 auto;
      min-width: 0;
      color: var(--text-primary);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .finding-list {
      display: grid;
      gap: 14px;
    }

    .finding-card {
      padding: 18px;
      border-radius: 18px;
      border: 1px solid var(--finding-border, var(--border));
      background: linear-gradient(180deg, var(--finding-soft, #ffffff) 0%, #ffffff 100%);
    }

    .finding-card__header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 10px;
    }

    .finding-card__badges {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }

    .severity-badge {
      background: var(--finding-soft, #f8fbff);
      border-color: var(--finding-border, var(--border));
      color: var(--finding-color, var(--accent));
    }

    .verified-badge {
      background: #ecfdf5;
      border-color: #a7f3d0;
      color: #047857;
    }

    .finding-card__location {
      color: var(--text-muted);
      font-size: 12px;
      word-break: break-word;
      text-align: right;
    }

    .finding-card__title {
      margin: 0 0 8px;
      color: var(--text-primary);
      font-size: 18px;
      letter-spacing: -0.01em;
    }

    .finding-card__description,
    .finding-card__section-text {
      margin: 0;
      color: var(--text-secondary);
      font-size: 14px;
      white-space: pre-wrap;
      word-break: break-word;
    }

    .finding-card__section {
      margin-top: 12px;
      padding-top: 12px;
      border-top: 1px dashed var(--border);
    }

    .finding-card__section-title {
      margin-bottom: 6px;
      color: var(--text-primary);
      font-size: 12px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }

    .finding-card__details {
      margin-top: 12px;
      border-top: 1px dashed var(--border);
      padding-top: 12px;
    }

    .finding-card__details > summary {
      cursor: pointer;
      color: var(--accent);
      font-weight: 700;
      margin-bottom: 8px;
    }

    .finding-card__code-wrap {
      margin-top: 12px;
      padding-top: 12px;
      border-top: 1px dashed var(--border);
    }

    .finding-card__code {
      margin: 8px 0 0;
      padding: 14px;
      border-radius: 14px;
      border: 1px solid var(--border);
      background: #f8fafc;
      color: #0f172a;
      overflow: auto;
      font-size: 12px;
      line-height: 1.55;
      white-space: pre-wrap;
      word-break: break-word;
    }

    .markdown-body {
      color: var(--text-secondary);
      font-size: 14px;
    }

    .markdown-body h1,
    .markdown-body h2,
    .markdown-body h3,
    .markdown-body h4,
    .markdown-body h5,
    .markdown-body h6 {
      color: var(--text-primary);
      line-height: 1.3;
      letter-spacing: -0.02em;
      margin: 1.2em 0 0.6em;
    }

    .markdown-body h1 {
      font-size: 1.6rem;
      padding-bottom: 0.45rem;
      border-bottom: 2px solid #dbe2ea;
    }

    .markdown-body h2 {
      font-size: 1.28rem;
      padding-bottom: 0.35rem;
      border-bottom: 1px solid #e2e8f0;
    }

    .markdown-body h3 {
      font-size: 1.08rem;
    }

    .markdown-body p {
      margin: 0.7em 0;
      color: var(--text-secondary);
    }

    .markdown-body ul,
    .markdown-body ol {
      margin: 0.75em 0;
      padding-left: 1.4em;
    }

    .markdown-body li {
      margin: 0.35em 0;
    }

    .markdown-body blockquote {
      margin: 1em 0;
      padding: 0.9em 1em;
      border-left: 4px solid var(--accent);
      border-radius: 0 14px 14px 0;
      background: #eff6ff;
      color: #1e3a8a;
    }

    .markdown-body table {
      width: 100%;
      border-collapse: collapse;
      margin: 1em 0;
      border: 1px solid #dbe2ea;
      border-radius: 14px;
      overflow: hidden;
    }

    .markdown-body th,
    .markdown-body td {
      border-bottom: 1px solid #e2e8f0;
      padding: 0.75rem 0.9rem;
      text-align: left;
      vertical-align: top;
    }

    .markdown-body th {
      background: #f8fbff;
      color: #475569;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }

    .markdown-body tr:last-child td {
      border-bottom: none;
    }

    .markdown-body code {
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
      font-size: 0.92em;
      background: #eef2ff;
      color: #4338ca;
      padding: 0.12em 0.35em;
      border-radius: 0.4rem;
    }

    .markdown-body pre {
      margin: 1em 0;
      padding: 0;
      border-radius: 16px;
      border: 1px solid #dbe2ea;
      overflow: auto;
      background: #f8fafc;
    }

    .markdown-body pre code {
      display: block;
      padding: 1rem 1.1rem;
      background: transparent;
      color: #0f172a;
      white-space: pre;
      overflow-x: auto;
    }

    .markdown-body hr {
      margin: 1.4rem 0;
      border: none;
      height: 1px;
      background: linear-gradient(90deg, transparent, #dbe2ea, transparent);
    }

    .report-footer {
      padding: 16px 20px;
    }

    .report-footer__inner {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      color: var(--text-muted);
      font-size: 12px;
    }

    .report-footer__brand {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      color: var(--text-primary);
      font-weight: 700;
    }

    .report-footer__brand-mark {
      width: 22px;
      height: 22px;
      border-radius: 7px;
      background: linear-gradient(135deg, #2563eb, #0ea5e9);
      color: #ffffff;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      box-shadow: 0 8px 18px rgba(37, 99, 235, 0.2);
    }

    .report-footer__meta {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .footer-chip {
      padding: 6px 10px;
      border-radius: 999px;
      border: 1px solid var(--border);
      background: #ffffff;
      color: var(--text-secondary);
    }

    @media (max-width: 1100px) {
      .report-layout {
        grid-template-columns: 1fr;
      }

      .report-sidebar {
        position: static;
        max-height: none;
        overflow: visible;
        padding-right: 0;
      }

      .hero-layout,
      .section-grid--two {
        grid-template-columns: 1fr;
      }

      .summary-grid,
      .info-grid,
      .hero-kpis {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
    }

    @media (max-width: 720px) {
      .report-shell {
        padding: 14px 12px 28px;
      }

      .report-hero,
      .report-section,
      .report-footer {
        border-radius: 18px;
      }

      .report-hero,
      .report-section,
      .report-footer {
        padding-left: 16px;
        padding-right: 16px;
      }

      .hero-kpis,
      .summary-grid,
      .summary-grid--compact,
      .info-grid {
        grid-template-columns: 1fr;
      }

      .report-layout {
        gap: 14px;
      }

      .report-header__chips,
      .sidebar-brand__meta {
        gap: 8px;
      }

      .section-head,
      .finding-card__header,
      .report-footer__inner,
      .panel__head {
        flex-direction: column;
        align-items: flex-start;
      }

      .finding-card__location {
        text-align: left;
      }
    }

    @media print {
      :root {
        --page-bg: #ffffff;
        --panel-bg: #ffffff;
        --panel-soft: #ffffff;
        --panel-strong: #ffffff;
        --border: #d1d5db;
        --shadow: none;
      }

      body {
        background: #ffffff;
      }

      .report-shell {
        padding: 0;
      }

      .report-layout {
        display: block;
        max-width: none;
        gap: 12px;
      }

      .report-sidebar {
        position: static;
        max-height: none;
        overflow: visible;
        margin-bottom: 12px;
        padding-right: 0;
      }

      .report-header,
      .report-section,
      .sidebar-panel,
      .toc-item,
      .summary-bullet {
        break-inside: avoid;
        box-shadow: none;
      }

      a {
        color: #1d4ed8;
      }

      .report-header,
      .report-section,
      .sidebar-panel {
        border: 1px solid var(--border);
      }
    }
  </style>
</head>
<body class="${buildBodyClass(model)}">
  <main class="report-layout">
    <aside class="report-sidebar" aria-label="报告侧栏">
      <section class="sidebar-panel">
        <div class="sidebar-panel__header">
          <h2 class="sidebar-panel__title">目录</h2>
          <div class="sidebar-panel__hint">${model.hasBodyHeadings ? `${Math.max(0, model.tocEntries.length - 2)} 个标题` : "仅摘要与正文"}</div>
        </div>
        ${toc}
      </section>
    </aside>

    <article class="report-main">
      <header class="report-header" id="report-header">
        <div class="report-header__eyebrow">AgentAudit Report</div>
        <h1 class="report-header__title">${escapeHtml(model.title)}</h1>
        <p class="report-header__subtitle">${escapeHtml(model.subtitle)}</p>
        <div class="report-header__chips">
          ${model.heroBadges
						.map(
							(badge) =>
								`<span class="hero-chip" data-tone="${badge.tone}">${escapeHtml(badge.label)}</span>`,
						)
						.join("")}
        </div>
      </header>

      <section class="report-section" id="summary">
        <div class="section-head">
          <div>
            <h2 class="section-title">摘要</h2>
            <p class="section-subtitle">简要结论、覆盖范围与交付提示。</p>
          </div>
          <div class="section-kicker">Summary</div>
        </div>
        <div class="summary-notes">
          <div class="summary-notes__title">摘要要点</div>
          <ul class="summary-notes__list">${summaryBullets}</ul>
        </div>
      </section>

      <section class="report-section" id="report-body">
        <div class="section-head">
          <div>
            <h2 class="section-title">正文</h2>
            <p class="section-subtitle">保留 Markdown 结构和自动锚点，便于继续查阅细节。</p>
          </div>
          <div class="section-kicker">Body</div>
        </div>
        ${body}
      </section>
    </article>
  </main>
</body>
</html>`;
}

export async function buildAgentAuditReportModel(
	markdown: string,
	task: AgentTask,
	findings: AgentFinding[],
	options: Partial<ReportExportOptions> = {},
): Promise<AgentAuditReportModel> {
	const normalizedOptions = normalizeOptions(options);
	const safeFindings = Array.isArray(findings) ? findings : [];
	const severityCounts = buildSeverityCounts(safeFindings, task);
	const typeDistribution = buildTopTypes(safeFindings);
	const scoreValue = Number(task.security_score || 0);
	const scoreMeta = getScoreMeta(scoreValue);
	const statusMeta = formatStatus(task.status);
	const title = String(
		task.name || `Task ${String(task.id || "").slice(0, 8) || "unknown"}`,
	).trim();
	const subtitleParts = [
		task.description
			? truncateText(task.description.trim(), 180)
			: "Agent 审计报告",
		task.branch_name ? `分支：${task.branch_name}` : null,
		task.workspace_source ? `来源：${task.workspace_source}` : null,
	].filter(Boolean);
	const subtitle = subtitleParts.join(" · ");
	const generatedAt = formatDateTime(new Date().toISOString());
	const topFindings = buildTopFindings(safeFindings, normalizedOptions);
	const summaryCards = buildSummaryCards(task, safeFindings, severityCounts);
	const summaryBullets = buildSummaryBullets(
		task,
		safeFindings,
		severityCounts,
		scoreMeta.label,
		normalizedOptions.includeRemediation,
	);
	const sidebarGroups = normalizedOptions.includeMetadata
		? buildSidebarGroups(task, safeFindings, severityCounts)
		: [];
	const recommendations = buildRecommendations(
		task,
		safeFindings,
		severityCounts,
	);
	const tocHeadings = extractMarkdownHeadings(markdown);
	const tocEntries: ReportTocEntry[] = [
		...FIXED_TOC_ENTRIES,
		...tocHeadings.map((heading) => ({
			id: heading.id,
			label: heading.label,
			level: heading.level,
			fixed: false,
		})),
	];

	const markdownHtml = await marked.parse(markdown || "");
	const bodyHtml = injectHeadingAnchors(
		String(markdownHtml || ""),
		tocHeadings,
	);
	const finalBodyHtml = normalizedOptions.includeCodeSnippets
		? bodyHtml
		: stripCodeBlocksFromHtml(bodyHtml);

	return {
		title,
		subtitle,
		generatedAt,
		statusLabel: statusMeta.label,
		statusTone: statusMeta.tone,
		scoreLabel: scoreMeta.label,
		scoreValue,
		scoreTone: scoreMeta.tone,
		heroBadges: [
			{ label: `任务 ${task.id}`, tone: "info" },
			{ label: statusMeta.label, tone: statusMeta.tone },
			{ label: formatPhase(task.current_phase), tone: "neutral" },
			{
				label: `问题 ${findings.length || Number(task.findings_count || 0)}`,
				tone: topFindings.length > 0 ? "warning" : "success",
			},
		],
		summaryCards,
		summaryBullets,
		sidebarGroups,
		severityDistribution: buildDistributionItems(
			severityCounts,
			["critical", "high", "medium", "low"],
			Math.max(1, safeFindings.length || Number(task.findings_count || 0)),
			SEVERITY_LABELS,
		),
		typeDistribution,
		recommendations,
		topFindings,
		tocEntries,
		bodyHtml: finalBodyHtml,
		hasBodyHeadings: tocHeadings.length > 0,
		includeMetadata: normalizedOptions.includeMetadata,
		includeCodeSnippets: normalizedOptions.includeCodeSnippets,
		includeRemediation: normalizedOptions.includeRemediation,
		compactMode: normalizedOptions.compactMode,
	};
}

export async function generateAgentAuditHtmlReport(
	markdown: string,
	task: AgentTask,
	findings: AgentFinding[],
	options: Partial<ReportExportOptions> = {},
): Promise<string> {
	const model = await buildAgentAuditReportModel(
		markdown,
		task,
		findings,
		options,
	);
	return renderHtmlDocument(model);
}
