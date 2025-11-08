from typing import TypedDict, List, Dict

# LangGraph core
from langgraph.graph import StateGraph, START, END

# Используем уже готовое подключение к OpenRouter
from src.web.connect_openrouter import get_response_llm


class AgentState(TypedDict):
    """Состояние графа с историей сообщений в формате ChatML-подобного списка."""

    messages: List[Dict[str, str]]


def _call_model(state: AgentState) -> AgentState:
    """Узел-главная логика: берём последний запрос пользователя и получаем ответ LLM."""

    user_message = state["messages"][-1]["content"] if state["messages"] else ""
    answer = get_response_llm(user_message)
    updated_messages = state["messages"] + [{"role": "assistant", "content": answer}]
    return {"messages": updated_messages}


def create_simple_agent():
    """Создаёт и компилирует простой агент на LangGraph с одним узлом модельного вызова."""

    graph = StateGraph(AgentState)
    graph.add_node("model", _call_model)
    graph.add_edge(START, "model")
    graph.add_edge("model", END)
    return graph.compile()


def run_simple_agent(query: str) -> str:
    """Утилита для быстрого запуска агента одной командой.

    Возвращает текст ответа ассистента.
    """

    app = create_simple_agent()
    initial_state: AgentState = {"messages": [{"role": "user", "content": query}]}
    final_state: AgentState = app.invoke(initial_state)
    # Последнее сообщение — ответ ассистента
    return final_state["messages"][-1]["content"]


if __name__ == "__main__":
    # Пример локального запуска: python -m src.web.agents.simple_agent
    demo_answer = run_simple_agent("Привет! Расскажи, что ты умеешь?")
    print(demo_answer)


