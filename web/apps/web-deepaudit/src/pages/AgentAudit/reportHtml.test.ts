import { describe, expect, it } from "vitest";
import type { AgentFinding, AgentTask } from "@/shared/api/agentTasks";
import {
	buildAgentAuditReportModel,
	generateAgentAuditHtmlReport,
} from "./reportHtml";

function createTask(overrides: Partial<AgentTask> = {}): AgentTask {
	return {
		id: "task-1",
		project_id: "project-1",
		name: "支付链路审计",
		description: "检查支付模块的鉴权、输入验证与错误回显。",
		task_type: "deepaudit",
		status: "completed",
		current_phase: "reporting",
		current_step: "整理结果",
		total_files: 120,
		indexed_files: 96,
		analyzed_files: 88,
		files_with_findings: 3,
		total_chunks: 200,
		findings_count: 3,
		verified_count: 2,
		false_positive_count: 1,
		total_iterations: 11,
		tool_calls_count: 42,
		tokens_used: 12345,
		critical_count: 1,
		high_count: 1,
		medium_count: 1,
		low_count: 0,
		quality_score: 87,
		security_score: 66,
		created_at: "2026-05-04T01:02:03.000Z",
		started_at: "2026-05-04T01:10:00.000Z",
		completed_at: "2026-05-04T01:34:56.000Z",
		repository_type: "multi",
		repository_signature: "repo-signature",
		repository_url: "https://example.com/repo.git",
		branch_name: "release/1.2",
		manifest_xml: null,
		group: "security",
		workspace_path: "/workspaces/repo",
		cache_repo: null,
		last_synced_at: 1710000000,
		progress_percentage: 100,
		audit_scope: {},
		target_vulnerabilities: ["sql_injection", "xss"],
		verification_level: "sandbox",
		exclude_patterns: [],
		target_files: ["src/app.ts"],
		selected_target_count: 2,
		selected_directory_count: 1,
		resolved_file_count: 88,
		workspace_source: "workspace",
		error_message: null,
		...overrides,
	};
}

function createFindings(): AgentFinding[] {
	return [
		{
			id: "finding-1",
			task_id: "task-1",
			vulnerability_type: "sql_injection",
			severity: "critical",
			title: "SQL injection in query builder",
			description: "用户输入未经过滤直接拼接到 SQL 语句中。",
			file_path: "src/services/user.ts",
			line_start: 42,
			line_end: 48,
			code_snippet: [
				"const sql = `SELECT * FROM users WHERE id = ${userId}`;",
				"return db.query(sql);",
			].join("\n"),
			status: "open",
			is_verified: true,
			has_poc: false,
			poc_code: null,
			suggestion: "使用参数化查询并校验 userId 的类型。",
			fix_code:
				"return db.query('SELECT * FROM users WHERE id = ?', [userId]);",
			ai_explanation: "该片段存在明显的字符串拼接风险，容易触发注入攻击。",
			ai_confidence: 0.96,
			created_at: "2026-05-04T01:11:00.000Z",
		},
		{
			id: "finding-2",
			task_id: "task-1",
			vulnerability_type: "xss",
			severity: "high",
			title: "Cross-site scripting in comment renderer",
			description: "评论内容在进入 DOM 前未做编码。",
			file_path: "src/components/Comment.tsx",
			line_start: 18,
			line_end: 22,
			code_snippet: "<div dangerouslySetInnerHTML={{ __html: comment }} />",
			status: "open",
			is_verified: false,
			has_poc: false,
			poc_code: null,
			suggestion: "在渲染前进行 HTML 转义，或改为白名单渲染。",
			fix_code: null,
			ai_explanation: "直接渲染不可信输入会导致脚本注入。",
			ai_confidence: 0.91,
			created_at: "2026-05-04T01:12:00.000Z",
		},
		{
			id: "finding-3",
			task_id: "task-1",
			vulnerability_type: "auth_logic",
			severity: "medium",
			title: "Authorization check can be bypassed",
			description: "部分分支仅依赖前端状态判断。",
			file_path: "src/routes/admin.ts",
			line_start: 7,
			line_end: 11,
			code_snippet: "if (isAdmin) {\n  return next();\n}",
			status: "open",
			is_verified: false,
			has_poc: true,
			poc_code: "curl -H 'X-Role: admin' ...",
			suggestion: "将鉴权逻辑移动到服务端并补充单元测试。",
			fix_code: null,
			ai_explanation: "仅依赖前端变量无法阻止篡改请求。",
			ai_confidence: 0.83,
			created_at: "2026-05-04T01:13:00.000Z",
		},
	];
}

describe("AgentAudit HTML report generation", () => {
	it("renders a light reporting shell with summary, metadata, risk overview and anchors", async () => {
		const task = createTask();
		const findings = createFindings();
		const markdown = [
			"# 总览",
			"",
			"## 风险分析",
			"本节描述审计结论。",
			"",
			"### 证据",
			"- 日志已归档",
		].join("\n");

		const model = await buildAgentAuditReportModel(markdown, task, findings);

		expect(model.title).toBe("支付链路审计");
		expect(model.summaryCards).toHaveLength(4);
		expect(model.reportInfoGroups).toHaveLength(2);
		expect(model.reportInfoGroups[0].cards).toEqual(
			expect.arrayContaining([
				expect.objectContaining({ label: "任务 ID", value: "task-1" }),
				expect.objectContaining({ label: "项目 ID", value: "project-1" }),
			]),
		);
		expect(model.reportInfoGroups[1].cards).toEqual(
			expect.arrayContaining([
				expect.objectContaining({
					label: "问题文件",
					detail: expect.stringContaining("严重 1 / 高危 1"),
				}),
				expect.objectContaining({ label: "验证数", value: "1" }),
			]),
		);
		expect(model.severityDistribution.map((item) => item.count)).toEqual([
			1, 1, 1, 0,
		]);
		expect(model.topFindings[0]).toEqual(
			expect.objectContaining({
				severity: "critical",
				title: "SQL injection in query builder",
				location: "src/services/user.ts:42-48",
			}),
		);
		expect(model.tocEntries.map((entry) => entry.id)).toEqual(
			expect.arrayContaining([
				"executive-summary",
				"report-info",
				"risk-overview",
				"key-findings",
				"report-body",
				"总览",
				"风险分析",
				"证据",
			]),
		);
		expect(model.hasBodyHeadings).toBe(true);

		const html = await generateAgentAuditHtmlReport(markdown, task, findings);

		expect(html).toContain('meta name="color-scheme" content="light"');
		expect(html).toContain("color-scheme: light");
		expect(html).toContain("--page-bg: #eef2f7");
		expect(html).toContain("执行摘要");
		expect(html).toContain("报告信息");
		expect(html).toContain("风险总览");
		expect(html).toContain("重点发现");
		expect(html).toContain("目录");
		expect(html).toContain("正文");
		expect(html).toContain("本次审计共识别 3 个问题");
		expect(html).toContain("命中 3 条问题 · 严重 1 / 高危 1");
		expect(html).toContain("Sql Injection");
		expect(html).toContain('id="总览"');
		expect(html).toContain('id="风险分析"');
		expect(html).toContain('id="证据"');
		expect(html).toContain('href="#总览"');
		expect(html).toContain('href="#风险分析"');
		expect(html).toContain('href="#证据"');
		expect(html).toContain('id="report-info"');
	});

	it("hides metadata and renders empty states when no findings are available", async () => {
		const task = createTask({
			findings_count: 0,
			verified_count: 0,
			false_positive_count: 0,
			critical_count: 0,
			high_count: 0,
			medium_count: 0,
			low_count: 0,
			security_score: null,
			quality_score: 0,
			started_at: null,
			completed_at: null,
			branch_name: null,
			workspace_source: null,
			current_phase: null,
			current_step: null,
			analyzed_files: 0,
			total_files: 0,
			files_with_findings: 0,
			resolved_file_count: 0,
		});
		const markdown = ["# 结果", "", "暂无更多内容。"].join("\n");

		const model = await buildAgentAuditReportModel(markdown, task, [], {
			includeMetadata: false,
			includeCodeSnippets: false,
			includeRemediation: false,
		});

		expect(model.includeMetadata).toBe(false);
		expect(model.reportInfoGroups).toHaveLength(0);
		expect(model.tocEntries.some((entry) => entry.id === "report-info")).toBe(
			false,
		);
		expect(model.topFindings).toHaveLength(0);

		const html = await generateAgentAuditHtmlReport(markdown, task, [], {
			includeMetadata: false,
			includeCodeSnippets: false,
			includeRemediation: false,
		});

		expect(html).not.toContain('id="report-info"');
		expect(html).not.toContain("报告信息");
		expect(html).toContain("暂无可展示的重点发现");
		expect(html).toContain("暂无数据");
		expect(html).toContain("本次审计未产出可展示的结构化问题项");
		expect(html).toContain("—");
		expect(html).toContain("color-scheme: light");
	});
});
