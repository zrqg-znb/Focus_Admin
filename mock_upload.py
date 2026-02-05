import uuid
import math
import requests
import time

# 配置参数
PROJECT_KEY = "7a17af26-91f6-4205-82b4-622782c22e66"
API_BASE = "http://127.0.0.1:8001/api/code-scan/upload/chunk"
TOOL_NAME = "tscan"

# 模拟的 TScanCode XML 报告内容
MOCK_XML_CONTENT = """<?xml version="1.0" encoding="UTF-8"?>
<results>
    <error file="/src/main.cpp" line="42" id="nullPointer" severity="error" msg="Possible null pointer dereference">
        <verbose>Value is initialized to null and dereferenced.</verbose>
    </error>
    <error file="/src/utils.cpp" line="108" id="memoryLeak" severity="error" msg="Memory leak detected">
        <verbose>Memory allocated at line 100 is not freed.</verbose>
    </error>
    <error file="/src/config.cpp" line="15" id="unusedVariable" severity="warning" msg="Unused variable 'ret'">
        <verbose>Variable 'ret' is assigned a value that is never used.</verbose>
    </error>
</results>
"""

def mock_upload():
    # 1. 准备数据
    content = MOCK_XML_CONTENT
    file_id = str(uuid.uuid4())
    
    # 2. 分片参数 (这里数据量小，直接当做一个分片)
    CHUNK_SIZE = 1024 
    total_len = len(content)
    total_chunks = math.ceil(total_len / CHUNK_SIZE)
    
    print(f"Start uploading mock report (Size: {total_len} bytes, Chunks: {total_chunks})...")

    # 3. 循环上传
    for i in range(total_chunks):
        start = i * CHUNK_SIZE
        end = min((i + 1) * CHUNK_SIZE, total_len)
        chunk_data = content[start:end]

        payload = {
            "project_key": PROJECT_KEY,
            "tool_name": TOOL_NAME,
            "chunk_index": i,
            "total_chunks": total_chunks,
            "chunk_content": chunk_data,
            "file_id": file_id,
            "file_ext": "xml"
        }
        
        try:
            print(f"Uploading chunk {i+1}/{total_chunks}...")
            # 已移除 auth 鉴权，直接上传
            resp = requests.post(API_BASE, json=payload)
            print(f"Response: {resp.status_code} - {resp.text}")
            
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "completed":
                    print(f"\nUpload completed! Task ID: {data.get('task_id')}")
            else:
                print("Upload failed!")
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    mock_upload()
