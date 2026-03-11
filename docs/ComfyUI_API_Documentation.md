# ComfyUI REST API 文档

**版本**: 1.0  
**日期**: 2025-03-11  
**基础URL**: `http://localhost:8188`

---

## 目录

1. [API 概述](#1-api-概述)
2. [基础端点](#2-基础端点)
3. [提示词队列](#3-提示词队列)
4. [历史记录](#4-历史记录)
5. [图片上传与查看](#5-图片上传与查看)
6. [节点信息](#6-节点信息)
7. [系统状态](#7-系统状态)
8. [Python 使用示例](#8-python-使用示例)
9. [curl 使用示例](#9-curl-使用示例)
10. [工作流 JSON 格式](#10-工作流-json-格式)

---

## 1. API 概述

ComfyUI 提供 REST API 用于程序化控制工作流执行。API 支持：

- 提交提示词（运行工作流）
- 查询队列状态
- 查看执行历史
- 上传图片
- 获取节点信息
- 查看系统状态

**基础URL**: `http://127.0.0.1:8188` 或 `http://localhost:8188`

---

## 2. 基础端点

### 2.1 测试连接

```http
GET /
```

返回 ComfyUI Web 界面 HTML。

**示例**:
```bash
curl http://localhost:8188/
```

---

## 3. 提示词队列

### 3.1 提交提示词（运行工作流）

```http
POST /prompt
Content-Type: application/json
```

**请求体**:
```json
{
  "prompt": {
    "3": {
      "inputs": {
        "seed": 123456,
        "steps": 20,
        "cfg": 8.0,
        "sampler_name": "euler",
        "scheduler": "normal",
        "denoise": 1.0,
        "model": ["4", 0],
        "positive": ["6", 0],
        "negative": ["7", 0],
        "latent_image": ["5", 0]
      },
      "class_type": "KSampler"
    },
    "4": {
      "inputs": {
        "ckpt_name": "v1-5-pruned.ckpt"
      },
      "class_type": "CheckpointLoaderSimple"
    },
    "5": {
      "inputs": {
        "width": 512,
        "height": 512,
        "batch_size": 1
      },
      "class_type": "EmptyLatentImage"
    },
    "6": {
      "inputs": {
        "text": "a beautiful landscape",
        "clip": ["4", 1]
      },
      "class_type": "CLIPTextEncode"
    },
    "7": {
      "inputs": {
        "text": "bad quality",
        "clip": ["4", 1]
      },
      "class_type": "CLIPTextEncode"
    },
    "8": {
      "inputs": {
        "samples": ["3", 0],
        "vae": ["4", 2]
      },
      "class_type": "VAEDecode"
    },
    "9": {
      "inputs": {
        "filename_prefix": "ComfyUI",
        "images": ["8", 0]
      },
      "class_type": "SaveImage"
    }
  },
  "client_id": "test-client-id",
  "prompt_id": "test-prompt-id"
}
```

**响应**:
```json
{
  "prompt_id": "test-prompt-id",
  "number": 1,
  "node_errors": {}
}
```

**Python 示例**:
```python
import requests
import json

url = "http://localhost:8188/prompt"

# 加载工作流 JSON
with open("workflow.json", "r") as f:
    workflow = json.load(f)

payload = {
    "prompt": workflow,
    "client_id": "my-client-id"
}

response = requests.post(url, json=payload)
result = response.json()
print(f"Prompt ID: {result['prompt_id']}")
print(f"Queue Number: {result['number']}")
```

### 3.2 获取队列信息

```http
GET /queue
```

**响应**:
```json
{
  "queue_running": [],
  "queue_pending": [
    ["prompt-id", 1, {"3": {...}}, {"client_id": "xxx"}, [], []]
  ]
}
```

**Python 示例**:
```python
import requests

response = requests.get("http://localhost:8188/queue")
queue_info = response.json()

print(f"Running: {len(queue_info['queue_running'])}")
print(f"Pending: {len(queue_info['queue_pending'])}")
```

### 3.3 清除队列

```http
POST /queue
Content-Type: application/json
```

**请求体** (清除所有):
```json
{
  "clear": true
}
```

**请求体** (删除特定):
```json
{
  "delete": ["prompt-id"]
}
```

**Python 示例**:
```python
import requests

# 清除所有队列
requests.post("http://localhost:8188/queue", json={"clear": True})

# 删除特定任务
requests.post("http://localhost:8188/queue", json={"delete": ["prompt-id"]})
```

### 3.4 中断当前执行

```http
POST /interrupt
```

**Python 示例**:
```python
import requests

requests.post("http://localhost:8188/interrupt")
```

---

## 4. 历史记录

### 4.1 获取历史记录

```http
GET /history
GET /history?max_items=10
GET /history?max_items=10&offset=0
```

**响应**:
```json
{
  "prompt-id": {
    "prompt": [...],
    "outputs": {
      "9": {
        "images": [
          {
            "filename": "ComfyUI_00001_.png",
            "subfolder": "",
            "type": "output"
          }
        ]
      }
    },
    "status": {
      "status_str": "success",
      "completed": true,
      "messages": []
    }
  }
}
```

**Python 示例**:
```python
import requests

response = requests.get("http://localhost:8188/history")
history = response.json()

for prompt_id, data in history.items():
    print(f"Prompt ID: {prompt_id}")
    print(f"Status: {data['status']['status_str']}")
```

### 4.2 获取特定历史记录

```http
GET /history/{prompt_id}
```

**Python 示例**:
```python
import requests

response = requests.get("http://localhost:8188/history/test-prompt-id")
data = response.json()
```

---

## 5. 图片上传与查看

### 5.1 上传图片

```http
POST /upload/image
Content-Type: multipart/form-data
```

**参数**:
- `image`: 图片文件
- `type`: "input", "temp", 或 "output"
- `subfolder`: 子文件夹（可选）
- `overwrite`: "true" 或 "false"（可选）

**Python 示例**:
```python
import requests

url = "http://localhost:8188/upload/image"

with open("input_image.png", "rb") as f:
    files = {"image": f}
    data = {
        "type": "input",
        "subfolder": "my_images"
    }
    response = requests.post(url, files=files, data=data)
    
result = response.json()
print(f"Uploaded: {result['name']}")
```

### 5.2 查看图片

```http
GET /view?filename=ComfyUI_00001_.png&subfolder=&type=output
```

**参数**:
- `filename`: 文件名
- `type`: "input", "temp", "output"
- `subfolder`: 子文件夹
- `preview`: 预览格式，如 "webp;90"
- `channel`: 通道，如 "rgb", "rgba", "a"

**Python 示例**:
```python
import requests
from PIL import Image
from io import BytesIO

url = "http://localhost:8188/view"
params = {
    "filename": "ComfyUI_00001_.png",
    "type": "output"
}

response = requests.get(url, params=params)
image = Image.open(BytesIO(response.content))
image.show()
```

### 5.3 上传遮罩

```http
POST /upload/mask
Content-Type: multipart/form-data
```

**参数**:
- `image`: 遮罩图片
- `original_ref`: JSON 字符串，原始图片引用

---

## 6. 节点信息

### 6.1 获取所有节点信息

```http
GET /object_info
```

**响应**: 包含所有可用节点的输入输出类型定义。

**Python 示例**:
```python
import requests

response = requests.get("http://localhost:8188/object_info")
nodes = response.json()

# 查看 KSampler 节点信息
print(nodes['KSampler'])
```

### 6.2 获取特定节点信息

```http
GET /object_info/{node_class}
```

**示例**:
```http
GET /object_info/KSampler
```

### 6.3 获取模型列表

```http
GET /models
```

**响应**:
```json
["checkpoints", "loras", "vae", ...]
```

### 6.4 获取特定模型类型文件列表

```http
GET /models/{folder}
```

**示例**:
```http
GET /models/checkpoints
```

**响应**:
```json
["v1-5-pruned.ckpt", "v2-1_768-ema-pruned.ckpt", ...]
```

### 6.5 获取 embeddings 列表

```http
GET /embeddings
```

---

## 7. 系统状态

### 7.1 获取系统统计信息

```http
GET /system_stats
```

**响应**:
```json
{
  "system": {
    "os": "linux",
    "ram_total": 68719476736,
    "ram_free": 34359738368,
    "comfyui_version": "0.16.4",
    "python_version": "3.12.12",
    "pytorch_version": "2.10.0+cu128"
  },
  "devices": [
    {
      "name": "NVIDIA GeForce RTX 5090",
      "type": "cuda",
      "index": 0,
      "vram_total": 34359738368,
      "vram_free": 32212254720
    }
  ]
}
```

**Python 示例**:
```python
import requests

response = requests.get("http://localhost:8188/system_stats")
stats = response.json()

for device in stats['devices']:
    print(f"GPU: {device['name']}")
    print(f"VRAM: {device['vram_free'] / 1024**3:.2f} GB free")
```

### 7.2 获取功能标志

```http
GET /features
```

---

## 8. Python 使用示例

### 8.1 完整示例：提交工作流并获取结果

```python
import requests
import json
import time
from PIL import Image
from io import BytesIO

class ComfyUIClient:
    def __init__(self, server_address="127.0.0.1:8188"):
        self.server_address = server_address
        self.client_id = "python-client"
    
    def get_history(self, prompt_id):
        """获取历史记录"""
        url = f"http://{self.server_address}/history/{prompt_id}"
        response = requests.get(url)
        return response.json()
    
    def get_image(self, filename, subfolder, folder_type):
        """获取图片"""
        url = f"http://{self.server_address}/view"
        params = {
            "filename": filename,
            "subfolder": subfolder,
            "type": folder_type
        }
        response = requests.get(url, params=params)
        return Image.open(BytesIO(response.content))
    
    def queue_prompt(self, prompt):
        """提交提示词"""
        url = f"http://{self.server_address}/prompt"
        payload = {
            "prompt": prompt,
            "client_id": self.client_id
        }
        response = requests.post(url, json=payload)
        return response.json()
    
    def wait_for_result(self, prompt_id, timeout=300):
        """等待执行完成并获取结果"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            history = self.get_history(prompt_id)
            if prompt_id in history:
                return history[prompt_id]
            time.sleep(1)
        return None
    
    def generate_image(self, workflow_json, save_node_id="9"):
        """生成图片并返回"""
        # 提交工作流
        result = self.queue_prompt(workflow_json)
        prompt_id = result['prompt_id']
        print(f"Prompt queued: {prompt_id}")
        
        # 等待完成
        history = self.wait_for_result(prompt_id)
        if not history:
            raise TimeoutError("Generation timeout")
        
        # 获取输出图片
        outputs = history['outputs']
        if save_node_id in outputs:
            images = outputs[save_node_id]['images']
            if images:
                img_info = images[0]
                return self.get_image(
                    img_info['filename'],
                    img_info['subfolder'],
                    img_info['type']
                )
        
        raise Exception("No output image found")

# 使用示例
if __name__ == "__main__":
    client = ComfyUIClient("localhost:8188")
    
    # 加载工作流
    with open("workflow.json", "r") as f:
        workflow = json.load(f)
    
    # 修改参数（可选）
    # workflow["3"]["inputs"]["seed"] = 12345
    # workflow["6"]["inputs"]["text"] = "a beautiful sunset over mountains"
    
    try:
        image = client.generate_image(workflow)
        image.save("output.png")
        print("Image saved to output.png")
    except Exception as e:
        print(f"Error: {e}")
```

---

## 9. curl 使用示例

### 9.1 提交简单提示词

```bash
# 创建 JSON 文件
cat > prompt.json << 'EOF'
{
  "prompt": {
    "3": {
      "inputs": {
        "seed": 123456,
        "steps": 20,
        "cfg": 8,
        "sampler_name": "euler",
        "scheduler": "normal",
        "denoise": 1,
        "model": ["4", 0],
        "positive": ["6", 0],
        "negative": ["7", 0],
        "latent_image": ["5", 0]
      },
      "class_type": "KSampler"
    },
    "4": {
      "inputs": {"ckpt_name": "v1-5-pruned.ckpt"},
      "class_type": "CheckpointLoaderSimple"
    },
    "5": {
      "inputs": {"width": 512, "height": 512, "batch_size": 1},
      "class_type": "EmptyLatentImage"
    },
    "6": {
      "inputs": {"text": "a beautiful landscape", "clip": ["4", 1]},
      "class_type": "CLIPTextEncode"
    },
    "7": {
      "inputs": {"text": "bad quality", "clip": ["4", 1]},
      "class_type": "CLIPTextEncode"
    },
    "8": {
      "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
      "class_type": "VAEDecode"
    },
    "9": {
      "inputs": {"filename_prefix": "ComfyUI", "images": ["8", 0]},
      "class_type": "SaveImage"
    }
  }
}
EOF

# 提交
curl -X POST http://localhost:8188/prompt \
  -H "Content-Type: application/json" \
  -d @prompt.json
```

### 9.2 上传图片

```bash
curl -X POST http://localhost:8188/upload/image \
  -F "image=@input.png" \
  -F "type=input" \
  -F "subfolder=my_images"
```

### 9.3 下载生成的图片

```bash
# 假设生成的文件名为 ComfyUI_00001_.png
curl -o output.png \
  "http://localhost:8188/view?filename=ComfyUI_00001_.png&type=output"
```

---

## 10. 工作流 JSON 格式

### 10.1 基本结构

```json
{
  "prompt_id": "optional-id",
  "client_id": "optional-client-id",
  "prompt": {
    "node_id": {
      "inputs": {
        "input_name": value,
        "linked_input": ["source_node_id", output_index]
      },
      "class_type": "NodeClassName"
    }
  }
}
```

### 10.2 节点连接格式

```json
{
  "6": {
    "inputs": {
      "text": "positive prompt",
      "clip": ["4", 1]  // 连接到节点 4 的第 2 个输出（索引从0开始）
    },
    "class_type": "CLIPTextEncode"
  },
  "4": {
    "inputs": {
      "ckpt_name": "model.ckpt"
    },
    "class_type": "CheckpointLoaderSimple"
  }
}
```

### 10.3 从 Web UI 导出工作流

1. 在 ComfyUI Web 界面中完成工作流设计
2. 点击 "Save (API Format)" 按钮
3. 保存为 JSON 文件
4. 使用此 JSON 作为 API 请求的 prompt 参数

---

## 附录 A：常见问题

### Q1: 如何修改工作流参数？

```python
with open("workflow.json", "r") as f:
    workflow = json.load(f)

# 修改种子
workflow["3"]["inputs"]["seed"] = 12345

# 修改提示词
workflow["6"]["inputs"]["text"] = "new prompt"

# 修改模型
workflow["4"]["inputs"]["ckpt_name"] = "new_model.ckpt"
```

### Q2: 如何获取所有可用模型？

```python
response = requests.get("http://localhost:8188/models/checkpoints")
models = response.json()
print(models)
```

### Q3: API 返回 403 错误？

- 检查 ComfyUI 是否启用了 CORS
- 确保请求来源与 ComfyUI 服务器匹配
- 使用 `--enable-cors-header` 启动 ComfyUI

---

## 附录 B：错误码

| HTTP 状态码 | 含义 |
|-------------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 403 | 禁止访问（CORS/Origin 不匹配）|
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

---

**注意**: 本文档基于 ComfyUI v0.16.4。API 可能随版本更新而变化，请以实际代码为准。
