# ComfyUI API Demo

本目录包含 ComfyUI API 调用示例，演示如何通过 REST API 程序化控制工作流执行。

## 目录结构

```
demo/
├── text2img/          # 文生图示例（多 GPU）
│   ├── workflow_api.json      # 工作流定义
│   ├── test_api.py            # Python 测试脚本
│   └── outputs/               # 生成图片输出目录
│
├── img2video/         # 图生视频示例（MOVA）
│   ├── workflow_api.json      # 工作流定义
│   ├── input_image.jpg        # 参考图片（示例）
│   ├── test_api.py            # Python 测试脚本
│   └── outputs/               # 生成视频输出目录
│
└── README.md          # 本说明文档
```

---

## 前置要求

### 1. 启动 ComfyUI 服务

```bash
cd /mnt/data/project/ComfyUI
python main.py --listen 0.0.0.0 --port 8188
```

服务启动后，API 地址为：`http://127.0.0.1:8188`

### 2. 安装 Python 依赖

```bash
pip install requests Pillow
```

### 3. 下载模型

#### 文生图
- 下载 Stable Diffusion 模型到 `models/checkpoints/`
- 文件名：`v1-5-pruned.ckpt`

#### 图生视频
- 下载 MOVA 模型到 `models/MOVA/`
- 支持：`MOVA-360p` 或 `MOVA-720p`
- GPU 要求：>= 32GB VRAM (RTX 4090/5090)

---

## 快速开始

### 示例 1: 文生图（多 GPU）

**工作流功能**:
- CLIPTextEncode → cuda:0
- KSampler → cuda:1  
- VAEDecode → cuda:2

**运行测试**:

```bash
cd demo/text2img
python test_api.py
```

**预期输出**:
```
============================================================
ComfyUI 多 GPU 文生图测试
============================================================
1. 检查文件...
   图片: workflow_api.json ✓

2. 检查 ComfyUI 服务...
✓ 服务正常运行
  版本: 0.16.4
  GPU [0]: NVIDIA GeForce RTX 5090 (30.9GB free)

3. 配置工作流...
✓ 工作流配置:
  正面提示词: a beautiful landscape with mountains and lake
  GPU 分配:
    CLIPTextEncode (节点6): cuda:0
    KSampler (节点8):       cuda:1
    VAEDecode (节点9):      cuda:2

4. 提交工作流...
✓ 已提交
  Prompt ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

5. 等待生成完成...
✓ 执行完成 (耗时: 5.2s)

6. 获取结果...
  状态: success
  ✓ 生成 1 张图片
    下载中... ✓
    已保存: outputs/ComfyUI_00001_.png
    尺寸: (512, 512)

============================================================
✓ 测试完成!
  生成图片: 1 张
    - outputs/ComfyUI_00001_.png
============================================================
```

### 示例 2: 图生视频（MOVA）

**工作流功能**:
- 使用参考图片和文本生成同步视频+音频
- 模型: MOVA-360p
- 分辨率: 640x352
- 时长: 4秒 (97帧 @ 24fps)

**运行测试**:

```bash
cd demo/img2video
python test_api.py
```

**预期输出**:
```
============================================================
ComfyUI MOVA 图生视频测试
============================================================
1. 检查文件...
   图片: input_image.jpg ✓
   工作流: workflow_api.json ✓

2. 上传图片...
✓ 上传成功: input_image.jpg

3. 配置工作流...
✓ 工作流配置:
  参考图片: input_image.jpg
  提示词: 一个女生对着镜头撒娇...
  MOVA 配置:
    模型: MOVA-360p
    设备: cuda:3
    Offload: group
  生成参数:
    分辨率: 640x352
    帧数: 97 (4.0秒)

4. 提交工作流...
  ⚠️  MOVA 生成较慢，预计 10-20 分钟...
✓ 已提交
  Prompt ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

5. 等待生成完成...
  ⏱️  1分0秒...
  ⏱️  2分0秒...
  ...
✓ 完成! (耗时: 15分30秒)

6. 获取结果...
  状态: success
  ✓ 生成 1 个视频

  视频 1: ComfyUI_00001_.mp4
  下载中... ✓ (2.3 MB)
  保存: outputs/ComfyUI_00001_.mp4

============================================================
✓ 测试完成!
  生成视频: 1 个
    - outputs/ComfyUI_00001_.mp4
============================================================
```

---

## 自定义工作流

### 修改提示词

编辑 `workflow_api.json` 中的文本节点：

```json
{
  "6": {
    "inputs": {
      "text": "你的自定义提示词",  // ← 修改这里
      "device": "cuda:0",
      "clip": ["4", 1]
    },
    "class_type": "CLIPTextEncode"
  }
}
```

### 修改 GPU 分配

```json
{
  "8": {
    "inputs": {
      "device": "cuda:0",  // ← 修改 GPU 设备
      "model": ["4", 0],
      "positive": ["6", 0]
    },
    "class_type": "KSampler"
  }
}
```

### 从 Web UI 导出工作流

1. 在 ComfyUI Web 界面中完成工作流设计
2. 点击 "Save (API Format)" 按钮
3. 保存为 `workflow_api.json`
4. 替换 demo 目录中的文件

---

## API 端点说明

### 核心端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/prompt` | POST | 提交工作流 |
| `/prompt` | GET | 获取队列状态 |
| `/history/{id}` | GET | 获取执行历史 |
| `/upload/image` | POST | 上传图片 |
| `/view` | GET | 下载图片/视频 |
| `/queue` | POST | 清除/删除队列 |
| `/interrupt` | POST | 中断当前执行 |

### Python 示例

```python
import requests
import json

# 1. 提交工作流
with open("workflow_api.json", "r") as f:
    workflow = json.load(f)

response = requests.post(
    "http://localhost:8188/prompt",
    json={"prompt": workflow}
)
prompt_id = response.json()["prompt_id"]

# 2. 等待完成
import time
while True:
    response = requests.get(f"http://localhost:8188/history/{prompt_id}")
    history = response.json()
    if prompt_id in history:
        break
    time.sleep(1)

# 3. 下载结果
data = history[prompt_id]
images = data['outputs']['9']['images']

for img in images:
    params = {
        "filename": img['filename'],
        "type": "output"
    }
    response = requests.get("http://localhost:8188/view", params=params)
    with open(img['filename'], 'wb') as f:
        f.write(response.content)
```

完整 API 文档请参考：`docs/ComfyUI_API_Documentation.md`

---

## 故障排查

### 问题 1: 连接失败

**症状**:
```
✗ 连接失败: HTTPConnectionPool(...)
```

**解决**:
```bash
# 检查 ComfyUI 是否运行
curl http://localhost:8188/system_stats

# 重新启动
python main.py --listen 0.0.0.0
```

### 问题 2: 模型未找到

**症状**:
```
Checkpoint not found: v1-5-pruned.ckpt
```

**解决**:
```bash
# 检查模型是否存在
ls models/checkpoints/

# 下载模型
# 从 HuggingFace 或 Civitai 下载 Stable Diffusion v1.5
```

### 问题 3: MOVA OOM

**症状**:
```
Allocation on device X would exceed allowed memory
```

**解决**:
- 确保使用 `offload_mode: group`
- 确保 GPU 显存 >= 32GB
- 或使用更小分辨率 (480x272)

### 问题 4: 队列卡住

**症状**:
任务长时间不执行

**解决**:
```bash
# 清除队列
curl -X POST http://localhost:8188/queue \
  -H "Content-Type: application/json" \
  -d '{"clear": true}'

# 中断当前任务
curl -X POST http://localhost:8188/interrupt
```

---

## 技术细节

### 多 GPU 实现

本示例演示的节点级 GPU 分配：
- 每个节点可独立指定 GPU 设备
- 支持 `cuda:0`, `cuda:1`, `cuda:2`, `cuda:3`
- 自动设备迁移和内存管理

### MOVA 视频生成

- 模型并行处理视频和音频
- 使用 group offload 节省显存
- 生成带音频的 MP4 视频

---

## 参考文档

- [ComfyUI API 完整文档](../docs/ComfyUI_API_Documentation.md)
- [MOVA GPU 设计文档](../docs/MOVA_GPU_Design.md)
- [多 GPU 功能设计](../docs/ComfyUI_单节点指定GPU功能开发_需求与设计方案.md)

---

## 更新日志

| 日期 | 版本 | 说明 |
|------|------|------|
| 2025-03-12 | 1.0 | 初始版本，添加文生图和图生视频示例 |

---

**注意**: 确保 ComfyUI 服务已启动后再运行测试脚本。
