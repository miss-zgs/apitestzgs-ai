"""
Agent 核心模块

实现基于 LangGraph 的 ReAct Agent。
负责：接收任务 → 调用 LLM → 选择工具 → 执行 → 判断是否完成。
"""
import logging
from typing import Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent
from langgraph.graph.state import CompiledStateGraph

from agent.config import (
    AGENT_API_KEY,
    AGENT_BASE_URL,
    AGENT_MODEL,
    AGENT_TEMPERATURE,
    MAX_ITERATIONS,
    MAX_REQUESTS_PER_TASK,
)
from agent.prompts import build_system_prompt
from agent.tools.http_tool import send_http_request, reset_request_counter
from agent.tools.assertion_tool import (
    check_status_code,
    check_json_field,
    check_json_contains,
    check_json_not_empty,
    extract_json_value,
)
from agent.tools.data_tool import load_test_cases, list_test_data_files
from agent.tools.file_tool import read_project_file
from config.settings import get_base_url, get_current_env

logger = logging.getLogger(__name__)


# Agent 可用的全部工具集
ALL_TOOLS = [
    send_http_request,
    check_status_code,
    check_json_field,
    check_json_contains,
    check_json_not_empty,
    extract_json_value,
    load_test_cases,
    list_test_data_files,
    read_project_file,
]


def create_llm() -> ChatAnthropic:
    """
    创建 LLM 实例（通过 Anthropic 兼容接口调用中转站）

    :return: ChatAnthropic 实例
    :raises ValueError: API Key 未配置时抛出
    """
    if not AGENT_API_KEY:
        raise ValueError(
            "AGENT_API_KEY 未配置。请在 .env 文件中设置:\n"
            "AGENT_API_KEY=your_api_key_here\n"
            "AGENT_BASE_URL=https://api.meai.cloud"
        )

    return ChatAnthropic(
        model=AGENT_MODEL,
        api_key=AGENT_API_KEY,
        base_url=AGENT_BASE_URL,
        temperature=AGENT_TEMPERATURE,
        max_retries=2,
        timeout=120,
    )


def create_agent_graph() -> CompiledStateGraph:
    """
    创建 Agent 图（基于 LangGraph 的 ReAct Agent）

    组装 LLM + System Prompt + Tools，返回编译后的 Agent 图。

    :return: CompiledGraph 实例
    """
    llm = create_llm()

    # 构建动态 System Prompt
    system_prompt_text = build_system_prompt(
        base_url=get_base_url(),
        current_env=get_current_env(),
        max_requests=MAX_REQUESTS_PER_TASK,
    )

    # 创建 ReAct Agent
    graph = create_react_agent(
        model=llm,
        tools=ALL_TOOLS,
        prompt=system_prompt_text,
    )

    return graph


class TestAgent:
    """
    API 测试 Agent

    封装 LangGraph ReAct Agent，提供对话式交互接口。
    支持多轮对话，维护对话历史。
    """

    def __init__(self):
        """初始化 Agent，创建图和对话历史"""
        self._graph: Optional[CompiledStateGraph] = None
        self._chat_history: list[HumanMessage | AIMessage] = []

    @property
    def graph(self) -> CompiledStateGraph:
        """懒加载 Agent 图（首次调用时创建）"""
        if self._graph is None:
            self._graph = create_agent_graph()
            logger.info(
                "Agent 初始化完成 [模型: %s, 环境: %s, 最大轮次: %d]",
                AGENT_MODEL, get_current_env(), MAX_ITERATIONS,
            )
        return self._graph

    def chat(self, user_input: str) -> str:
        """
        与 Agent 对话

        发送用户输入，Agent 自主规划并执行，返回最终结果。
        自动维护对话历史，支持多轮上下文。

        :param user_input: 用户的自然语言输入
        :return: Agent 的回复文本
        """
        # 每次新对话重置请求计数器
        reset_request_counter()

        try:
            # 构建消息列表（历史 + 当前输入）
            messages = list(self._chat_history) + [HumanMessage(content=user_input)]

            # 调用 Agent 图，设置递归限制防止死循环
            result = self.graph.invoke(
                {"messages": messages},
                config={"recursion_limit": MAX_ITERATIONS * 2},
            )

            # 从结果中提取最后一条 AI 消息
            output_messages = result.get("messages", [])
            agent_output = ""
            for message in reversed(output_messages):
                if isinstance(message, AIMessage) and message.content:
                    agent_output = message.content
                    break

            if not agent_output:
                agent_output = "Agent 未返回有效结果"

            # 更新对话历史（使用 LangChain Message 类型）
            self._chat_history.append(HumanMessage(content=user_input))
            self._chat_history.append(AIMessage(content=agent_output))

            # 控制历史长度（保留最近 10 轮 = 20 条消息）
            if len(self._chat_history) > 20:
                self._chat_history = self._chat_history[-20:]

            return agent_output

        except Exception as exc:
            error_message = f"Agent 执行出错: {type(exc).__name__}: {str(exc)}"
            logger.error(error_message, exc_info=True)
            return error_message

    def clear_history(self):
        """清空对话历史"""
        self._chat_history.clear()
        logger.info("对话历史已清空")

    def get_status(self) -> str:
        """获取 Agent 当前状态信息"""
        from agent.tools.http_tool import get_request_count
        return (
            f"模型: {AGENT_MODEL}\n"
            f"环境: {get_current_env()}\n"
            f"Base URL: {get_base_url()}\n"
            f"对话轮次: {len(self._chat_history) // 2}\n"
            f"本轮请求数: {get_request_count()}/{MAX_REQUESTS_PER_TASK}\n"
            f"最大迭代: {MAX_ITERATIONS}"
        )
