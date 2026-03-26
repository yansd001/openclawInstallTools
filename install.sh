#!/usr/bin/env bash
# ============================================================================
# OpenClaw Linux 安装配置脚本
# 功能：环境检测、安装 OpenClaw / uv、配置 API 密钥与模型、启动服务
# ============================================================================

set -euo pipefail

# ── 颜色定义 ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m' # No Color

# ── 常量 ──
DEFAULT_BASE_URL="https://yansd666.com"
OPENCLAW_DIR="$HOME/.openclaw"
AUTH_PROFILES_DIR="$OPENCLAW_DIR/agents/main/agent"
CONFIG_FILE="$OPENCLAW_DIR/openclaw.json"
AUTH_FILE="$AUTH_PROFILES_DIR/auth-profiles.json"
DEFAULT_WORKSPACE="$OPENCLAW_DIR/workspace"

# ── Provider 定义 ──
# provider_key|label|baseUrl_suffix|api
PROVIDERS=(
    "api-proxy-gpt|GPT|/v1|openai-completions"
    "api-proxy-claude|Claude||anthropic-messages"
    "api-proxy-google|Google|/v1beta|google-generative-ai"
    "api-proxy-other|Other|/v1|openai-completions"
)

# ── 默认模型 ──
# provider|id|name|contextWindow|maxTokens
DEFAULT_MODELS=(
    "api-proxy-gpt|gpt-5.4|GPT-5.4|128000|8192"
    "api-proxy-claude|claude-sonnet-4-6|Claude Sonnet 4.6|200000|8192"
    "api-proxy-google|gemini-3.1-pro-preview|Gemini 3.1 Pro|2000000|8192"
    "api-proxy-google|gemini-3.1-flash-preview|Gemini 3.1 Flash|2000000|8192"
    "api-proxy-other|deepseek-v3.2|DeepSeek V3.2|65536|8192"
)

DEFAULT_PRIMARY_MODEL="api-proxy-claude/claude-sonnet-4-6"

# ── 工具函数 ──

info()    { echo -e "${BLUE}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC} $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; }

header() {
    echo ""
    echo -e "${CYAN}${BOLD}══════════════════════════════════════════${NC}"
    echo -e "${CYAN}${BOLD}  $*${NC}"
    echo -e "${CYAN}${BOLD}══════════════════════════════════════════${NC}"
    echo ""
}

separator() {
    echo -e "${DIM}──────────────────────────────────────────${NC}"
}

# 检查命令是否存在
cmd_exists() {
    command -v "$1" &>/dev/null
}

# ── 环境检测 ──

check_environment() {
    header "🔍 环境检测"

    # Node.js
    if cmd_exists node; then
        success "Node.js: $(node --version)"
    else
        error "Node.js: 未安装"
        warn "请先安装 Node.js 22+: https://nodejs.org/"
    fi

    # npm
    if cmd_exists npm; then
        success "npm: v$(npm --version)"
    else
        error "npm: 未安装"
    fi

    # Git
    if cmd_exists git; then
        success "Git: $(git --version)"
    else
        error "Git: 未安装"
    fi

    # uv
    if cmd_exists uv; then
        success "uv: $(uv --version)"
    elif [ -f "$HOME/.local/bin/uv" ]; then
        success "uv: $($HOME/.local/bin/uv --version) (位于 ~/.local/bin/)"
    elif [ -f "$HOME/.cargo/bin/uv" ]; then
        success "uv: $($HOME/.cargo/bin/uv --version) (位于 ~/.cargo/bin/)"
    else
        warn "uv: 未安装（Skills 安装所需）"
    fi

    # OpenClaw
    if cmd_exists openclaw; then
        success "OpenClaw: $(openclaw --version 2>/dev/null || echo '已安装')"
    else
        warn "OpenClaw: 未安装"
    fi

    # 配置文件
    if [ -f "$CONFIG_FILE" ]; then
        success "配置文件: $CONFIG_FILE"
    else
        warn "配置文件: 不存在"
    fi

    # 密钥文件
    if [ -f "$AUTH_FILE" ]; then
        success "密钥文件: $AUTH_FILE"
    else
        warn "密钥文件: 不存在"
    fi

    echo ""
}

# ── 安装 OpenClaw ──

install_openclaw() {
    header "📦 安装 OpenClaw"

    if ! cmd_exists npm; then
        error "npm 未安装，请先安装 Node.js"
        return 1
    fi

    info "正在通过 npm 全局安装 openclaw ..."
    if npm i -g openclaw; then
        success "OpenClaw 安装成功"
    else
        error "OpenClaw 安装失败"
        return 1
    fi
}

# ── 安装 uv ──

install_uv() {
    header "📦 安装 uv"

    if cmd_exists uv; then
        success "uv 已安装: $(uv --version)"
        return 0
    fi

    info "正在安装 uv ..."
    if curl -LsSf https://astral.sh/uv/install.sh | sh; then
        success "uv 安装成功"
        info "请重新加载 shell 或执行: source ~/.bashrc (或 ~/.zshrc)"
    else
        error "uv 安装失败"
        return 1
    fi
}

# ── 卸载 OpenClaw ──

uninstall_openclaw() {
    header "🗑️  卸载 OpenClaw"

    echo -e "${RED}${BOLD}警告：卸载将删除 OpenClaw 及 $OPENCLAW_DIR 下所有配置！${NC}"
    read -rp "确认卸载？(y/N): " confirm
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
        info "已取消"
        return 0
    fi

    # npm 卸载
    if cmd_exists npm; then
        info "正在通过 npm 卸载 openclaw ..."
        npm uninstall -g openclaw || warn "npm 卸载返回非零退出码"
    else
        warn "npm 未安装，跳过 npm 卸载步骤"
    fi

    # 删除配置目录
    if [ -d "$OPENCLAW_DIR" ]; then
        info "正在删除配置目录: $OPENCLAW_DIR"
        rm -rf "$OPENCLAW_DIR"
        success "配置目录已删除"
    else
        info "配置目录不存在，无需删除"
    fi

    success "OpenClaw 卸载完成"
}

# ── 卸载 uv ──

uninstall_uv() {
    header "🗑️  卸载 uv"

    if ! cmd_exists uv && [ ! -f "$HOME/.local/bin/uv" ] && [ ! -f "$HOME/.cargo/bin/uv" ]; then
        info "uv 未安装，无需卸载"
        return 0
    fi

    info "正在卸载 uv ..."
    if cmd_exists uv; then
        uv self uninstall || warn "uv self uninstall 失败，请手动清理"
    else
        # 手动清理
        for f in "$HOME/.local/bin/uv" "$HOME/.local/bin/uvx" "$HOME/.cargo/bin/uv" "$HOME/.cargo/bin/uvx"; do
            if [ -f "$f" ]; then
                rm -f "$f" && info "已删除: $f"
            fi
        done
        if [ -d "$HOME/.local/share/uv" ]; then
            rm -rf "$HOME/.local/share/uv" && info "已删除缓存目录"
        fi
    fi

    success "uv 卸载完成"
}

# ── JSON 辅助函数（纯 bash + python 生成 JSON）──

# 使用 Python 生成配置文件（保证 JSON 格式安全可靠）
generate_and_save_config() {
    local base_url="$1"
    shift
    # 剩余参数: models (provider|id|name|ctx|maxtok) ...
    # 然后是 primary_model, workspace
    # 以及 provider keys 和对应的 api keys/base urls

    # 收集模型数据
    local models_json="["
    local first=true
    while [[ "$1" != "--" ]]; do
        IFS='|' read -r m_provider m_id m_name m_ctx m_max <<< "$1"
        if [ "$first" = true ]; then
            first=false
        else
            models_json+=","
        fi
        models_json+="{\"provider\":\"$m_provider\",\"id\":\"$m_id\",\"name\":\"$m_name\",\"contextWindow\":$m_ctx,\"maxTokens\":$m_max}"
        shift
    done
    models_json+="]"
    shift # skip --

    local primary_model="$1"
    local workspace="$2"
    shift 2

    # 收集 API keys：provider_key|base_url|api_key
    local auth_json="["
    first=true
    while [[ $# -gt 0 ]]; do
        IFS='|' read -r p_key p_base_url p_api_key <<< "$1"
        if [ "$first" = true ]; then
            first=false
        else
            auth_json+=","
        fi
        auth_json+="{\"provider\":\"$p_key\",\"baseUrl\":\"$p_base_url\",\"apiKey\":\"$p_api_key\"}"
        shift
    done
    auth_json+="]"

    # 使用 Python 生成并保存配置文件
    python3 - "$CONFIG_FILE" "$AUTH_FILE" "$primary_model" "$workspace" "$models_json" "$auth_json" << 'PYTHON_SCRIPT'
import json
import sys
import os
from datetime import datetime, timezone

config_path = sys.argv[1]
auth_path = sys.argv[2]
primary_model = sys.argv[3]
workspace = sys.argv[4]
models = json.loads(sys.argv[5])
auth_entries = json.loads(sys.argv[6])

PROVIDERS = {
    "api-proxy-gpt":    {"label": "GPT",    "baseUrl_suffix": "/v1",     "api": "openai-completions"},
    "api-proxy-claude":  {"label": "Claude", "baseUrl_suffix": "",        "api": "anthropic-messages"},
    "api-proxy-google":  {"label": "Google", "baseUrl_suffix": "/v1beta", "api": "google-generative-ai"},
    "api-proxy-other":   {"label": "Other",  "baseUrl_suffix": "/v1",     "api": "openai-completions"},
}

# 构建 auth 映射
auth_map = {}
for entry in auth_entries:
    auth_map[entry["provider"]] = {"baseUrl": entry["baseUrl"], "apiKey": entry["apiKey"]}

# 按 provider 分组模型
provider_models = {}
for m in models:
    p = m["provider"]
    if p not in provider_models:
        provider_models[p] = []
    provider_models[p].append({
        "id": m["id"],
        "name": m["name"],
        "contextWindow": m["contextWindow"],
        "maxTokens": m["maxTokens"],
    })

# 构建 providers 配置
providers_config = {}
for pkey, pinfo in PROVIDERS.items():
    if pkey in provider_models:
        # 使用该 provider 自己的 baseUrl（如果已配置），否则跳过
        if pkey in auth_map:
            base = auth_map[pkey]["baseUrl"].rstrip("/")
        else:
            continue
        suffix = pinfo["baseUrl_suffix"]
        providers_config[pkey] = {
            "baseUrl": f"{base}{suffix}" if suffix else base,
            "api": pinfo["api"],
            "models": provider_models[pkey],
        }

# 构建 auth profiles (用于 openclaw.json)
oc_auth_profiles = {}
for pkey in provider_models:
    if pkey in auth_map:
        oc_auth_profiles[f"{pkey}:default"] = {
            "provider": pkey,
            "mode": "api_key",
        }

# 构建 agents models alias
agent_models = {}
for m in models:
    full_id = f"{m['provider']}/{m['id']}"
    agent_models[full_id] = {"alias": m["name"]}

# ── 读取已有配置并合并 ──
def read_json(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def ensure_dict(parent, key):
    node = parent.get(key)
    if isinstance(node, dict):
        return node
    parent[key] = {}
    return parent[key]

# ── 生成 openclaw.json ──
config = read_json(config_path)

meta = ensure_dict(config, "meta")
meta["lastTouchedVersion"] = "2026.3.2"
meta["lastTouchedAt"] = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

auth = ensure_dict(config, "auth")
auth_profiles_node = ensure_dict(auth, "profiles")
for profile_key, profile_value in oc_auth_profiles.items():
    auth_profiles_node[profile_key] = profile_value

models_node = ensure_dict(config, "models")
models_node["mode"] = "merge"
prov_node = ensure_dict(models_node, "providers")
for provider_key, provider_config in providers_config.items():
    existing = prov_node.get(provider_key)
    if isinstance(existing, dict):
        existing["baseUrl"] = provider_config["baseUrl"]
        existing["api"] = provider_config["api"]
        existing["models"] = provider_config["models"]
    else:
        prov_node[provider_key] = provider_config

# 移除未使用的 managed provider
for provider_key in list(PROVIDERS.keys()):
    if provider_key not in providers_config:
        prov_node.pop(provider_key, None)

agents = ensure_dict(config, "agents")
defaults = ensure_dict(agents, "defaults")
model_node = ensure_dict(defaults, "model")
model_node["primary"] = primary_model

aliases = ensure_dict(defaults, "models")
provider_prefixes = tuple(f"{pkey}/" for pkey in PROVIDERS)
for alias_key in list(aliases.keys()):
    if isinstance(alias_key, str) and alias_key.startswith(provider_prefixes):
        aliases.pop(alias_key, None)
for alias_key, alias_value in agent_models.items():
    aliases[alias_key] = alias_value

defaults["workspace"] = workspace

compaction = defaults.get("compaction")
if not isinstance(compaction, dict):
    defaults["compaction"] = {"mode": "safeguard"}
elif "mode" not in compaction:
    compaction["mode"] = "safeguard"

commands = ensure_dict(config, "commands")
for key, value in {"native": "auto", "nativeSkills": "auto", "restart": True, "ownerDisplay": "raw"}.items():
    commands.setdefault(key, value)

gateway = ensure_dict(config, "gateway")
gateway.setdefault("mode", "local")

os.makedirs(os.path.dirname(config_path), exist_ok=True)
with open(config_path, "w", encoding="utf-8") as f:
    json.dump(config, f, indent=2, ensure_ascii=False)

# ── 生成 auth-profiles.json ──
auth_config = read_json(auth_path)
auth_config.setdefault("version", 1)

profiles = ensure_dict(auth_config, "profiles")
last_good = ensure_dict(auth_config, "lastGood")

for entry in auth_entries:
    pkey = entry["provider"]
    profile_name = f"{pkey}:default"
    profiles[profile_name] = {
        "type": "api_key",
        "provider": pkey,
        "key": entry["apiKey"],
    }
    last_good[pkey] = profile_name

os.makedirs(os.path.dirname(auth_path), exist_ok=True)
with open(auth_path, "w", encoding="utf-8") as f:
    json.dump(auth_config, f, indent=2, ensure_ascii=False)

print(f"CONFIG:{config_path}")
print(f"AUTH:{auth_path}")
PYTHON_SCRIPT
}

# ── 配置 API 密钥（可选择提供商）──

configure_api() {
    header "🔑 API 配置"

    echo -e "${BOLD}可用的 API Provider:${NC}"
    echo ""
    echo "  1) GPT       (api-proxy-gpt)"
    echo "  2) Claude    (api-proxy-claude)"
    echo "  3) Google    (api-proxy-google)"
    echo "  4) Other     (api-proxy-other)"
    echo ""

    read -rp "请输入要配置的 Provider 编号（多个用空格分隔，如 1 2 3，直接回车配置全部）: " selections

    if [ -z "$selections" ]; then
        selections="1 2 3 4"
    fi

    # 映射选择到 provider key
    declare -A selected_providers
    for sel in $selections; do
        case "$sel" in
            1) selected_providers["api-proxy-gpt"]="GPT" ;;
            2) selected_providers["api-proxy-claude"]="Claude" ;;
            3) selected_providers["api-proxy-google"]="Google" ;;
            4) selected_providers["api-proxy-other"]="Other" ;;
            *) warn "忽略无效选择: $sel" ;;
        esac
    done

    if [ ${#selected_providers[@]} -eq 0 ]; then
        error "未选择任何 Provider"
        return 1
    fi

    echo ""
    info "将配置以下 Provider: ${!selected_providers[*]}"
    separator

    # 读取已有配置
    local existing_base_url="$DEFAULT_BASE_URL"
    if [ -f "$CONFIG_FILE" ] && cmd_exists python3; then
        existing_base_url=$(python3 -c "
import json, sys
try:
    with open('$CONFIG_FILE', 'r') as f:
        data = json.load(f)
    providers = data.get('models', {}).get('providers', {})
    # 优先 Claude
    claude = providers.get('api-proxy-claude', {})
    raw = claude.get('baseUrl', '')
    if raw:
        print(raw)
        sys.exit(0)
    for pkey, pdata in providers.items():
        raw = pdata.get('baseUrl', '')
        if raw:
            # 去掉后缀
            for suffix in ['/v1beta', '/v1', '']:
                if suffix and raw.endswith(suffix):
                    print(raw[:-len(suffix)])
                    sys.exit(0)
            print(raw)
            sys.exit(0)
    print('$DEFAULT_BASE_URL')
except Exception:
    print('$DEFAULT_BASE_URL')
" 2>/dev/null || echo "$DEFAULT_BASE_URL")
    fi

    # 读取已有 API keys
    declare -A existing_keys
    if [ -f "$AUTH_FILE" ] && cmd_exists python3; then
        while IFS='=' read -r k v; do
            existing_keys["$k"]="$v"
        done < <(python3 -c "
import json
try:
    with open('$AUTH_FILE', 'r') as f:
        data = json.load(f)
    profiles = data.get('profiles', {})
    for pkey in ['api-proxy-gpt', 'api-proxy-claude', 'api-proxy-google', 'api-proxy-other']:
        key = profiles.get(f'{pkey}:default', {}).get('key', '')
        print(f'{pkey}={key}')
except Exception:
    pass
" 2>/dev/null)
    fi

    # 收集每个 provider 的 base_url 和 api_key
    declare -A provider_base_urls
    declare -A provider_api_keys

    for provider_key in "${!selected_providers[@]}"; do
        local label="${selected_providers[$provider_key]}"
        echo ""
        echo -e "${BOLD}── 配置 $label ($provider_key) ──${NC}"

        # 获取该 provider 的 suffix
        local suffix=""
        for p in "${PROVIDERS[@]}"; do
            IFS='|' read -r pk pl ps pa <<< "$p"
            if [ "$pk" = "$provider_key" ]; then
                suffix="$ps"
                break
            fi
        done

        # Base URL
        local default_url="$existing_base_url"
        echo -e "  Base URL ${DIM}(不含 provider 后缀 $suffix)${NC}"
        read -rp "  Base URL [$default_url]: " input_url
        local final_url="${input_url:-$default_url}"
        final_url="${final_url%/}" # 去末尾斜杠
        provider_base_urls["$provider_key"]="$final_url"

        # API Key（明文显示）
        local default_key="${existing_keys[$provider_key]:-}"
        local key_hint=""
        if [ -n "$default_key" ]; then
            key_hint=" [已有密钥，直接回车保留]"
        fi
        read -rp "  API Key${key_hint}: " input_key
        local final_key="${input_key:-$default_key}"
        provider_api_keys["$provider_key"]="$final_key"

        if [ -n "$final_key" ]; then
            success "$label 配置完成"
        else
            warn "$label 未设置 API Key"
        fi
    done

    separator

    # ── 模型配置 ──
    echo ""
    echo -e "${BOLD}模型配置${NC}"
    echo ""
    echo "默认模型列表:"
    for i in "${!DEFAULT_MODELS[@]}"; do
        IFS='|' read -r mp mi mn mc mm <<< "${DEFAULT_MODELS[$i]}"
        echo "  $((i+1))) $mn ($mi) [Provider: $mp]"
    done
    echo ""
    read -rp "使用默认模型列表？(Y/n): " use_default_models
    
    local models_args=()
    if [[ "$use_default_models" == "n" || "$use_default_models" == "N" ]]; then
        info "自定义模型配置暂不支持交互式编辑，将使用默认模型列表"
        info "安装后可手动编辑 $CONFIG_FILE"
    fi
    # 使用默认模型
    for m in "${DEFAULT_MODELS[@]}"; do
        models_args+=("$m")
    done

    # 默认模型选择
    echo ""
    echo "选择默认模型:"
    for i in "${!DEFAULT_MODELS[@]}"; do
        IFS='|' read -r mp mi mn mc mm <<< "${DEFAULT_MODELS[$i]}"
        local full_id="$mp/$mi"
        local marker=""
        if [ "$full_id" = "$DEFAULT_PRIMARY_MODEL" ]; then
            marker=" ${GREEN}(默认)${NC}"
        fi
        echo -e "  $((i+1))) $mn${marker}"
    done
    echo ""
    read -rp "选择默认模型编号 [默认: 2 (Claude Sonnet 4.6)]: " model_choice
    
    local primary_model="$DEFAULT_PRIMARY_MODEL"
    if [ -n "$model_choice" ] && [ "$model_choice" -ge 1 ] 2>/dev/null && [ "$model_choice" -le ${#DEFAULT_MODELS[@]} ] 2>/dev/null; then
        local idx=$((model_choice - 1))
        IFS='|' read -r mp mi mn mc mm <<< "${DEFAULT_MODELS[$idx]}"
        primary_model="$mp/$mi"
        info "默认模型设置为: $mn ($primary_model)"
    else
        info "使用默认模型: Claude Sonnet 4.6"
    fi

    # Workspace
    echo ""
    read -rp "Workspace 路径 [$DEFAULT_WORKSPACE]: " workspace_input
    local workspace="${workspace_input:-$DEFAULT_WORKSPACE}"

    separator

    # ── 生成配置 ──
    echo ""
    info "正在生成配置文件 ..."

    # 构建 auth 参数
    local auth_args=()
    for provider_key in "${!selected_providers[@]}"; do
        local p_base_url="${provider_base_urls[$provider_key]}"
        local p_api_key="${provider_api_keys[$provider_key]}"
        if [ -n "$p_api_key" ]; then
            auth_args+=("${provider_key}|${p_base_url}|${p_api_key}")
        fi
    done

    # 同时保留已有的、未在本次被选择配置的 provider 的 auth
    for p in "${PROVIDERS[@]}"; do
        IFS='|' read -r pk pl ps pa <<< "$p"
        if [ -z "${selected_providers[$pk]+_}" ]; then
            # 未被选择配置，保留已有
            local ek="${existing_keys[$pk]:-}"
            if [ -n "$ek" ]; then
                auth_args+=("${pk}|${existing_base_url}|${ek}")
            fi
        fi
    done

    if [ ${#auth_args[@]} -eq 0 ]; then
        error "没有任何 Provider 配置了 API Key，无法生成配置"
        return 1
    fi

    generate_and_save_config \
        "$existing_base_url" \
        "${models_args[@]}" \
        "--" \
        "$primary_model" \
        "$workspace" \
        "${auth_args[@]}"

    echo ""
    success "配置文件已保存:"
    echo -e "  📄 $CONFIG_FILE"
    echo -e "  🔑 $AUTH_FILE"
    echo ""
}

# ── 启动 Gateway ──

start_gateway() {
    header "🚀 启动 Gateway"

    if ! cmd_exists openclaw; then
        error "OpenClaw 未安装，请先安装"
        return 1
    fi

    info "正在启动 openclaw gateway ..."
    info "按 Ctrl+C 停止"
    echo ""
    openclaw gateway
}

# ── 启动 Dashboard ──

start_dashboard() {
    header "📊 启动 Dashboard"

    if ! cmd_exists openclaw; then
        error "OpenClaw 未安装，请先安装"
        return 1
    fi

    info "正在启动 openclaw dashboard ..."
    info "按 Ctrl+C 停止"
    echo ""
    openclaw dashboard
}

# ── 主菜单 ──

show_menu() {
    echo ""
    echo -e "${CYAN}${BOLD}🐾 OpenClaw Linux 安装配置工具${NC}"
    echo ""
    echo "  1) 环境检测"
    echo "  2) 安装 OpenClaw"
    echo "  3) 安装 uv"
    echo "  4) 配置 API 密钥与模型"
    echo "  5) 启动 Gateway"
    echo "  6) 启动 Dashboard"
    separator
    echo "  7) 卸载 OpenClaw"
    echo "  8) 卸载 uv"
    separator
    echo "  0) 退出"
    echo ""
}

# ── 快速安装模式（非交互）──

quick_install() {
    header "⚡ 快速安装模式"

    # 1. 环境检测
    check_environment

    # 2. 安装 OpenClaw
    if ! cmd_exists openclaw; then
        install_openclaw || true
    else
        success "OpenClaw 已安装，跳过"
    fi

    # 3. 安装 uv
    if ! cmd_exists uv; then
        install_uv || true
    else
        success "uv 已安装，跳过"
    fi

    # 4. 配置 API
    configure_api
}

# ── 入口 ──

main() {
    # 检查 Python3（用于生成 JSON 配置）
    if ! cmd_exists python3; then
        error "需要 python3 来生成配置文件，请先安装 Python 3"
        exit 1
    fi

    # 支持命令行参数
    case "${1:-}" in
        check|status)
            check_environment
            exit 0
            ;;
        install)
            install_openclaw
            exit $?
            ;;
        install-uv)
            install_uv
            exit $?
            ;;
        config|configure)
            configure_api
            exit $?
            ;;
        gateway)
            start_gateway
            exit $?
            ;;
        dashboard)
            start_dashboard
            exit $?
            ;;
        uninstall)
            uninstall_openclaw
            exit $?
            ;;
        uninstall-uv)
            uninstall_uv
            exit $?
            ;;
        quick)
            quick_install
            exit $?
            ;;
        help|--help|-h)
            echo "用法: $0 [命令]"
            echo ""
            echo "命令:"
            echo "  check        环境检测"
            echo "  install      安装 OpenClaw"
            echo "  install-uv   安装 uv"
            echo "  config       配置 API 密钥与模型"
            echo "  gateway      启动 Gateway"
            echo "  dashboard    启动 Dashboard"
            echo "  uninstall    卸载 OpenClaw"
            echo "  uninstall-uv 卸载 uv"
            echo "  quick        快速安装（安装 + 配置一条龙）"
            echo ""
            echo "不带参数时进入交互式菜单模式"
            exit 0
            ;;
        "")
            # 交互式菜单
            ;;
        *)
            error "未知命令: $1"
            echo "使用 $0 --help 查看帮助"
            exit 1
            ;;
    esac

    # 交互式菜单循环
    while true; do
        show_menu
        read -rp "请选择操作 [0-8]: " choice
        case "$choice" in
            1) check_environment ;;
            2) install_openclaw ;;
            3) install_uv ;;
            4) configure_api ;;
            5) start_gateway ;;
            6) start_dashboard ;;
            7) uninstall_openclaw ;;
            8) uninstall_uv ;;
            0)
                echo ""
                info "再见！👋"
                exit 0
                ;;
            *)
                warn "无效选择，请重试"
                ;;
        esac
    done
}

main "$@"
