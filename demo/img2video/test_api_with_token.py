#!/usr/bin/env python3
"""
ComfyUI API MOVA 图生视频测试脚本（带 Token 认证）
使用参考图片和文本提示生成同步视频和音频

使用方法:
    python test_api_with_token.py
    
要求:
    - ComfyUI 服务已启动并开启 Token 认证
    - 已安装 MOVA 节点：custom_nodes/ComfyUI_RH_MOVA
    - 已下载模型：models/MOVA/MOVA-360p 或 MOVA-720p
    - GPU 显存 >= 32GB (RTX 4090/5090 可用 group offload)
    
注意事项:
    - 首次加载模型需要 1-2 分钟
    - 视频生成需要 10-20 分钟 (97 帧 @ 24fps = 4 秒视频)
    - 确保有足够显存 (~12GB with group offload)
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
SERVER = "127.0.0.1:1800"
BASE_URL = f"http://{SERVER}"
# 替换为你的 Token
API_TOKEN = ""


# 认证请求头
HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

WORKFLOW_FILE = "workflow_api.json"
IMAGE_FILE = "input_image.jpg"
OUTPUT_DIR = "outputs"

# 获取脚本所在目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def check_server():
    """检查 ComfyUI 服务状态（带认证）"""
    print("=" * 70)
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
        
        print(f"\n  GPU 设备:")
        for device in stats['devices']:
            vram_gb = device['vram_total'] / 1024**3
            free_gb = device['vram_free'] / 1024**3
            print(f"    [{device['index']}] {device['name']}")
            print(f"        VRAM: {free_gb:.1f}GB / {vram_gb:.1f}GB free")
        return True
    except requests.exceptions.ConnectionError:
        print("✗ 无法连接到服务器")
        return False
    except Exception as e:
        print(f"✗ 错误：{e}")
        return False


def upload_image():
    """上传参考图片（带认证）"""
    image_path = os.path.join(SCRIPT_DIR, IMAGE_FILE)
    print(f"\n上传参考图片：{image_path}")
    
    if not os.path.exists(image_path):
        print(f"✗ 图片不存在：{image_path}")
        return None
    
    with open(image_path, "rb") as f:
        files = {"image": f}
        data = {
            "type": "input",
            "subfolder": "",
            "overwrite": "true"
        }
        response = requests.post(
            f"{BASE_URL}/upload/image",
            files=files,
            data=data,
            headers={"Authorization": f"Bearer {API_TOKEN}"}
        )
    
    if response.status_code == 401:
        print("✗ 认证失败，请检查 Token")
        return None
        
    if response.status_code != 200:
        print(f"✗ 上传失败：{response.status_code}")
        return None
    
    result = response.json()
    print(f"✓ 上传成功：{result['name']}")
    return result['name']


def load_workflow(image_name):
    """加载并配置工作流"""
    workflow_path = os.path.join(SCRIPT_DIR, WORKFLOW_FILE)
    print(f"\n加载工作流：{workflow_path}")
    with open(workflow_path, "r", encoding="utf-8") as f:
        workflow = json.load(f)
    
    workflow["1"]["inputs"]["image"] = image_name
    
    print("✓ 工作流配置:")
    print(f"  参考图片：{image_name}")
    print(f"  提示词：{workflow['10']['inputs']['value'][:40]}...")
    print(f"\n  MOVA 配置:")
    print(f"    模型：{workflow['2']['inputs']['model_name']}")
    print(f"    设备：{workflow['2']['inputs']['device']}")
    print(f"    Offload: {workflow['2']['inputs']['offload_mode']}")
    print(f"    Dtype: {workflow['2']['inputs']['dtype']}")
    print(f"\n  生成参数:")
    print(f"    分辨率：{workflow['3']['inputs']['width']}x{workflow['3']['inputs']['height']}")
    print(f"    帧数：{workflow['3']['inputs']['num_frames']} ({workflow['3']['inputs']['num_frames']/24:.1f}秒)")
    print(f"    FPS: {workflow['3']['inputs']['fps']}")
    print(f"    步数：{workflow['3']['inputs']['steps']}")
    
    return workflow


def submit_workflow(workflow):
    """提交工作流到队列（带认证）"""
    print(f"\n提交工作流...")
    print("  ⚠️  MOVA 生成较慢，预计 10-20 分钟...")
    
    response = requests.post(
        f"{BASE_URL}/prompt",
        headers=HEADERS,
        json={"prompt": workflow, "client_id": "img2video_token_demo"}
    )
    
    if response.status_code == 401:
        print("✗ 认证失败，请检查 Token")
        return None
    
    result = response.json()
    prompt_id = result['prompt_id']
    print(f"✓ 已提交")
    print(f"  Prompt ID: {prompt_id}")
    return prompt_id


def wait_for_completion(prompt_id, timeout=1200):
    """等待执行完成（带认证）"""
    print(f"\n等待生成完成...")
    start_time = time.time()
    
    while True:
        elapsed = time.time() - start_time
        if elapsed > timeout:
            print(f"\n  ⚠️  超时 ({timeout}s)")
            return None
        
        try:
            response = requests.get(
                f"{BASE_URL}/history/{prompt_id}",
                headers=HEADERS,
                timeout=5
            )
            
            if response.status_code == 401:
                print("\n  ✗ 认证失败")
                return None
                
            history = response.json()
            
            if prompt_id in history:
                mins = int(elapsed) // 60
                secs = int(elapsed) % 60
                print(f"\n  ✓ 完成! (耗时：{mins}分{secs}秒)")
                return history[prompt_id]
        except:
            pass
        
        if int(elapsed) % 15 == 0:
            mins = int(elapsed) // 60
            secs = int(elapsed) % 60
            print(f"  ⏱️  {mins}分{secs}秒...", end="\r")
        
        time.sleep(3)


def download_video(prompt_id, save_dir=OUTPUT_DIR):
    """下载生成的视频（带认证）"""
    print(f"\n获取生成结果...")
    
    # 使用绝对路径保存
    save_dir = os.path.join(SCRIPT_DIR, save_dir)
    
    response = requests.get(
        f"{BASE_URL}/history/{prompt_id}",
        headers=HEADERS,
        timeout=5
    )
    
    if response.status_code != 200:
        print(f"  ✗ 获取历史失败：HTTP {response.status_code}")
        return None
        
    history = response.json()
    data = history[prompt_id]
    
    status = data.get('status', {}).get('status_str', 'unknown')
    print(f"  状态：{status}")
    
    if status != 'success':
        print(f"  ✗ 执行失败")
        if 'messages' in data.get('status', {}):
            for msg in data['status']['messages']:
                print(f"    {msg}")
        return None
    
    outputs = data['outputs']
    if '4' not in outputs:
        print(f"  ✗ 未找到视频输出节点")
        return None
    
    videos = outputs['4'].get('images', [])
    if not videos:
        print(f"  ✗ 未找到视频")
        return None
    
    os.makedirs(save_dir, exist_ok=True)
    
    downloaded = []
    for i, video_info in enumerate(videos):
        print(f"\n  视频 {i+1}: {video_info['filename']}")
        
        params = {
            "filename": video_info['filename'],
            "subfolder": video_info.get('subfolder', ''),
            "type": video_info.get('type', 'output')
        }
        
        print(f"  下载中...", end=" ")
        try:
            response = requests.get(
                f"{BASE_URL}/view",
                params=params,
                headers=HEADERS,
                timeout=120
            )
            
            if response.status_code == 401:
                print("✗ 认证失败")
                return None
                
            if response.status_code == 200:
                output_path = os.path.join(save_dir, video_info['filename'])
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                size_mb = len(response.content) / 1024 / 1024
                print(f"✓ ({size_mb:.1f} MB)")
                print(f"  保存：{output_path}")
                downloaded.append(output_path)
            else:
                print(f"✗ HTTP {response.status_code}")
        except Exception as e:
            print(f"✗ {e}")
    
    return downloaded


def main():
    """主函数"""
    print("=" * 70)
    print("ComfyUI MOVA 图生视频测试（带 Token 认证）")
    print("=" * 70)
    
    # 1. 检查服务
    if not check_server():
        print("\n请检查:")
        print("  1. ComfyUI 服务器是否运行")
        print("  2. Token 是否正确配置")
        print(f"  3. 服务器地址：{BASE_URL}")
        return 1
    
    # 2. 上传图片
    image_name = upload_image()
    if not image_name:
        return 1
    
    # 3. 加载工作流
    workflow = load_workflow(image_name)
    
    # 4. 提交
    prompt_id = submit_workflow(workflow)
    if not prompt_id:
        return 1
    
    # 5. 等待
    result = wait_for_completion(prompt_id)
    if not result:
        return 1
    
    # 6. 下载视频
    videos = download_video(prompt_id)
    if not videos:
        return 1
    
    print(f"\n" + "=" * 70)
    print("✓ 测试完成!")
    print(f"  生成视频：{len(videos)} 个")
    for video in videos:
        print(f"    - {video}")
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    exit(main())
