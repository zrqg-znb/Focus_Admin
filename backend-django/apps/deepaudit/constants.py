PROJECT_SOURCE_REPOSITORY = 'repository'
PROJECT_SOURCE_ZIP = 'zip'
PROJECT_SOURCE_CHOICES = [
    (PROJECT_SOURCE_REPOSITORY, '仓库项目'),
    (PROJECT_SOURCE_ZIP, 'ZIP 项目'),
]

REPOSITORY_TYPE_SINGLE = 'single'
REPOSITORY_TYPE_MULTI = 'multi'
REPOSITORY_TYPE_CHOICES = [
    (REPOSITORY_TYPE_SINGLE, '单仓'),
    (REPOSITORY_TYPE_MULTI, '多仓'),
]

PROJECT_MEMBER_ROLE_OWNER = 'owner'
PROJECT_MEMBER_ROLE_ADMIN = 'admin'
PROJECT_MEMBER_ROLE_MEMBER = 'member'
PROJECT_MEMBER_ROLE_VIEWER = 'viewer'
PROJECT_MEMBER_ROLE_CHOICES = [
    (PROJECT_MEMBER_ROLE_OWNER, 'Owner'),
    (PROJECT_MEMBER_ROLE_ADMIN, 'Admin'),
    (PROJECT_MEMBER_ROLE_MEMBER, 'Member'),
    (PROJECT_MEMBER_ROLE_VIEWER, 'Viewer'),
]

TASK_STATUS_PENDING = 'pending'
TASK_STATUS_RUNNING = 'running'
TASK_STATUS_COMPLETED = 'completed'
TASK_STATUS_FAILED = 'failed'
TASK_STATUS_CANCELLED = 'cancelled'
TASK_STATUS_CHOICES = [
    (TASK_STATUS_PENDING, '等待中'),
    (TASK_STATUS_RUNNING, '运行中'),
    (TASK_STATUS_COMPLETED, '已完成'),
    (TASK_STATUS_FAILED, '失败'),
    (TASK_STATUS_CANCELLED, '已取消'),
]

AGENT_TASK_STATUS_PENDING = 'pending'
AGENT_TASK_STATUS_INITIALIZING = 'initializing'
AGENT_TASK_STATUS_RUNNING = 'running'
AGENT_TASK_STATUS_PLANNING = 'planning'
AGENT_TASK_STATUS_INDEXING = 'indexing'
AGENT_TASK_STATUS_ANALYZING = 'analyzing'
AGENT_TASK_STATUS_VERIFYING = 'verifying'
AGENT_TASK_STATUS_REPORTING = 'reporting'
AGENT_TASK_STATUS_COMPLETED = 'completed'
AGENT_TASK_STATUS_FAILED = 'failed'
AGENT_TASK_STATUS_CANCELLED = 'cancelled'
AGENT_TASK_STATUS_CHOICES = [
    (AGENT_TASK_STATUS_PENDING, '等待中'),
    (AGENT_TASK_STATUS_INITIALIZING, '初始化'),
    (AGENT_TASK_STATUS_RUNNING, '运行中'),
    (AGENT_TASK_STATUS_PLANNING, '规划中'),
    (AGENT_TASK_STATUS_INDEXING, '索引中'),
    (AGENT_TASK_STATUS_ANALYZING, '分析中'),
    (AGENT_TASK_STATUS_VERIFYING, '验证中'),
    (AGENT_TASK_STATUS_REPORTING, '报告生成中'),
    (AGENT_TASK_STATUS_COMPLETED, '已完成'),
    (AGENT_TASK_STATUS_FAILED, '失败'),
    (AGENT_TASK_STATUS_CANCELLED, '已取消'),
]

AGENT_PHASE_PLANNING = 'planning'
AGENT_PHASE_INDEXING = 'indexing'
AGENT_PHASE_RECONNAISSANCE = 'reconnaissance'
AGENT_PHASE_ANALYSIS = 'analysis'
AGENT_PHASE_VERIFICATION = 'verification'
AGENT_PHASE_REPORTING = 'reporting'
AGENT_PHASE_CHOICES = [
    (AGENT_PHASE_PLANNING, 'Planning'),
    (AGENT_PHASE_INDEXING, 'Indexing'),
    (AGENT_PHASE_RECONNAISSANCE, 'Reconnaissance'),
    (AGENT_PHASE_ANALYSIS, 'Analysis'),
    (AGENT_PHASE_VERIFICATION, 'Verification'),
    (AGENT_PHASE_REPORTING, 'Reporting'),
]

ISSUE_STATUS_OPEN = 'open'
ISSUE_STATUS_RESOLVED = 'resolved'
ISSUE_STATUS_FALSE_POSITIVE = 'false_positive'
ISSUE_STATUS_CHOICES = [
    (ISSUE_STATUS_OPEN, '待处理'),
    (ISSUE_STATUS_RESOLVED, '已修复'),
    (ISSUE_STATUS_FALSE_POSITIVE, '误报'),
]

FINDING_STATUS_OPEN = 'open'
FINDING_STATUS_FIXED = 'fixed'
FINDING_STATUS_WONT_FIX = 'wont_fix'
FINDING_STATUS_FALSE_POSITIVE = 'false_positive'
FINDING_STATUS_CHOICES = [
    (FINDING_STATUS_OPEN, '待处理'),
    (FINDING_STATUS_FIXED, '已修复'),
    (FINDING_STATUS_WONT_FIX, '暂不修复'),
    (FINDING_STATUS_FALSE_POSITIVE, '误报'),
]

SEVERITY_CRITICAL = 'critical'
SEVERITY_HIGH = 'high'
SEVERITY_MEDIUM = 'medium'
SEVERITY_LOW = 'low'
SEVERITY_CHOICES = [
    (SEVERITY_CRITICAL, 'Critical'),
    (SEVERITY_HIGH, 'High'),
    (SEVERITY_MEDIUM, 'Medium'),
    (SEVERITY_LOW, 'Low'),
]

SCAN_TYPE_REPOSITORY = 'repository'
SCAN_TYPE_ZIP = 'zip'
SCAN_TYPE_INSTANT = 'instant'
SCAN_TYPE_CHOICES = [
    (SCAN_TYPE_REPOSITORY, '仓库扫描'),
    (SCAN_TYPE_ZIP, 'ZIP 扫描'),
    (SCAN_TYPE_INSTANT, '即时分析'),
]

AGENT_EVENT_TYPES = [
    'task_start',
    'task_complete',
    'task_error',
    'task_cancel',
    'phase_start',
    'phase_complete',
    'thinking',
    'planning',
    'decision',
    'tool_call',
    'tool_result',
    'tool_error',
    'finding_new',
    'finding_update',
    'finding_verified',
    'finding_false_positive',
    'progress',
    'info',
    'warning',
    'error',
]

EMBEDDING_PROVIDERS = [
    {
        'id': 'openai',
        'name': 'OpenAI Compatible',
        'description': 'OpenAI 官方或兼容 embeddings 接口',
        'models': ['text-embedding-3-small', 'text-embedding-3-large', 'text-embedding-ada-002'],
        'requires_api_key': True,
        'default_model': 'text-embedding-3-small',
    },
    {
        'id': 'azure',
        'name': 'Azure OpenAI',
        'description': 'Azure 托管的 OpenAI embeddings 接口',
        'models': ['text-embedding-3-small', 'text-embedding-3-large', 'text-embedding-ada-002'],
        'requires_api_key': True,
        'default_model': 'text-embedding-3-small',
    },
    {
        'id': 'ollama',
        'name': 'Ollama',
        'description': '本地嵌入模型',
        'models': ['nomic-embed-text', 'mxbai-embed-large', 'all-minilm', 'snowflake-arctic-embed', 'bge-m3', 'qwen3-embedding'],
        'requires_api_key': False,
        'default_model': 'bge-m3',
    },
    {
        'id': 'cohere',
        'name': 'Cohere',
        'description': 'Cohere Embed API',
        'models': [
            'embed-english-v3.0',
            'embed-multilingual-v3.0',
            'embed-english-light-v3.0',
            'embed-multilingual-light-v3.0',
            'embed-v4.0',
        ],
        'requires_api_key': True,
        'default_model': 'embed-multilingual-v3.0',
    },
    {
        'id': 'huggingface',
        'name': 'HuggingFace',
        'description': 'HuggingFace Inference Providers',
        'models': [
            'sentence-transformers/all-MiniLM-L6-v2',
            'sentence-transformers/all-mpnet-base-v2',
            'BAAI/bge-large-zh-v1.5',
            'BAAI/bge-m3',
        ],
        'requires_api_key': True,
        'default_model': 'BAAI/bge-m3',
    },
    {
        'id': 'jina',
        'name': 'Jina AI',
        'description': 'Jina AI 代码和通用嵌入模型',
        'models': ['jina-embeddings-v2-base-code', 'jina-embeddings-v2-base-en', 'jina-embeddings-v2-base-zh'],
        'requires_api_key': True,
        'default_model': 'jina-embeddings-v2-base-code',
    },
    {
        'id': 'qwen',
        'name': 'Qwen',
        'description': '阿里云 DashScope 嵌入模型',
        'models': ['text-embedding-v4', 'text-embedding-v3', 'text-embedding-v2'],
        'requires_api_key': True,
        'default_model': 'text-embedding-v4',
    },
]

DEFAULT_LLM_CONFIG = {
    'provider': 'openai',
    'model': '',
    'api_key': '',
    'base_url': '',
    'timeout': 150,
    'temperature': 0.1,
    'max_tokens': 4096,
    'first_token_timeout': 90,
    'stream_timeout': 60,
    'tool_timeout': 60,
    'sub_agent_timeout': 600,
    'agent_timeout': 1800,
}

DEFAULT_OTHER_CONFIG = {
    'codehub_token': '',
    'output_language': 'zh-CN',
    'scan_config': {
        'max_analyze_files': 0,
        'llm_concurrency': 3,
        'llm_gap_ms': 500,
        'include_tests': False,
        'include_docs': False,
        'max_file_size': 200 * 1024,
        'analysis_depth': 'standard',
    },
    'agent_config': {
        'max_iterations': 50,
        'timeout_seconds': 1800,
        'verification_level': 'sandbox',
        'target_vulnerabilities': [
            'sql_injection',
            'xss',
            'command_injection',
            'path_traversal',
            'ssrf',
        ],
    },
    'embedding_config': {
        'provider': 'ollama',
        'model': 'bge-m3',
        'api_key': '',
        'base_url': 'http://127.0.0.1:11434',
        'dimensions': 1024,
        'batch_size': 100,
    },
}

DEEPAUDIT_PERMISSION_CODES = {
    'projects_create': 'deepaudit:projects:create',
    'projects_update': 'deepaudit:projects:update',
    'projects_delete': 'deepaudit:projects:delete',
    'projects_restore': 'deepaudit:projects:restore',
    'projects_members': 'deepaudit:projects:members',
    'tasks_create': 'deepaudit:tasks:create',
    'agent_tasks_create': 'deepaudit:agent-tasks:create',
    'tasks_cancel': 'deepaudit:tasks:cancel',
    'issues_update': 'deepaudit:issues:update',
    'reports_export': 'deepaudit:reports:export',
    'rules_manage': 'deepaudit:rules:manage',
    'prompts_manage': 'deepaudit:prompts:manage',
    'settings_save': 'deepaudit:settings:save',
}
