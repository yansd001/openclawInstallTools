"""OpenClaw 安装配置工具 - 入口文件"""

from gui import OpenClawApp


def main():
    app = OpenClawApp()
    app.run()


if __name__ == "__main__":
    main()
