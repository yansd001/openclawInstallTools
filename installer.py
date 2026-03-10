"""OpenClaw 安装与配置核心逻辑模块"""

import json
import os
import subprocess
import shutil
from pathlib import Path

# ── 常量定义 ──

BASE_URL = "https://yansd666.com"

PROVIDERS = {
    "api-proxy-gpt": {"label": "GPT", "baseUrl_suffix": "/v1", "api": "openai-completions"},
    "api-proxy-claude": {"label": "Claude", "baseUrl_suffix": "", "api": "anthropic-messages"},
    "api-proxy-google": {"label": "Google", "baseUrl_suffix": "/v1beta", "api": "google-generative-ai"},
    "api-proxy-other": {"label": "Other", "baseUrl_suffix": "/v1", "api": "openai-completions"},
}

# provider key 到 auth key 名称的映射
PROVIDER_AUTH_KEYS = {
    "api-proxy-gpt": "gpt",
    "api-proxy-claude": "claude",
    "api-proxy-google": "google",
    "api-proxy-other": "other",
}

DEFAULT_MODELS = [
    {"provider": "api-proxy-gpt", "id": "gpt-5.4", "name": "GPT-5.4", "contextWindow": 128000, "maxTokens": 8192},
    {"provider": "api-proxy-claude", "id": "claude-sonnet-4-6", "name": "Claude Sonnet 4.6", "contextWindow": 200000, "maxTokens": 8192},
    {"provider": "api-proxy-google", "id": "gemini-3.1-pro-preview", "name": "Gemini 3.1 Pro", "contextWindow": 2000000, "maxTokens": 8192},
    {"provider": "api-proxy-google", "id": "gemini-3.1-flash-preview", "name": "Gemini 3.1 Flash", "contextWindow": 2000000, "maxTokens": 8192},
    {"provider": "api-proxy-other", "id": "deepseek-v3.2", "name": "DeepSeek V3.2", "contextWindow": 65536, "maxTokens": 8192},
]

DEFAULT_PRIMARY_MODEL = "api-proxy-claude/claude-sonnet-4-6"

DEFAULT_WORKSPACE = str(Path(os.environ["USERPROFILE"]) / ".openclaw" / "workspace")


def get_openclaw_dir() -> Path:
    """获取 OpenClaw 配置目录"""
    return Path(os.environ["USERPROFILE"]) / ".openclaw"


def get_auth_profiles_dir() -> Path:
    """获取 auth-profiles.json 所在目录"""
    return get_openclaw_dir() / "agents" / "main" / "agent"


def check_node_installed() -> tuple[bool, str]:
    """检查 Node.js 是否已安装，返回 (是否安装, 版本号或错误信息)"""
    try:
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, "node 命令执行失败"
    except FileNotFoundError:
        return False, "未找到 Node.js，请先安装 Node.js"
    except Exception as e:
        return False, str(e)


def check_npm_installed() -> tuple[bool, str]:
    """检查 npm 是否已安装"""
    try:
        result = subprocess.run(
            ["npm", "--version"],
            capture_output=True, text=True, timeout=10,
            shell=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, "npm 命令执行失败"
    except FileNotFoundError:
        return False, "未找到 npm"
    except Exception as e:
        return False, str(e)


def check_openclaw_installed() -> tuple[bool, str]:
    """检查 OpenClaw 是否已安装"""
    try:
        result = subprocess.run(
            ["openclaw", "--version"],
            capture_output=True, text=True, timeout=10,
            shell=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, "openclaw 命令执行失败"
    except FileNotFoundError:
        return False, "未安装"
    except Exception as e:
        return False, str(e)


def install_openclaw(callback=None):
    """
    安装 OpenClaw，通过 npm i -g openclaw
    callback: 接收实时日志的回调函数 callback(line: str)
    返回 (成功, 消息)
    """
    try:
        process = subprocess.Popen(
            ["npm", "i", "-g", "openclaw"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            shell=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        output_lines = []
        for line in iter(process.stdout.readline, ""):
            line = line.rstrip()
            output_lines.append(line)
            if callback:
                callback(line)
        process.wait()
        if process.returncode == 0:
            return True, "OpenClaw 安装成功"
        return False, "\n".join(output_lines)
    except FileNotFoundError:
        return False, "未找到 npm，请先安装 Node.js"
    except Exception as e:
        return False, str(e)


def generate_openclaw_config(models: list[dict], primary_model: str, workspace: str = "") -> dict:
    """生成 openclaw.json 配置内容"""
    if not workspace:
        workspace = DEFAULT_WORKSPACE
    # 按 provider 分组模型
    provider_models = {}
    for m in models:
        p = m["provider"]
        if p not in provider_models:
            provider_models[p] = []
        provider_models[p].append({
            "id": m["id"],
            "name": m["name"],
            "contextWindow": m.get("contextWindow", 128000),
            "maxTokens": m.get("maxTokens", 8192),
        })

    # 构建 providers 配置
    providers_config = {}
    for pkey, pinfo in PROVIDERS.items():
        if pkey in provider_models:
            suffix = pinfo["baseUrl_suffix"]
            providers_config[pkey] = {
                "baseUrl": f"{BASE_URL}{suffix}" if suffix else BASE_URL,
                "api": pinfo["api"],
                "models": provider_models[pkey],
            }

    # 构建 auth profiles
    auth_profiles = {}
    for pkey in provider_models:
        auth_profiles[f"{pkey}:default"] = {
            "provider": pkey,
            "mode": "api_key",
        }

    # 构建 agents models (alias)
    agent_models = {}
    for m in models:
        full_id = f"{m['provider']}/{m['id']}"
        agent_models[full_id] = {"alias": m["name"]}

    return {
        "meta": {
            "lastTouchedVersion": "2026.3.2",
            "lastTouchedAt": "2026-03-04T11:23:47.011Z"
        },
        "auth": {
            "profiles": auth_profiles
        },
        "models": {
            "mode": "merge",
            "providers": providers_config
        },
        "agents": {
            "defaults": {
                "model": {
                    "primary": primary_model
                },
                "models": agent_models,
                "workspace": workspace,
                "compaction": {
                    "mode": "safeguard"
                }
            }
        },
        "commands": {
            "native": "auto",
            "nativeSkills": "auto",
            "restart": True,
            "ownerDisplay": "raw"
        },
        "gateway": {
            "mode": "local"
        }
    }


def generate_auth_profiles(gpt_key: str, claude_key: str, google_key: str, other_key: str) -> dict:
    """生成 auth-profiles.json 配置内容"""
    return {
        "version": 1,
        "profiles": {
            "api-proxy-gpt:default": {
                "type": "api_key",
                "provider": "api-proxy-gpt",
                "key": gpt_key
            },
            "api-proxy-claude:default": {
                "type": "api_key",
                "provider": "api-proxy-claude",
                "key": claude_key
            },
            "api-proxy-google:default": {
                "type": "api_key",
                "provider": "api-proxy-google",
                "key": google_key
            },
            "api-proxy-other:default": {
                "type": "api_key",
                "provider": "api-proxy-other",
                "key": other_key
            }
        },
        "lastGood": {
            "api-proxy-gpt": "api-proxy-gpt:default",
            "api-proxy-claude": "api-proxy-claude:default",
            "api-proxy-google": "api-proxy-google:default",
            "api-proxy-other": "api-proxy-other:default"
        }
    }


def save_openclaw_config(models: list[dict], primary_model: str, workspace: str = "") -> tuple[bool, str]:
    """保存 openclaw.json 配置文件"""
    try:
        config_dir = get_openclaw_dir()
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / "openclaw.json"
        config = generate_openclaw_config(models, primary_model, workspace)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True, str(config_path)
    except Exception as e:
        return False, str(e)


def save_auth_profiles(gpt_key: str, claude_key: str, google_key: str, other_key: str) -> tuple[bool, str]:
    """保存 auth-profiles.json 配置文件"""
    try:
        auth_dir = get_auth_profiles_dir()
        auth_dir.mkdir(parents=True, exist_ok=True)
        auth_path = auth_dir / "auth-profiles.json"
        config = generate_auth_profiles(gpt_key, claude_key, google_key, other_key)
        with open(auth_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True, str(auth_path)
    except Exception as e:
        return False, str(e)


def check_config_exists() -> tuple[bool, bool]:
    """检查配置文件是否存在，返回 (openclaw.json存在, auth-profiles.json存在)"""
    config_exists = (get_openclaw_dir() / "openclaw.json").exists()
    auth_exists = (get_auth_profiles_dir() / "auth-profiles.json").exists()
    return config_exists, auth_exists


def read_existing_auth_keys() -> tuple[str, str, str, str]:
    """读取已有的 API Key，返回 (gpt_key, claude_key, google_key, other_key)"""
    auth_path = get_auth_profiles_dir() / "auth-profiles.json"
    if not auth_path.exists():
        return "", "", "", ""
    try:
        with open(auth_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        profiles = data.get("profiles", {})
        gpt_key = profiles.get("api-proxy-gpt:default", {}).get("key", "")
        claude_key = profiles.get("api-proxy-claude:default", {}).get("key", "")
        google_key = profiles.get("api-proxy-google:default", {}).get("key", "")
        other_key = profiles.get("api-proxy-other:default", {}).get("key", "")
        return gpt_key, claude_key, google_key, other_key
    except Exception:
        return "", "", "", ""


def read_existing_base_url() -> str:
    """读取已有配置中的 baseUrl"""
    return BASE_URL


def read_existing_models() -> list[dict]:
    """从已有 openclaw.json 中读取模型列表，若无则返回默认列表"""
    config_path = get_openclaw_dir() / "openclaw.json"
    if not config_path.exists():
        return [m.copy() for m in DEFAULT_MODELS]
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        providers = data.get("models", {}).get("providers", {})
        models = []
        for pkey, pdata in providers.items():
            if pkey not in PROVIDERS:
                continue
            for m in pdata.get("models", []):
                models.append({
                    "provider": pkey,
                    "id": m["id"],
                    "name": m.get("name", m["id"]),
                    "contextWindow": m.get("contextWindow", 128000),
                    "maxTokens": m.get("maxTokens", 8192),
                })
        return models if models else [m.copy() for m in DEFAULT_MODELS]
    except Exception:
        return [m.copy() for m in DEFAULT_MODELS]


def read_existing_primary_model() -> str:
    """从已有 openclaw.json 中读取默认模型"""
    config_path = get_openclaw_dir() / "openclaw.json"
    if not config_path.exists():
        return DEFAULT_PRIMARY_MODEL
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("agents", {}).get("defaults", {}).get("model", {}).get("primary", DEFAULT_PRIMARY_MODEL)
    except Exception:
        return DEFAULT_PRIMARY_MODEL


def read_existing_workspace() -> str:
    """从已有 openclaw.json 中读取 workspace 路径"""
    config_path = get_openclaw_dir() / "openclaw.json"
    if not config_path.exists():
        return DEFAULT_WORKSPACE
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        ws = data.get("agents", {}).get("defaults", {}).get("workspace", DEFAULT_WORKSPACE)
        # 展开环境变量（如 %USERPROFILE%）
        return os.path.expandvars(ws)
    except Exception:
        return DEFAULT_WORKSPACE


def launch_gateway():
    """启动 openclaw gateway，返回进程对象"""
    return subprocess.Popen(
        'cmd /k "openclaw gateway"',
        shell=True,
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )


def launch_dashboard():
    """启动 openclaw dashboard，返回进程对象"""
    return subprocess.Popen(
        'cmd /k "openclaw dashboard"',
        shell=True,
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )
