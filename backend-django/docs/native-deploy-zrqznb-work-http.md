# 已迁移

旧的域名版原生部署说明已经不再维护。

新的可执行 IP/HTTP 版本请看：

- `backend-django/docs/native-deploy-8.146.236.192-http.md`

新的文档已经按这台服务器的实际情况重写，包含：

- `8.146.236.192` 的 IP 访问方式
- `nginx` 路由
- `nohup uvicorn`
- `nohup celery`
- `nohup python start_scheduler.py`
- 本地构建前端后再复制到服务器的流程
