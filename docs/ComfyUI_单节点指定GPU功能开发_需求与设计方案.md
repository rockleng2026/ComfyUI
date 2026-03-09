# ComfyUI 单节点指定 GPU 功能开发 – 需求与设计方案

**文档版本**：1.0  
**最后更新**：2026-03-09  
**作者**：AI 助手  
**项目仓库**：`https://github.com/rockleng2026/ComfyUI.it`  
**工作目录**：`/mnt/data/project/ComfyUI`  

---

## 1. 需求概述

在现有的 ComfyUI 框架中，所有节点默认在单一 GPU（或 CPU）上执行，无法充分利用多卡服务器的算力与显存。本需求旨在为 ComfyUI 增加**单节点指定 GPU** 的能力，允许用户通过工作流界面为特定节点选择执行设备（如 `cuda:0`、`cuda:1`、`cuda:2`、`cpu`），从而实现：

- **显存负载均衡**：将不同模型组件分配到不同 GPU，避免单卡显存溢出（OOM）。
- **流水线并行**：使 CLIP、UNet、VAE 等顺序执行的节点分布在多张卡上，缓解显存压力。
- **灵活的资源利用**：可根据节点计算特性，将重型计算（如 UNet 采样）分配给性能更强的 GPU。

**目标示例工作流**：
- `CLIPTextEncode` → 运行于 `cuda:0`
- `KSampler`（UNet） → 运行于 `cuda:1`
- `VAEDecode` → 运行于 `cuda:2`

---

## 2. 初步设计方案

### 2.1 原理说明

ComfyUI 的每个节点本质是一个 Python 类，其执行函数负责处理张量运算。PyTorch 支持通过 `.to(device)` 方法将模型或张量移动到指定设备。ComfyUI 的数据流引擎会自动在不同设备间迁移张量，因此只需在节点执行前将相关模型和输入数据手动迁移到目标设备，即可实现节点级设备控制。

### 2.2 代码修改点

需要修改的核心节点类（以官方源码为例，用户仓库 `ComfyUI.it` 结构应与官方一致）：

| 节点类型         | 文件路径（相对于项目根目录）            | 修改内容                                                                                       |
|------------------|----------------------------------------|------------------------------------------------------------------------------------------------|
| `CLIPTextEncode` | `comfy/clip.py` 或 `nodes.py`          | 在 `INPUT_TYPES` 中添加 `device` 下拉选项，在 `encode` 方法中将 `clip` 模型移动到指定设备。     |
| `KSampler`       | `comfy/sample.py` 或 `nodes.py`        | 增加 `device` 参数，在采样前将 `model` 和 `latent_image` 等张量移动到目标设备。                 |
| `VAEDecode`      | `comfy/vae.py` 或 `nodes.py`            | 增加 `device` 参数，在解码前将 `vae` 模型和 `samples` 移动到目标设备。                          |
| 其他节点（可选） | 对应实现文件                            | 参照上述模式，为需要指定设备的节点添加 `device` 参数。                                         |

**示例代码片段（以 KSampler 为例）**：

```python
# 在节点的 INPUT_TYPES 中增加 device 选项
@classmethod
def INPUT_TYPES(cls):
    return {
        "required": {
            "device": (["cuda:0", "cuda:1", "cuda:2", "cpu"], {"default": "cuda:0"}),
            # ... 保留原有参数
        }
    }

# 在采样函数中处理设备迁移
def sample(self, device, model, seed, steps, ...):
    # 将模型移动到指定设备
    model = model.to(device)
    # 将输入张量移动到同一设备（如有必要）
    latent_image = latent_image.to(device) if latent_image is not None else None
    # ... 执行原有采样逻辑
    return (result,)
2.3 工作流示例
以下 JSON 片段展示了节点中 device 参数的存储方式（以 widgets_values 形式体现）：

json
{
  "6": {
    "class_type": "CLIPTextEncode",
    "inputs": { "clip": ["4", 1] },
    "widgets_values": ["a beautiful landscape", "cuda:0"]
  },
  "8": {
    "class_type": "KSampler",
    "inputs": { "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["5", 0] },
    "widgets_values": [234, "fixed", 20, 8, "euler", "normal", 1, "cuda:1"]
  },
  "9": {
    "class_type": "VAEDecode",
    "inputs": { "samples": ["8", 0], "vae": ["4", 2] },
    "widgets_values": ["cuda:2"]
  }
}
完整工作流文件可参考本文档附录或单独提供的 multi_gpu_workflow.json。

3. 本地开发环境配置
3.1 硬件
GPU：4 × NVIDIA GeForce RTX 5090

CPU：与主板匹配的 x86_64 处理器

内存：建议 ≥ 64GB

3.2 操作系统
发行版：Ubuntu 24.04 LTS

内核：最新稳定版

NVIDIA 驱动：已安装（≥ 535 版本，支持 RTX 5090）

CUDA 工具包：建议 CUDA 12.2 或更高（与驱动兼容）

3.3 软件依赖
Python：conda 环境使用 3.12 
# 激活环境
conda activate comfyui-312

PyTorch：≥ 2.0.0（需支持 CUDA 12）

ComfyUI 依赖项：通过 pip install -r requirements.txt 安装

3.4 代码仓库
远程仓库：https://github.com/rockleng2026/ComfyUI.it

本地工作目录：/mnt/data/project/ComfyUI

默认分支：master（建议创建功能分支进行开发）

3.5 网络代理配置
在终端中执行以下命令设置代理（用于 git clone、pip install 等）：

bash
export http_proxy="http://192.168.0.250:10808"
export https_proxy="http://192.168.0.250:10808"
若需持久化，可将上述命令添加到 ~/.bashrc 或 ~/.zshrc。

3.6 Conda 环境
bash
# 激活已有环境
conda activate comfyui-312

# 确认环境信息
which python   # 应指向 conda 环境下的 python
python --version  # 应为 3.12.x
4. 开发过程要求
4.1 版本控制
所有修改应基于 master 分支创建功能分支，例如 feature/node-device-control。

提交信息需清晰描述改动内容，遵循 Conventional Commits 规范。

完成开发后，通过 Pull Request 合并回主分支（如有权限）。

4.2 编码规范
遵循 PEP 8 编码风格。

添加必要的注释，尤其是设备迁移的关键代码段。

保持与原代码风格一致，避免不必要的格式化改动。

4.3 测试要求
单元测试：为修改的节点编写简单测试，验证设备迁移是否生效（例如检查模型所在设备）。

集成测试：运行包含多节点指定设备的工作流，观察 GPU 占用和显存分布是否符合预期。

回归测试：确保未修改设备参数的节点行为不变。

4.4 文档更新
每次代码修改后，同步更新本文档的实施Checklist状态。

最终提供一份可导入的示例工作流 JSON 文件，并附使用说明。

如有必要，在项目 README.md 中添加多 GPU 使用的说明。

文档统一放到 docs目录下

5. 实施 Checklist
5.1 环境准备
确认工作目录 /mnt/data/project/ComfyUI 存在，并已克隆最新代码。

激活 conda 环境 comfyui-312。

安装项目依赖：pip install -r requirements.txt（使用代理）。

验证 ComfyUI 能否正常运行：python main.py。

创建功能分支：git checkout -b feature/node-device-control。

5.2 代码修改
分析源码：找到 CLIPTextEncode、KSampler、VAEDecode 的定义位置。

修改 CLIPTextEncode：

在 INPUT_TYPES 中添加 device 参数。

修改 encode 函数，增加 device 形参，并在函数体内将 clip 模型移动到该设备。

修改 KSampler：

增加 device 参数。

在采样前将 model 和必要的张量（如 latent_image）移动到目标设备。

修改 VAEDecode：

增加 device 参数。

在解码前将 vae 模型和 samples 移动到目标设备。

可选：为其他常用节点（如 ControlNet、LoadImage 等）添加类似支持。

5.3 构建与测试
运行 ComfyUI：python main.py，检查启动是否正常。

打开 Web UI：访问 http://127.0.0.1:8188，查看节点面板中是否出现 device 下拉选项。

单元测试（手动）：

放置三个节点，分别选择不同 GPU。

在代码中添加临时打印语句，输出模型所在设备，确认迁移成功。

集成测试：

使用下方示例工作流（或附录中的 JSON 文件），观察三张 GPU 的显存占用和计算负载（可用 nvidia-smi 监控）。

确认最终图像生成无误。

5.4 工作流验证
创建包含以下映射的工作流并运行：

CLIPTextEncode → cuda:0

KSampler → cuda:1

VAEDecode → cuda:2

验证显存分布符合预期（可适当增大分辨率或增加 ControlNet 以制造显存压力）。

测试回退兼容性：不选择 device 时，节点应默认使用原有设备（通常为 cuda:0 或 cpu）。

5.5 文档归档
将示例工作流导出为 JSON 文件，保存至项目 workflows/ 目录（如不存在则创建）。

更新本文档的附录，添加工作流使用说明。

提交代码并推送至远程仓库：git push origin feature/node-device-control。

如有权限，创建 Pull Request 并请求评审。

附录：示例工作流 JSON
将以下内容保存为 multi_gpu_demo.json，然后在 ComfyUI 中通过“Load”按钮导入。

json
{
  "last_node_id": 10,
  "last_link_id": 9,
  "nodes": [
    {
      "id": 6,
      "type": "CLIPTextEncode",
      "pos": [200, 100],
      "size": {"0": 425.78, "1": 180.61},
      "flags": {},
      "order": 1,
      "mode": 0,
      "inputs": [{"name": "clip", "type": "CLIP", "link": 2}],
      "outputs": [{"name": "CONDITIONING", "type": "CONDITIONING", "links": [4], "slot_index": 0}],
      "properties": {"Node name for S&R": "CLIPTextEncode"},
      "widgets_values": ["a beautiful landscape", "cuda:0"]
    },
    {
      "id": 7,
      "type": "CLIPTextEncode",
      "pos": [200, 300],
      "size": {"0": 425.78, "1": 180.61},
      "flags": {},
      "order": 2,
      "mode": 0,
      "inputs": [{"name": "clip", "type": "CLIP", "link": 3}],
      "outputs": [{"name": "CONDITIONING", "type": "CONDITIONING", "links": [5], "slot_index": 0}],
      "properties": {"Node name for S&R": "CLIPTextEncode"},
      "widgets_values": ["text, watermark", "cuda:0"]
    },
    {
      "id": 8,
      "type": "KSampler",
      "pos": [700, 200],
      "size": {"0": 320, "1": 326},
      "flags": {},
      "order": 4,
      "mode": 0,
      "inputs": [
        {"name": "model", "type": "MODEL", "link": 1},
        {"name": "positive", "type": "CONDITIONING", "link": 4},
        {"name": "negative", "type": "CONDITIONING", "link": 5},
        {"name": "latent_image", "type": "LATENT", "link": 6}
      ],
      "outputs": [{"name": "LATENT", "type": "LATENT", "links": [7], "slot_index": 0}],
      "properties": {"Node name for S&R": "KSampler"},
      "widgets_values": [234, "fixed", 20, 8, "euler", "normal", 1, "cuda:1"]
    },
    {
      "id": 9,
      "type": "VAEDecode",
      "pos": [1100, 200],
      "size": {"0": 210, "1": 46},
      "flags": {},
      "order": 5,
      "mode": 0,
      "inputs": [
        {"name": "samples", "type": "LATENT", "link": 7},
        {"name": "vae", "type": "VAE", "link": 8}
      ],
      "outputs": [{"name": "IMAGE", "type": "IMAGE", "links": [9], "slot_index": 0}],
      "properties": {"Node name for S&R": "VAEDecode"},
      "widgets_values": ["cuda:2"]
    },
    {
      "id": 10,
      "type": "SaveImage",
      "pos": [1400, 200],
      "size": {"0": 280, "1": 46},
      "flags": {},
      "order": 6,
      "mode": 0,
      "inputs": [{"name": "images", "type": "IMAGE", "link": 9}],
      "properties": {"Node name for S&R": "SaveImage"},
      "widgets_values": ["ComfyUI"]
    },
    {
      "id": 4,
      "type": "CheckpointLoaderSimple",
      "pos": [200, 500],
      "size": {"0": 280, "1": 46},
      "flags": {},
      "order": 0,
      "mode": 0,
      "outputs": [
        {"name": "MODEL", "type": "MODEL", "links": [1], "slot_index": 0},
        {"name": "CLIP", "type": "CLIP", "links": [2, 3], "slot_index": 1},
        {"name": "VAE", "type": "VAE", "links": [8], "slot_index": 2}
      ],
      "properties": {"Node name for S&R": "CheckpointLoaderSimple"},
      "widgets_values": ["v1-5-pruned.ckpt"]
    },
    {
      "id": 5,
      "type": "EmptyLatentImage",
      "pos": [700, 400],
      "size": {"0": 315, "1": 106},
      "flags": {},
      "order": 3,
      "mode": 0,
      "outputs": [{"name": "LATENT", "type": "LATENT", "links": [6], "slot_index": 0}],
      "properties": {"Node name for S&R": "EmptyLatentImage"},
      "widgets_values": [512, 512, 1]
    }
  ],
  "links": [
    [1, 4, 0, 8, 0, "MODEL"],
    [2, 4, 1, 6, 0, "CLIP"],
    [3, 4, 1, 7, 0, "CLIP"],
    [4, 6, 0, 8, 1, "CONDITIONING"],
    [5, 7, 0, 8, 2, "CONDITIONING"],
    [6, 5, 0, 8, 3, "LATENT"],
    [7, 8, 0, 9, 0, "LATENT"],
    [8, 4, 2, 9, 1, "VAE"],
    [9, 9, 0, 10, 0, "IMAGE"]
  ],
  "groups": [],
  "config": {},
  "extra": {},
  "version": 0.4
}
使用方法：

将上述 JSON 保存为 .json 文件。

在 ComfyUI 界面中点击“Load”按钮，选择该文件。

根据需要修改模型路径（CheckpointLoaderSimple 中的 widgets_values）。

点击“Queue Prompt”运行，观察各 GPU 负载。