#!/usr/bin/env python3
"""
ComfyUI API 文生图测试脚本（带 Token 认证）
测试多 GPU 功能：CLIPTextEncode、KSampler、VAEDecode 分别运行在不同 GPU

使用方法:
    python test_api_with_token.py
    
要求:
    - ComfyUI 服务已启动并开启 Token 认证
    - 已安装依赖：pip install requests
    - 已下载模型：models/checkpoints/v1-5-pruned.ckpt
"""

import requests
import json
import time
import os

# 禁用代理
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''
os.environ['NO_PROXY'] = '*'

# ComfyUI 服务器地址
SERVER = "127.0.0.1:40800"
BASE_URL = f"http://{SERVER}"
# 替换为你的 Token
API_TOKEN = ""

# 认证请求头
HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

WORKFLOW_FILE = "workflow_api.json"
OUTPUT_DIR = "outputs"

# 获取脚本所在目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def check_server():
    """检查 ComfyUI 服务状态（带认证）"""
    print("=" * 60)
    print("检查 ComfyUI 服务...")
    try:
        response = requests.get(f"{BASE_URL}/system_stats", headers=HEADERS, timeout=5)
        
        if response.status_code == 401:
            print("✗ 认证失败 (401 Unauthorized)")
            print("  请检查 Token 是否正确配置")
            return False
        elif response.status_code != 200:
            print(f"✗ 连接失败：HTTP {response.status_code}")
            return False
            
        stats = response.json()
        print("✓ 认证通过，服务正常运行")
        print(f"  版本：{stats['system']['comfyui_version']}")
        print(f"  PyTorch: {stats['system']['pytorch_version']}")
        
        print(f"\n  GPU 设备:")
        for device in stats['devices']:
            vram_gb = device['vram_total'] / 1024**3
            free_gb = device['vram_free'] / 1024**3
            print(f"    [{device['index']}] {device['name']}")
            print(f"        VRAM: {free_gb:.1f}GB / {vram_gb:.1f}GB")
        return True
    except requests.exceptions.ConnectionError:
        print("✗ 无法连接到服务器")
        return False
    except Exception as e:
        print(f"✗ 错误：{e}")
        return False


def load_workflow():
    """加载工作流 JSON"""
    workflow_path = os.path.join(SCRIPT_DIR, WORKFLOW_FILE)
    print(f"\n加载工作流：{workflow_path}")
    with open(workflow_path, "r", encoding="utf-8") as f:
        workflow = json.load(f)
    
    print("✓ 工作流配置:")
    print(f"  正面提示词：{workflow['6']['inputs']['text']}")
    print(f"  负面提示词：{workflow['7']['inputs']['text']}")
    print(f"\n  GPU 分配:")
    print(f"    CLIPTextEncode (节点 6): {workflow['6']['inputs']['device']}")
    print(f"    CLIPTextEncode (节点 7): {workflow['7']['inputs']['device']}")
    print(f"    KSampler (节点 8):       {workflow['8']['inputs']['device']}")
    print(f"    VAEDecode (节点 9):      {workflow['9']['inputs']['device']}")
    print(f"\n  生成参数:")
    print(f"    分辨率：{workflow['5']['inputs']['width']}x{workflow['5']['inputs']['height']}")
    print(f"    步数：{workflow['8']['inputs']['steps']}")
    print(f"    种子：{workflow['8']['inputs']['seed']}")
    
    return workflow


def submit_workflow(workflow):
    """提交工作流到队列（带认证）"""
    print(f"\n提交工作流...")
    response = requests.post(
        f"{BASE_URL}/prompt",
        headers=HEADERS,
        json={"prompt": workflow, "client_id": "text2img_token_demo"}
    )
    
    if response.status_code == 401:
        print("✗ 认证失败，请检查 Token")
        return None
    
    result = response.json()
    prompt_id = result['prompt_id']
    print(f"✓ 已提交")
    print(f"  Prompt ID: {prompt_id}")
    print(f"  Queue Number: {result['number']}")
    return prompt_id


def wait_for_completion(prompt_id, timeout=300):
    """等待执行完成（带认证）"""
    print(f"\n等待执行完成...")
    start_time = time.time()
    
    while True:
        elapsed = time.time() - start_time
        if elapsed > timeout:
            print(f"✗ 超时 ({timeout}s)")
            return None
        
        response = requests.get(
            f"{BASE_URL}/history/{prompt_id}",
            headers=HEADERS,
            timeout=5
        )
        
        if response.status_code == 401:
            print("✗ 认证失败")
            return None
        
        history = response.json()
        
        if prompt_id in history:
            print(f"✓ 执行完成 (耗时：{elapsed:.1f}s)")
            return history[prompt_id]
        
        if int(elapsed) % 5 == 0:
            print(f"  等待中... {elapsed:.0f}s", end="\r")
        
        time.sleep(1)


def download_image(prompt_id, save_dir=OUTPUT_DIR):
    """下载生成的图片（带认证）"""
    print(f"\n获取生成结果...")
    
    # 使用绝对路径保存
    save_dir = os.path.join(SCRIPT_DIR, save_dir)
    
    response = requests.get(
        f"{BASE_URL}/history/{prompt_id}",
        headers=HEADERS,
        timeout=5
    )
    
    if response.status_code != 200:
        print(f"✗ 获取历史失败：HTTP {response.status_code}")
        return None
        
    history = response.json()
    data = history[prompt_id]
    
    status = data.get('status', {}).get('status_str', 'unknown')
    print(f"  状态：{status}")
    
    if status != 'success':
        print(f"✗ 执行失败")
        return None
    
    outputs = data['outputs']
    # 查找包含 images 的输出节点（可能是 SaveImage 节点 10 或其他）
    output_node = None
    for node_id in ['10', '9', '8']:  # 按优先级查找
        if node_id in outputs and 'images' in outputs[node_id]:
            output_node = node_id
            break
    
    if not output_node:
        print(f"✗ 未找到输出节点")
        print(f"  可用输出：{list(outputs.keys())}")
        return None
    
    images = outputs[output_node]['images']
    if not images:
        print(f"✗ 未找到生成的图片")
        return None
    
    os.makedirs(save_dir, exist_ok=True)
    
    downloaded = []
    for i, img_info in enumerate(images):
        print(f"\n  图片 {i+1}: {img_info['filename']}")
        
        params = {
            "filename": img_info['filename'],
            "subfolder": img_info.get('subfolder', ''),
            "type": img_info.get('type', 'output')
        }
        
        response = requests.get(
            f"{BASE_URL}/view",
            params=params,
            headers=HEADERS,
            timeout=30
        )
        
        output_path = os.path.join(save_dir, img_info['filename'])
        with open(output_path, 'wb') as f:
            f.write(response.content)
        print(f"    ✓ 已保存：{output_path}")
        print(f"    大小：{len(response.content) / 1024:.1f} KB")
        downloaded.append(output_path)
    
    return downloaded


def main():
    """主函数"""
    print("=" * 60)
    print("ComfyUI 多 GPU 文生图测试（带 Token 认证）")
    print("=" * 60)
    
    # 1. 检查服务
    if not check_server():
        print("\n请检查:")
        print("  1. ComfyUI 服务器是否运行")
        print("  2. Token 是否正确配置")
        print(f"  3. 服务器地址：{BASE_URL}")
        return 1
    
    # 2. 加载工作流
    workflow = load_workflow()
    
    # 3. 提交
    prompt_id = submit_workflow(workflow)
    if not prompt_id:
        return 1
    
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
    print(f"  生成图片：{len(images)} 张")
    for img in images:
        print(f"    - {img}")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    exit(main())
