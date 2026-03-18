#!/usr/bin/env python3
"""
清空 ComfyUI GPU 显存的工具脚本
通过执行空工作流强制卸载所有模型

使用方法:
    python clear_gpu_cache.py
"""

import requests
import json
import time

SERVER = "127.0.0.1:8188"
BASE_URL = f"http://{SERVER}"

# 空工作流 (没有任何节点)
EMPTY_WORKFLOW = {
    "last_node_id": 0,
    "last_link_id": 0,
    "nodes": [],
    "links": [],
    "groups": [],
    "config": {},
    "extra": {},
    "version": 0.4
}

def clear_gpu_cache():
    """执行空工作流清空显存"""
    print("=" * 60)
    print("清空 ComfyUI GPU 显存")
    print("=" * 60)
    
    # 1. 提交空工作流
    print("\n提交空工作流...")
    try:
        response = requests.post(
            f"{BASE_URL}/prompt",
            json={"prompt": EMPTY_WORKFLOW}
        )
        
        if response.status_code != 200:
            print(f"✗ 提交失败: {response.status_code}")
            print(response.text[:200])
            return False
        
        result = response.json()
        prompt_id = result.get('prompt_id')
        
        if not prompt_id:
            print(f"✗ 未返回 prompt_id: {result}")
            return False
        
        print(f"✓ 已提交: {prompt_id}")
        
    except Exception as e:
        print(f"✗ 提交出错: {e}")
        print("  请确保 ComfyUI 已启动")
        return False
    
    # 2. 等待执行完成
    print("\n等待执行完成...")
    for i in range(30):
        time.sleep(0.5)
        try:
            response = requests.get(f"{BASE_URL}/history/{prompt_id}", timeout=5)
            history = response.json()
            
            if prompt_id in history:
                print(f"✓ 执行完成")
                break
        except:
            pass
        if i % 10 == 0 and i > 0:
            print(f"  等待中... {i*0.5}s", end="\r")
    else:
        print(f"\n⚠  超时，但可能已经清空")
    
    # 3. 检查队列和状态
    print("\n检查状态...")
    try:
        response = requests.get(f"{BASE_URL}/queue")
        queue = response.json()
        running = len(queue.get('queue_running', []))
        pending = len(queue.get('queue_pending', []))
        print(f"  运行中: {running}")
        print(f"  等待中: {pending}")
        
        response = requests.get(f"{BASE_URL}/system_stats")
        stats = response.json()
        for device in stats.get('devices', []):
            vram_free = device.get('vram_free', 0) / 1024**3
            vram_total = device.get('vram_total', 0) / 1024**3
            print(f"  GPU {device.get('index', 0)}: {vram_free:.1f}GB / {vram_total:.1f}GB free")
        
        print("\n" + "=" * 60)
        print("✓ GPU 显存清理完成!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"  ✗ 检查失败: {e}")
        return False

if __name__ == "__main__":
    success = clear_gpu_cache()
    exit(0 if success else 1)
