payload = {
    "START_DATE" : "20260720",
    "END_DATE" : "20260721",
    "CMC_LEVEL" : 2,
    "CMCDEPTID" : 100294,
    "FLAG" : 3,
    "TAG" : 1,
    "SORT_TYPE" : "asc",
    "SORT_COLUMN" : "SCORE",
    "START_PAGE" : 1,
    "END_PAGE" : 10,
    "DEPT_NAME" : "底层软件开发部",
}

# 返回内容如下：
{
    "data": [
        {
            "cnt_total": 33, # 合入的MR总数
            "major_comments_cnt": 14, # 有效检视意见数 严重
            "fatal_comments_cnt": 34, # 有效检视意见数 致命
            "minor_comments_cnt": 22, # 有效检视意见数 一般
            "sugge_comments_cnt": 102, # 有效检视意见数 建议
            "cmt_issue": 10, # 提交issue总数
            "checked_mr_lines": 3303, # 检视的代码行总数
            "cmt_lines": 3344, # 提交的MR总代码量
            "not_0_comment_rate": "48.26%", # 合入的MR零检视意见MR比例
        }
    ]
}