#!/usr/bin/env python3
"""
ComfyUI API 文生图测试脚本
测试多 GPU 功能：CLIPTextEncode、KSampler、VAEDecode 分别运行在不同 GPU

使用方法:
    python test_api.py
    
要求:
    - ComfyUI 服务已启动: python main.py --listen 0.0.0.0
    - 已安装依赖: pip install requests Pillow
    - 已下载模型: models/checkpoints/v1-5-pruned.ckpt
"""

import requests
import json
import time
from PIL import Image
from io import BytesIO
import os

# ComfyUI 服务器地址
SERVER = "127.0.0.1:8188"
BASE_URL = f"http://{SERVER}"
WORKFLOW_FILE = "workflow_api.json"
OUTPUT_DIR = "outputs"

def check_server():
    """检查 ComfyUI 服务状态"""
    print("=" * 60)
    print("检查 ComfyUI 服务...")
    try:
        response = requests.get(f"{BASE_URL}/system_stats", timeout=5)
        stats = response.json()
        print("✓ 服务正常运行")
        print(f"  版本: {stats['system']['comfyui_version']}")
        print(f"  PyTorch: {stats['system']['pytorch_version']}")
        
        print(f"\n  GPU 设备:")
        for device in stats['devices']:
            vram_gb = device['vram_total'] / 1024**3
            free_gb = device['vram_free'] / 1024**3
            print(f"    [{device['index']}] {device['name']}")
            print(f"        VRAM: {free_gb:.1f}GB / {vram_gb:.1f}GB")
        return True
    except Exception as e:
        print(f"✗ 连接失败: {e}")
        print("  请确保 ComfyUI 已启动: python main.py --listen 0.0.0.0")
        return False

def load_workflow():
    """加载工作流 JSON"""
    print(f"\n加载工作流: {WORKFLOW_FILE}")
    with open(WORKFLOW_FILE, "r") as f:
        workflow = json.load(f)
    
    # 显示配置
    print("✓ 工作流配置:")
    print(f"  正面提示词: {workflow['6']['inputs']['text']}")
    print(f"  负面提示词: {workflow['7']['inputs']['text']}")
    print(f"\n  GPU 分配:")
    print(f"    CLIPTextEncode (节点6): {workflow['6']['inputs']['device']}")
    print(f"    CLIPTextEncode (节点7): {workflow['7']['inputs']['device']}")
    print(f"    KSampler (节点8):       {workflow['8']['inputs']['device']}")
    print(f"    VAEDecode (节点9):      {workflow['9']['inputs']['device']}")
    print(f"\n  生成参数:")
    print(f"    分辨率: {workflow['5']['inputs']['width']}x{workflow['5']['inputs']['height']}")
    print(f"    步数: {workflow['8']['inputs']['steps']}")
    print(f"    种子: {workflow['8']['inputs']['seed']}")
    
    return workflow

def submit_workflow(workflow):
    """提交工作流到队列"""
    print(f"\n提交工作流...")
    response = requests.post(
        f"{BASE_URL}/prompt",
        json={"prompt": workflow, "client_id": "text2img_demo"}
    )
    result = response.json()
    prompt_id = result['prompt_id']
    print(f"✓ 已提交")
    print(f"  Prompt ID: {prompt_id}")
    print(f"  Queue Number: {result['number']}")
    return prompt_id

def wait_for_completion(prompt_id, timeout=300):
    """等待执行完成"""
    print(f"\n等待执行完成...")
    start_time = time.time()
    
    while True:
        elapsed = time.time() - start_time
        if elapsed > timeout:
            print(f"✗ 超时 ({timeout}s)")
            return None
        
        # 查询历史记录
        response = requests.get(f"{BASE_URL}/history/{prompt_id}")
        history = response.json()
        
        if prompt_id in history:
            print(f"✓ 执行完成 (耗时: {elapsed:.1f}s)")
            return history[prompt_id]
        
        # 显示进度
        if int(elapsed) % 5 == 0:
            print(f"  等待中... {elapsed:.0f}s", end="\r")
        
        time.sleep(1)

def download_image(prompt_id, save_dir=OUTPUT_DIR):
    """下载生成的图片"""
    print(f"\n获取生成结果...")
    
    # 获取历史记录
    response = requests.get(f"{BASE_URL}/history/{prompt_id}")
    history = response.json()
    data = history[prompt_id]
    
    # 检查状态
    status = data.get('status', {}).get('status_str', 'unknown')
    print(f"  状态: {status}")
    
    if status != 'success':
        print(f"✗ 执行失败")
        return None
    
    # 获取输出
    outputs = data['outputs']
    if '9' not in outputs:
        print(f"✗ 未找到输出节点")
        return None
    
    images = outputs['9']['images']
    if not images:
        print(f"✗ 未找到生成的图片")
        return None
    
    # 创建输出目录
    os.makedirs(save_dir, exist_ok=True)
    
    # 下载图片
    downloaded = []
    for i, img_info in enumerate(images):
        print(f"\n  图片 {i+1}: {img_info['filename']}")
        
        params = {
            "filename": img_info['filename'],
            "subfolder": img_info.get('subfolder', ''),
            "type": img_info.get('type', 'output')
        }
        
        response = requests.get(f"{BASE_URL}/view", params=params)
        image = Image.open(BytesIO(response.content))
        
        # 保存
        output_path = os.path.join(save_dir, img_info['filename'])
        image.save(output_path)
        print(f"    ✓ 已保存: {output_path}")
        print(f"    尺寸: {image.size}")
        downloaded.append(output_path)
    
    return downloaded

def main():
    """主函数"""
    print("=" * 60)
    print("ComfyUI 多 GPU 文生图测试")
    print("=" * 60)
    
    # 1. 检查服务
    if not check_server():
        return 1
    
    # 2. 加载工作流
    workflow = load_workflow()
    
    # 3. 提交
    prompt_id = submit_workflow(workflow)
    
    # 4. 等待
    result = wait_for_completion(prompt_id)
    if not result:
        return 1
    
    # 5. 下载图片
    images = download_image(prompt_id)
    if not images:
        return 1
    
    print(f"\n" + "=" * 60)
    print("✓ 测试完成!")
    print(f"  生成图片: {len(images)} 张")
    for img in images:
        print(f"    - {img}")
    print("=" * 60)
    
    return 0

if __name__ == "__main__":
    exit(main())
