# ComfyUI 清空 GPU 显存

## 方法 1: 使用空工作流（推荐）

在 Web UI 中导入空工作流文件：

```
/mnt/data/project/ComfyUI/workflows/empty_gpu_cleanup.json
```

点击 **Queue Prompt** 执行即可清空显存。

## 方法 2: 使用脚本（需要关闭认证）

```bash
cd /mnt/data/project/ComfyUI/workflows
python clear_gpu_cache.py
```

## 方法 3: 手动清空（最快）

直接在浏览器访问并执行空工作流：

```bash
curl -X POST http://localhost:8188/prompt \
  -H "Content-Type: application/json" \
  -d '{"prompt": {}}'
```

## 方法 4: 通过队列清空

```bash
# 清除所有队列中的任务（会触发垃圾回收）
curl -X POST http://localhost:8188/queue \
  -H "Content-Type: application/json" \
  -d '{"clear": true}'
```

## 为什么有效？

执行空工作流后，ComfyUI 会：
1. 完成当前正在执行的任务
2. 卸载所有模型
3. 触发 Python 垃圾回收
4. 释放显存

## 查看显存状态

```bash
# 通过 API 查看
curl http://localhost:8188/system_stats | python -m json.tool

# 或直接用 nvidia-smi
watch -n 1 nvidia-smi
```

## 文件说明

- `empty_gpu_cleanup.json` - 空工作流定义
- `clear_gpu_cache.py` - Python 自动清理脚本

**注意**: 如果启用了认证，需要通过 Web UI 或配置 API_KEY_DISABLED=true
