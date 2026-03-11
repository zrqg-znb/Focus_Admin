STATUS_ORDER = ("I", "D", "P", "C", "A")
STATUS_LABELS = {
    "I": "初始化",
    "D": "已定义完成",
    "P": "开发中",
    "C": "已开发完成（转测）",
    "A": "测试完成（已置A）",
}
STATUS_DESCRIPTIONS = {
    "I": "需求刚创建或进入初始化阶段，尚未完成定义。",
    "D": "需求已完成定义，等待进入开发或排期推进。",
    "P": "需求正在开发处理中，尚未达到转测状态。",
    "C": "需求已开发完成并转测，等待测试验收。",
    "A": "需求已测试完成并置 A，可视为验收完成。",
}
CATEGORY_ORDER = ("AR", "DR", "SR")
TIME_FIELD_OPTIONS = (
    "planned_test_time",
    "due_date",
    "completed_time",
    "accepted_time",
)
TIME_FIELD_LABELS = {
    "planned_test_time": "计划转测时间",
    "due_date": "计划完成时间",
    "completed_time": "开发完成时间",
    "accepted_time": "测试完成时间",
}
UNKNOWN_TEAM_NAME = "未识别团队"
