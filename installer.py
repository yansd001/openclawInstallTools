"""OpenClaw 安装与配置核心逻辑模块"""

import json
import os
import subprocess
import shutil
from datetime import datetime, timezone
from pathlib import Path

# ── 常量定义 ──

BASE_URL = "https://yansd666.com"
WEIXIN_PLUGIN_ALLOW = "openclaw-weixin"

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


def _normalize_base_url(base_url: str) -> str:
    """规范化 Base URL，去掉末尾斜杠"""
    value = (base_url or BASE_URL).strip()
    if not value:
        value = BASE_URL
    return value.rstrip("/")


def _ensure_dict(parent: dict, key: str) -> dict:
    """确保 parent[key] 为 dict，不存在或类型不对时自动创建"""
    node = parent.get(key)
    if isinstance(node, dict):
        return node
    parent[key] = {}
    return parent[key]


def _read_json_object(path: Path) -> dict:
    """读取 JSON 对象，失败时返回空对象"""
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _extract_base_url_from_providers(providers: dict) -> str:
    """从 providers 中提取基础 URL（去除 provider 后缀）"""
    if not isinstance(providers, dict):
        return BASE_URL

    # 优先使用 Claude（无后缀），值最直接
    claude = providers.get("api-proxy-claude")
    if isinstance(claude, dict):
        raw = claude.get("baseUrl")
        if isinstance(raw, str) and raw.strip():
            return _normalize_base_url(raw)

    for pkey, pinfo in PROVIDERS.items():
        pdata = providers.get(pkey)
        if not isinstance(pdata, dict):
            continue
        raw = pdata.get("baseUrl")
        if not isinstance(raw, str) or not raw.strip():
            continue

        base_url = raw.strip()
        suffix = pinfo["baseUrl_suffix"]
        if suffix and base_url.endswith(suffix):
            return _normalize_base_url(base_url[:-len(suffix)])
        if not suffix:
            return _normalize_base_url(base_url)

    return BASE_URL


def check_git_installed() -> tuple[bool, str]:
    """检查 Git 是否已安装，返回 (是否安装, 版本号或错误信息)"""
    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, "git 命令执行失败"
    except FileNotFoundError:
        return False, "未找到 Git，请先安装 Git"
    except Exception as e:
        return False, str(e)


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


def _find_uv_path() -> str | None:
    """查找 uv 可执行文件路径（含常见安装位置）"""
    # 先试 PATH 中的 uv
    found = shutil.which("uv")
    if found:
        return found
    # 检查 Windows 常见安装位置
    home = os.environ.get("USERPROFILE", "")
    candidates = [
        os.path.join(home, ".local", "bin", "uv.exe"),
        os.path.join(home, ".cargo", "bin", "uv.exe"),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


def check_uv_installed() -> tuple[bool, str]:
    """检查 uv 是否已安装"""
    uv_path = _find_uv_path()
    if not uv_path:
        return False, "未安装"
    try:
        result = subprocess.run(
            [uv_path, "--version"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, "uv 命令执行失败"
    except Exception as e:
        return False, str(e)


def install_uv(callback=None):
    """通过 PowerShell 安装 uv"""
    try:
        process = subprocess.Popen(
            ["powershell", "-ExecutionPolicy", "ByPass", "-c",
             "irm https://astral.sh/uv/install.ps1 | iex"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, creationflags=subprocess.CREATE_NO_WINDOW,
        )
        for line in iter(process.stdout.readline, ""):
            stripped = line.strip()
            if stripped and callback:
                callback(stripped)
        process.wait()
        if process.returncode == 0:
            return True, "uv 安装成功"
        return False, f"安装失败 (exit code {process.returncode})"
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


def generate_openclaw_config(models: list[dict], primary_model: str, workspace: str = "", base_url: str = BASE_URL) -> dict:
    """生成 openclaw.json 配置内容"""
    if not workspace:
        workspace = DEFAULT_WORKSPACE
    normalized_base_url = _normalize_base_url(base_url)
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
                "baseUrl": f"{normalized_base_url}{suffix}" if suffix else normalized_base_url,
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
            "lastTouchedAt": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
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


def save_openclaw_config(
    models: list[dict],
    primary_model: str,
    workspace: str = "",
    base_url: str = BASE_URL,
) -> tuple[bool, str]:
    """保存 openclaw.json 配置文件"""
    try:
        config_dir = get_openclaw_dir()
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / "openclaw.json"
        config = _read_json_object(config_path)
        managed = generate_openclaw_config(models, primary_model, workspace, base_url)

        # meta
        meta = _ensure_dict(config, "meta")
        meta["lastTouchedVersion"] = managed["meta"]["lastTouchedVersion"]
        meta["lastTouchedAt"] = managed["meta"]["lastTouchedAt"]

        # auth.profiles：只更新本工具管理的 profile，保留用户新增 profile
        auth = _ensure_dict(config, "auth")
        auth_profiles = _ensure_dict(auth, "profiles")
        for profile_key, profile_value in managed["auth"]["profiles"].items():
            auth_profiles[profile_key] = profile_value

        # models.providers：只覆盖本工具管理的 provider，其他 provider 不动
        models_node = _ensure_dict(config, "models")
        models_node["mode"] = managed["models"]["mode"]
        providers_node = _ensure_dict(models_node, "providers")
        managed_providers = managed["models"]["providers"]
        for provider_key, provider_config in managed_providers.items():
            existing_provider = providers_node.get(provider_key)
            if isinstance(existing_provider, dict):
                existing_provider["baseUrl"] = provider_config["baseUrl"]
                existing_provider["api"] = provider_config["api"]
                existing_provider["models"] = provider_config["models"]
            else:
                providers_node[provider_key] = provider_config

        # 对本工具管理的 provider，若当前模型列表不再包含则移除
        for provider_key in PROVIDERS:
            if provider_key not in managed_providers:
                providers_node.pop(provider_key, None)

        # agents.defaults：只更新约定路径，保留其他节点
        agents = _ensure_dict(config, "agents")
        defaults = _ensure_dict(agents, "defaults")
        model_node = _ensure_dict(defaults, "model")
        model_node["primary"] = managed["agents"]["defaults"]["model"]["primary"]

        aliases = _ensure_dict(defaults, "models")
        managed_aliases = managed["agents"]["defaults"]["models"]

        # 仅清理本工具管理 provider 的 alias，保留用户新增 provider 的 alias
        provider_prefixes = tuple(f"{pkey}/" for pkey in PROVIDERS)
        for alias_key in list(aliases.keys()):
            if isinstance(alias_key, str) and alias_key.startswith(provider_prefixes):
                aliases.pop(alias_key, None)
        for alias_key, alias_value in managed_aliases.items():
            aliases[alias_key] = alias_value

        defaults["workspace"] = managed["agents"]["defaults"]["workspace"]
        compaction = defaults.get("compaction")
        if not isinstance(compaction, dict):
            defaults["compaction"] = managed["agents"]["defaults"]["compaction"]
        elif "mode" not in compaction:
            compaction["mode"] = managed["agents"]["defaults"]["compaction"]["mode"]

        # commands / gateway：仅补默认值，不覆盖用户自定义
        commands = _ensure_dict(config, "commands")
        for key, value in managed["commands"].items():
            commands.setdefault(key, value)

        gateway = _ensure_dict(config, "gateway")
        for key, value in managed["gateway"].items():
            gateway.setdefault(key, value)

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
        config = _read_json_object(auth_path)
        managed = generate_auth_profiles(gpt_key, claude_key, google_key, other_key)

        # version：保持兼容，缺失时补默认
        config.setdefault("version", managed["version"])

        # profiles：只更新本工具管理的 4 个 profile，保留用户新增 profile
        profiles = _ensure_dict(config, "profiles")
        for profile_key, profile_value in managed["profiles"].items():
            profiles[profile_key] = profile_value

        # lastGood：只更新本工具管理 provider，保留用户新增 provider
        last_good = _ensure_dict(config, "lastGood")
        for provider_key, profile_name in managed["lastGood"].items():
            last_good[provider_key] = profile_name

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
    config_path = get_openclaw_dir() / "openclaw.json"
    if not config_path.exists():
        return BASE_URL
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        providers = data.get("models", {}).get("providers", {})
        return _extract_base_url_from_providers(providers)
    except Exception:
        return BASE_URL


def ensure_plugin_allowed(plugin_name: str = WEIXIN_PLUGIN_ALLOW) -> tuple[bool, str]:
    """确保 openclaw.json 的 plugins.allow 中包含指定插件"""
    try:
        config_dir = get_openclaw_dir()
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / "openclaw.json"
        config = _read_json_object(config_path)

        plugins = _ensure_dict(config, "plugins")
        allow = plugins.get("allow")
        if not isinstance(allow, list):
            allow = []
            plugins["allow"] = allow

        if plugin_name in allow:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True, f"plugins.allow 已包含 {plugin_name}"

        allow.append(plugin_name)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True, f"已将 {plugin_name} 添加到 plugins.allow"
    except Exception as e:
        return False, str(e)


def install_weixin_plugin(callback=None) -> tuple[bool, str]:
    """安装微信插件并执行登录绑定，最后写入 plugins.allow"""
    claw_ok, claw_msg = check_openclaw_installed()
    if not claw_ok:
        return False, f"OpenClaw 未安装或不可用: {claw_msg}"

    # 第一步：安装插件
    step1_cmd = "openclaw plugins install @tencent-weixin/openclaw-weixin"
    if callback:
        callback(f"[1/3] 正在安装微信插件: {step1_cmd}")
    try:
        process = subprocess.Popen(
            step1_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        output_lines = []
        for line in iter(process.stdout.readline, ""):
            line = line.rstrip()
            output_lines.append(line)
            if line and callback:
                callback(line)
        process.wait()
        if process.returncode != 0:
            install_output = "\n".join(output_lines)
            lowered = install_output.lower()
            # 已安装时允许继续后续步骤（写入 allow + 扫码登录）
            already_exists = (
                "plugin already exists" in lowered
                or ("already exists" in lowered and "openclaw-weixin" in lowered)
                or "已存在" in install_output
            )
            if already_exists:
                if callback:
                    callback("检测到微信插件已存在，跳过安装步骤，继续后续流程。")
            else:
                return False, "微信插件安装失败:\n" + install_output
    except Exception as e:
        return False, f"执行插件安装失败: {e}"

    # 第二步：先写入 plugins.allow
    if callback:
        callback("[2/3] 正在更新 openclaw.json 的 plugins.allow...")
    ok, msg = ensure_plugin_allowed(WEIXIN_PLUGIN_ALLOW)
    if not ok:
        return False, f"插件白名单更新失败: {msg}"
    if callback:
        callback(msg)

    # 第三步：直接执行扫码登录并输出日志
    step2_cmd = "openclaw channels login --channel openclaw-weixin"
    if callback:
        callback("[3/3] 正在执行微信扫码绑定，请按提示完成登录...")
    try:
        login_proc = subprocess.Popen(
            step2_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        login_output = []
        for line in iter(login_proc.stdout.readline, ""):
            line = line.rstrip()
            login_output.append(line)
            if line and callback:
                callback(line)
        login_proc.wait()
        if login_proc.returncode != 0:
            return False, "微信扫码绑定失败:\n" + "\n".join(login_output)
    except Exception as e:
        return False, f"执行微信扫码绑定失败: {e}"

    return True, "微信插件安装并绑定成功"


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


def uninstall_uv(callback=None):
    """
    卸载 uv。优先使用 uv self uninstall，失败则手动清理文件。
    callback: 接收实时日志的回调函数 callback(line: str)
    返回 (成功, 消息)
    """
    uv_path = _find_uv_path()
    if not uv_path:
        return False, "uv 未安装，无需卸载"

    # 先尝试 uv self uninstall
    try:
        if callback:
            callback(f"正在卸载 uv（{uv_path}）...")
        process = subprocess.Popen(
            [uv_path, "self", "uninstall"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, creationflags=subprocess.CREATE_NO_WINDOW,
        )
        for line in iter(process.stdout.readline, ""):
            stripped = line.strip()
            if stripped and callback:
                callback(stripped)
        process.wait()
        if process.returncode == 0:
            return True, "uv 卸载成功"
    except Exception:
        pass

    # 手动清理
    if callback:
        callback("uv self uninstall 失败，尝试手动清理...")
    home = os.environ.get("USERPROFILE", "")
    files_to_remove = [
        uv_path,
        os.path.join(os.path.dirname(uv_path), "uvx.exe"),
    ]
    dirs_to_remove = [
        os.path.join(home, ".local", "share", "uv"),
    ]
    removed_any = False
    for f in files_to_remove:
        if os.path.isfile(f):
            try:
                os.remove(f)
                if callback:
                    callback(f"已删除: {f}")
                removed_any = True
            except Exception as e:
                if callback:
                    callback(f"删除失败 {f}: {e}")
    for d in dirs_to_remove:
        if os.path.isdir(d):
            try:
                shutil.rmtree(d)
                if callback:
                    callback(f"已删除目录: {d}")
                removed_any = True
            except Exception as e:
                if callback:
                    callback(f"删除目录失败 {d}: {e}")
    if removed_any:
        return True, "uv 手动卸载完成"
    return False, "未能卸载 uv，请手动删除"


def uninstall_openclaw(callback=None):
    """
    卸载 OpenClaw：npm 全局卸载 + 删除 ~/.openclaw 配置目录。
    callback: 接收实时日志的回调函数 callback(line: str)
    返回 (成功, 消息)
    """
    errors = []

    # 1) npm 全局卸载
    if callback:
        callback("正在通过 npm 卸载 openclaw...")
    try:
        process = subprocess.Popen(
            ["npm", "uninstall", "-g", "openclaw"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, shell=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        for line in iter(process.stdout.readline, ""):
            line = line.rstrip()
            if line and callback:
                callback(line)
        process.wait()
        if process.returncode == 0:
            if callback:
                callback("npm 全局卸载 openclaw 完成")
        else:
            msg = f"npm uninstall 返回非零退出码: {process.returncode}"
            errors.append(msg)
            if callback:
                callback(msg)
    except FileNotFoundError:
        msg = "未找到 npm，跳过 npm 卸载步骤"
        errors.append(msg)
        if callback:
            callback(msg)
    except Exception as e:
        msg = f"npm 卸载失败: {e}"
        errors.append(msg)
        if callback:
            callback(msg)

    # 2) 删除 ~/.openclaw 配置目录
    openclaw_dir = get_openclaw_dir()
    if openclaw_dir.exists():
        if callback:
            callback(f"正在删除配置目录: {openclaw_dir}")
        try:
            shutil.rmtree(openclaw_dir)
            if callback:
                callback(f"已删除配置目录: {openclaw_dir}")
        except Exception as e:
            msg = f"删除配置目录失败: {e}"
            errors.append(msg)
            if callback:
                callback(msg)
    else:
        if callback:
            callback(f"配置目录不存在，无需删除: {openclaw_dir}")

    if errors:
        return False, "卸载过程中出现错误:\n" + "\n".join(errors)
    return True, "OpenClaw 卸载完成（已移除 npm 包及配置目录）"


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
