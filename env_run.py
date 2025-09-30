#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
env_run.py

用法:
  python env_run.py <config.json> <script.py> [--event mock_event.json] [其他参数...]

功能:
  - 读取第一个参数指定的 JSON 文件（键 -> 环境变量）
  - 在当前进程环境的基础上注入这些变量（不覆盖已有 ENV 除非 JSON 中有）
  - 使用 subprocess 在子进程中以相同 Python 解释器运行 <script.py>，并传递后续所有参数
  - 自动输出注入了哪些环境变量（值会遮掩中间部分以避免泄密），便于调试
"""
import os
import sys
import json
import subprocess
from typing import Dict

MASK_LEN = 6

def mask_secret(v: str) -> str:
    if not v:
        return ""
    s = str(v)
    if len(s) <= MASK_LEN*2:
        return s[:MASK_LEN] + "..." + s[-MASK_LEN:]
    return s[:MASK_LEN] + "..." + s[-MASK_LEN:]

def load_config(path: str) -> Dict[str,str]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise SystemExit("config file must contain a JSON object of key:value pairs")
    # only keep string values
    out = {}
    for k, v in data.items():
        if isinstance(v, (str, int, float, bool)):
            out[k] = str(v)
    return out

def main():
    if len(sys.argv) < 3:
        print("Usage: python env_run.py <config.json> <script.py> [args...]", file=sys.stderr)
        sys.exit(2)

    cfg_path = sys.argv[1]
    script_path = sys.argv[2]
    script_args = sys.argv[3:]

    if not os.path.exists(cfg_path):
        print(f"Config file not found: {cfg_path}", file=sys.stderr)
        sys.exit(3)
    if not os.path.exists(script_path):
        print(f"Script file not found: {script_path}", file=sys.stderr)
        sys.exit(4)

    cfg = load_config(cfg_path)

    # Prepare environment for child process: copy current env then update with cfg
    child_env = os.environ.copy()
    for k, v in cfg.items():
        child_env[k] = v

    # Print summary of injected vars (mask values)
    print("Injected environment variables from", cfg_path)
    for k in sorted(cfg.keys()):
        print(f"  {k} = {mask_secret(cfg[k])}")

    # Build command to run using same Python interpreter
    py = sys.executable or "python"
    cmd = [py, script_path] + script_args

    print("\nRunning:", " ".join(cmd))
    print("---- stdout/stderr from target script ----\n")

    # Run and forward exit code
    try:
        res = subprocess.run(cmd, env=child_env)
        sys.exit(res.returncode)
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print("Failed to run target script:", e, file=sys.stderr)
        sys.exit(5)

if __name__ == "__main__":
    main()
