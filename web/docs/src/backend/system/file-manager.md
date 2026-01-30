# 文件管理

文件管理模块负责文件的上传、下载和存储管理。

## 功能概述

- 文件上传
- 文件下载
- 文件删除
- 存储管理

## API 接口

### 文件上传

```
POST /api/file/upload
```

**请求参数：**

- Content-Type: multipart/form-data
- file: 上传的文件

**响应示例：**

```json
{
  "code": 200,
  "data": {
    "id": 1,
    "name": "document.pdf",
    "url": "/media/uploads/document.pdf",
    "size": 1024000,
    "type": "application/pdf"
  }
}
```

### 文件下载

```
GET /api/file/download/{id}
```

### 文件列表

```
GET /api/file/list
```

## 存储配置

支持多种存储方式：

- 本地存储 (默认)
- 阿里云 OSS
- 腾讯云 COS
- MinIO

配置示例：

```python
# env/dev_env.py
FILE_STORAGE = 'local'  # local, oss, cos, minio

# OSS 配置
OSS_ACCESS_KEY = 'your-access-key'
OSS_SECRET_KEY = 'your-secret-key'
OSS_BUCKET = 'your-bucket'
OSS_ENDPOINT = 'oss-cn-hangzhou.aliyuncs.com'
```
