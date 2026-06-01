"""
Agent 命令行入口

提供交互式 CLI，通过自然语言与 API 测试 Agent 对话。

使用方式:
    python3 agent_run.py

支持的命令:
    /status  - 查看 Agent 状态
    /clear   - 清空对话历史
    /help    - 显示帮助
    /quit    - 退出
"""
import sys
import logging

from utils.logger import setup_logging


def print_banner():
    """打印启动 Banner"""
    print("\n" + "=" * 60)
    print("  🤖 API 测试 Agent (Powered by LangChain + Claude)")
    print("=" * 60)
    print("  输入自然语言描述你的测试需求，Agent 会自动执行。")
    print("  命令: /status | /clear | /help | /quit")
    print("=" * 60 + "\n")


def print_help():
    """打印帮助信息"""
    print("""
📖 使用帮助:
  直接输入自然语言即可，例如:
    - "测试 /posts/1 接口，期望状态码 200"
    - "加载 test_demo.yaml 并执行所有用例"
    - "向 /posts 发送 POST 请求，body 为 {title: test, body: hello, userId: 1}"
    - "列出所有可用的测试数据文件"

  内置命令:
    /status  - 查看 Agent 当前状态（模型、环境、请求数等）
    /clear   - 清空对话历史，开始新的对话
    /help    - 显示本帮助
    /quit    - 退出 Agent
""")


def main():
    """主函数：命令行交互循环"""
    # 初始化日志
    setup_logging()
    logger = logging.getLogger(__name__)

    print_banner()

    # 延迟导入，确保环境检查在打印 banner 之后
    try:
        from agent.core import TestAgent
    except ImportError as exc:
        print(f"\n❌ 导入 Agent 模块失败: {exc}")
        print("请确认已安装依赖: pip install -r requirements.txt")
        sys.exit(1)

    # 创建 Agent 实例
    try:
        agent = TestAgent()
        # 触发懒加载，验证配置
        _ = agent.graph
        print("✅ Agent 初始化成功！\n")
    except ValueError as exc:
        print(f"\n❌ Agent 初始化失败: {exc}")
        sys.exit(1)
    except Exception as exc:
        print(f"\n❌ Agent 初始化失败: {type(exc).__name__}: {exc}")
        print("请检查 .env 中的 AGENT_API_KEY 和 AGENT_BASE_URL 配置。")
        sys.exit(1)

    # 交互循环
    while True:
        try:
            user_input = input("👤 你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n👋 再见！")
            break

        if not user_input:
            continue

        # 处理内置命令
        if user_input.startswith("/"):
            command = user_input.lower()
            if command == "/quit" or command == "/exit":
                print("\n👋 再见！")
                break
            elif command == "/status":
                print(f"\n📊 Agent 状态:\n{agent.get_status()}\n")
                continue
            elif command == "/clear":
                agent.clear_history()
                print("🧹 对话历史已清空。\n")
                continue
            elif command == "/help":
                print_help()
                continue
            else:
                print(f"❓ 未知命令: {user_input}，输入 /help 查看帮助。\n")
                continue

        # 调用 Agent
        print("\n🤖 Agent 思考中...\n")
        response = agent.chat(user_input)
        print(f"🤖 Agent: {response}\n")


if __name__ == "__main__":
    main()
