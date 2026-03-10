# OpenClaw 安装配置工具

一个可视化的 Windows 桌面工具，用于一键安装和配置 [OpenClaw](https://openclaw.ai/)。

## 功能特性

- **环境检测** — 自动检测 Node.js、npm、OpenClaw 的安装状态及配置文件状态
- **一键安装** — 通过 GUI 按钮直接运行 `npm i -g openclaw`，实时显示安装日志
- **API 配置** — 可视化填写 Base URL 和各模型 API Key（GPT / Claude / Google）
- **配置生成** — 自动生成 `openclaw.json` 和 `auth-profiles.json` 到正确目录
- **启动服务** — 一键启动 Gateway 和 Dashboard

## 前置要求

- Windows 10/11
- [Python 3.10+](https://www.python.org/)（仅使用内置 tkinter，无需额外依赖）
- [Node.js 18+](https://nodejs.org/)（安装 OpenClaw 需要）

## 使用方式

```bash
python main.py
```

## 工具界面说明

| 区域 | 说明 |
|------|------|
| 环境检测 | 显示 Node.js / npm / OpenClaw / 配置文件的安装状态 |
| API 配置 | 填写 API Base URL 和三个模型的 API Key |
| 启动服务 | 启动 Gateway 和 Dashboard |
| 日志输出 | 实时显示操作日志 |

## 配置文件路径

- `%USERPROFILE%\.openclaw\openclaw.json` — 主配置文件
- `%USERPROFILE%\.openclaw\agents\main\agent\auth-profiles.json` — API 密钥文件

## 项目结构

```
openclawInstallTools/
├── main.py          # 入口文件
├── gui.py           # GUI 界面模块
├── installer.py     # 安装与配置核心逻辑
└── README.md        # 本文件
```

## 参考文档

- [OpenClaw 配置教程](https://yansd.apifox.cn/8139289m0)
- [烟神殿 AI](https://yansd666.com/)
