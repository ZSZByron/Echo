#!/usr/bin/env python3
"""
千文万相 (Qwen-Image) API 快速测试
只测一个模型，快速验证 API 是否可用
"""

import json
import time
import datetime
from pathlib import Path

import requests

API_KEY = "sk-6551656db8e54b8a87b2e9727019f2a5"
SYNC_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
ASYNC_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"
TASK_URL = "https://dashscope.aliyuncs.com/api/v1/tasks"
OUTPUT_DIR = Path(__file__).parent / "output"


def download_image(url, save_path):
    try:
        resp = requests.get(url, timeout=60)
        if resp.status_code == 200:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            save_path.write_bytes(resp.content)
            size_kb = len(resp.content) / 1024
            print(f"  [OK] 已保存: {save_path} ({size_kb:.1f} KB)")
            return True
        print(f"  [FAIL] 下载失败 HTTP {resp.status_code}")
    except Exception as e:
        print(f"  [FAIL] 下载异常: {e}")
    return False


def test_sync(model, prompt, name, size="1024*1024"):
    """同步调用 multimodal-generation 接口"""
    print(f"\n{'='*60}")
    print(f"  同步测试: {model}")
    print(f"{'='*60}")
    print(f"  Prompt: {prompt[:80]}")
    print(f"  Size: {size}")

    payload = {
        "model": model,
        "input": {
            "messages": [
                {"role": "user", "content": [{"text": prompt}]}
            ]
        },
        "parameters": {
            "prompt_extend": True,
            "watermark": False,
            "size": size,
            "n": 1,
        },
    }

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    start = time.time()
    print("  发送请求中...")
    try:
        resp = requests.post(SYNC_URL, headers=headers, json=payload, timeout=180)
        elapsed = time.time() - start
        print(f"  HTTP {resp.status_code} | {elapsed:.1f}s")

        data = resp.json()

        if resp.status_code == 200:
            choices = data.get("output", {}).get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content", [])
                for item in content:
                    if "image" in item:
                        image_url = item["image"]
                        print(f"  图像URL: {image_url[:120]}...")
                        ts = datetime.datetime.now().strftime("%H%M%S")
                        save_path = OUTPUT_DIR / f"{model}_{name}_{ts}.png"
                        download_image(image_url, save_path)
                        return True
            # 没找到 image 字段
            print(f"  [WARN] 响应无图像字段，完整响应:")
            print(f"  {json.dumps(data, ensure_ascii=False, indent=2)[:800]}")
            return False
        else:
            print(f"  [ERROR] {json.dumps(data, ensure_ascii=False)[:500]}")
            return False
    except requests.exceptions.Timeout:
        print(f"  [ERROR] 超时 (180s)")
        return False
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False


def test_async(model, prompt, name, size="1024*1024"):
    """异步调用 image-synthesis 接口"""
    print(f"\n{'='*60}")
    print(f"  异步测试: {model}")
    print(f"{'='*60}")
    print(f"  Prompt: {prompt[:80]}")

    payload = {
        "model": model,
        "input": {"prompt": prompt},
        "parameters": {"size": size, "n": 1, "watermark": False},
    }

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }

    # Step 1: 提交
    print("  [1/2] 提交任务...")
    try:
        resp = requests.post(ASYNC_URL, headers=headers, json=payload, timeout=30)
        data = resp.json()
        if resp.status_code != 200:
            print(f"  [ERROR] 提交失败: {json.dumps(data, ensure_ascii=False)[:400]}")
            return False

        task_id = data.get("output", {}).get("task_id")
        if not task_id:
            print(f"  [ERROR] 无 task_id: {json.dumps(data, ensure_ascii=False)[:400]}")
            return False
        print(f"  Task ID: {task_id}")
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False

    # Step 2: 轮询
    start = time.time()
    poll_headers = {"Authorization": f"Bearer {API_KEY}"}
    for i in range(40):
        time.sleep(5)
        elapsed = time.time() - start
        print(f"  [2/2] 轮询 ({i+1}/40) {elapsed:.0f}s...", end="", flush=True)
        try:
            pr = requests.get(f"{TASK_URL}/{task_id}", headers=poll_headers, timeout=30)
            pd = pr.json()
            status = pd.get("output", {}).get("task_status", "")
            print(f" 状态={status}")

            if status == "SUCCEEDED":
                results = pd.get("output", {}).get("results", [])
                for r in results:
                    url = r.get("url")
                    if url:
                        ts = datetime.datetime.now().strftime("%H%M%S")
                        save_path = OUTPUT_DIR / f"{model}_{name}_{ts}.png"
                        download_image(url, save_path)
                        return True
                print(f"  [WARN] 成功但无URL: {json.dumps(pd, ensure_ascii=False)[:400]}")
                return True
            elif status == "FAILED":
                print(f"  [ERROR] 任务失败: {json.dumps(pd, ensure_ascii=False)[:400]}")
                return False
        except Exception as e:
            print(f" 异常={e}")

    print(f"  [ERROR] 轮询超时")
    return False


def main():
    print("=" * 60)
    print("  千文万相 API 测试")
    print(f"  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Key: {API_KEY[:10]}...{API_KEY[-4:]}")
    print("=" * 60)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results = []

    # 测试列表： (模型, 调用方式, prompt, size)
    tests = [
        # 同步模型
        ("qwen-image-2.0-pro", "sync", "赛博朋克城市夜景，霓虹灯，雨后湿润街道反射光影", "1024*1024"),
        ("wan2.6-t2i",         "sync", "一间有着精致窗户的花店，漂亮的木质门，摆放着花朵", "1280*1280"),
        # 异步模型（兼容老接口）
        ("qwen-image-plus",    "async", "治愈系手绘海报，三只小狗在绿草地上玩球", "1024*1024"),
    ]

    for model, mode, prompt, size in tests:
        name = prompt[:15].replace("，", "_").replace(" ", "_")
        if mode == "sync":
            ok = test_sync(model, prompt, name, size)
        else:
            ok = test_async(model, prompt, name, size)
        results.append((model, mode, ok))

    # 汇总
    print(f"\n{'='*60}")
    print("  汇总")
    print(f"{'='*60}")
    for model, mode, ok in results:
        print(f"  {'[PASS]' if ok else '[FAIL]'} {model} ({mode})")
    print(f"\n  图片保存在: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
