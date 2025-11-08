from typing import TypedDict, List, Dict, Optional, Any, Callable, Tuple
import re
import json
import os

# LangGraph core
from langgraph.graph import StateGraph, START, END

# Подключение к LLM через OpenRouter (как в simple_agent)
from src.web.connect_openrouter import get_response_llm


class MdSceneAgentState(TypedDict, total=False):
    """Состояние графа для агента парсинга сцен из Markdown."""

    # Обязательные входные данные
    md_path: str
    sample_chars: int

    # Промежуточные данные
    sample_text: str
    generated_code: str

    # Результат
    scenes: List[Dict[str, Any]]


def _read_sample(state: MdSceneAgentState) -> MdSceneAgentState:
    """Читает начало .md файла (sample_chars символов) для обучения агента."""

    md_path = state["md_path"]
    sample_chars = state.get("sample_chars", 6000)
    if not os.path.exists(md_path):
        raise FileNotFoundError(f"MD file not found: {md_path}")
    with open(md_path, "r", encoding="utf-8", errors="ignore") as f:
        sample_text = f.read(sample_chars)
    return {**state, "sample_text": sample_text}


def _extract_code_from_llm_text(text: str) -> str:
    """Извлекает код из ответа LLM. Поддержка ```python ... ``` и просто ``` ... ```.

    Если блоков несколько — берём первый. Если нет блоков, возвращаем исходный текст.
    """

    fence_pattern = re.compile(r"```(?:python)?\n([\s\S]*?)```", re.IGNORECASE)
    match = fence_pattern.search(text)
    if match:
        return match.group(1).strip()
    return text.strip()


def _build_codegen_prompt(sample_text: str) -> str:
    """Формирует промпт к LLM: сгенерировать функцию parse_scenes(markdown_text)."""

    instructions = (
        "Ты — помощник по обработке сценариев в формате Markdown. "
        "На вход у тебя кусок файла .md (часть эпизода). Твоя задача — написать автономную функцию Python "
        "parse_scenes(markdown_text: str) -> List[Dict[str, Any]], которая разбивает весь markdown на сцены.\n\n"
        "Требования к функции: \n"
        "- Не использовать чтение/запись файлов, только строку markdown_text.\n"
        "- Не использовать внешние зависимости. Разрешены стандартные конструкции Python и модуль re.\n"
        "- Вернуть список словарей: каждый элемент содержит 'id' (строка, например '1-16' или '3-2'), 'title' (строковый заголовок сцены без разметки), 'text' (полный текст сцены).\n"
        "- Определи устойчивые паттерны заголовков сцен на основе примера ниже. В сценариях встречаются варианты: \n"
        "  • Жирные заголовки с нумерацией, например: **3-1. НАТ. ...** или **1.1 НАТ. ...**\n"
        "  • Ненаборные заголовки вида: 1-16. НАТ. ...\n"
        "  • Могут быть маркеры времени/дня ('НОЧЬ', 'УТРО', 'СД 1. 00:15') и т.п.\n"
        "- Учитывай, что между сценами может быть много абзацев и реплик. Сцена — это блок от заголовка до следующего заголовка или конца файла.\n"
        "- Удали внешние ** в тексте заголовка при формировании 'title'. Поле 'id' вытащи из начала заголовка (например '3-2', '1.2', '1-3-N1' — оставь как есть именно идентификатор сцены, без точек и текста после).\n\n"
        "Верни только код функции (внутри одного блока кода). Не добавляй никакого текста вне кода."
    )

    example_hint = (
        "\n\nПример части входного markdown (укороченный):\n" +
        sample_text[:2000]
    )

    return instructions + example_hint


def _generate_code(state: MdSceneAgentState) -> MdSceneAgentState:
    """Запрашивает у LLM код функции parse_scenes и сохраняет его в состояние."""

    sample_text = state.get("sample_text", "")
    prompt = _build_codegen_prompt(sample_text)
    llm_answer = get_response_llm(prompt)
    code = _extract_code_from_llm_text(llm_answer)
    return {**state, "generated_code": code}


def _default_parse_scenes(markdown_text: str) -> List[Dict[str, Any]]:
    """Запасной разборщик на регулярках для распространённых шаблонов заголовков сцен.

    Пытается выделять заголовки вида:
      - **3-1. НАТ. ...**
      - **1.1 НАТ. ...**
      - 1-16. НАТ. ...
      - **1-3-N1. ...**
    """

    # Захватываем id сцены до первой точки, допускаем дефисы и N-индексы.
    # Примеры id: 3-2, 1.1, 1-3-N1, 1-17
    header_regex = re.compile(
        r"^(?:\*\*)?\s*(?P<id>[0-9]+(?:[.-][0-9A-Za-z]+)*?)\.?\s+(?P<title>.+?)\s*(?:\*\*)?$",
        re.IGNORECASE
    )

    lines = markdown_text.splitlines()
    indices: List[int] = []
    headers: List[Tuple[int, str, str]] = []  # (line_idx, id, title)

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        # Быстрые эвристики: начинается с **<digits> или <digits>
        if stripped.startswith("**") or stripped[0].isdigit():
            # Убираем ведущие ** и пробелы для проверки
            candidate = stripped
            # Пытаемся распознать жирный заголовок **...
            if candidate.startswith("**"):
                # Срежем начальные **, но не требуем закрывающих для поиска id
                candidate = candidate.lstrip("*").strip()
            m = header_regex.match(candidate)
            if m:
                scene_id = m.group("id").strip()
                title = m.group("title").strip()
                headers.append((i, scene_id, title))

    if not headers:
        return [{"id": "0", "title": "FULL", "text": markdown_text}]

    scenes: List[Dict[str, Any]] = []
    for idx, (line_idx, scene_id, title) in enumerate(headers):
        start = line_idx
        end = headers[idx + 1][0] if idx + 1 < len(headers) else len(lines)
        block = "\n".join(lines[start:end]).strip()
        # Очистим внешний жирный в заголовке
        clean_title = re.sub(r"^\*\*|\*\*$", "", title).strip()
        scenes.append({
            "id": scene_id,
            "title": clean_title,
            "text": block,
        })
    return scenes


def _safe_exec_and_get_parser(code: str) -> Callable[[str], List[Dict[str, Any]]]:
    """Безопасно выполняет сгенерированный код и возвращает функцию parse_scenes.

    Разрешённый окружение: ограниченный набор builtins и модуль re.
    """

    allowed_builtins = {
        "len": len,
        "range": range,
        "enumerate": enumerate,
        "sorted": sorted,
        "min": min,
        "max": max,
        "sum": sum,
        "any": any,
        "all": all,
        "map": map,
        "filter": filter,
        "list": list,
        "dict": dict,
        "set": set,
        "tuple": tuple,
        "str": str,
        "re": re,
    }

    safe_globals: Dict[str, Any] = {"__builtins__": allowed_builtins, "re": re}
    safe_locals: Dict[str, Any] = {}

    try:
        exec(code, safe_globals, safe_locals)
    except Exception as e:
        # Если код не выполнился — отдаём дефолтный парсер
        return _default_parse_scenes

    parse_func = safe_locals.get("parse_scenes") or safe_globals.get("parse_scenes")
    if not callable(parse_func):
        return _default_parse_scenes

    return parse_func  # type: ignore[return-value]


def _run_on_full_file(state: MdSceneAgentState) -> MdSceneAgentState:
    """Применяет сгенерированную функцию ко всему файлу и сохраняет список сцен."""

    md_path = state["md_path"]
    with open(md_path, "r", encoding="utf-8", errors="ignore") as f:
        full_text = f.read()

    code = state.get("generated_code", "").strip()
    parser = _safe_exec_and_get_parser(code) if code else _default_parse_scenes

    try:
        scenes = parser(full_text)
    except Exception:
        scenes = _default_parse_scenes(full_text)

    return {**state, "scenes": scenes}


def create_md_scene_agent():
    """Создаёт и компилирует агента на LangGraph с тремя узлами: чтение сэмпла → генерация кода → применение."""

    graph = StateGraph(MdSceneAgentState)
    graph.add_node("read_sample", _read_sample)
    graph.add_node("codegen", _generate_code)
    graph.add_node("run_full", _run_on_full_file)

    graph.add_edge(START, "read_sample")
    graph.add_edge("read_sample", "codegen")
    graph.add_edge("codegen", "run_full")
    graph.add_edge("run_full", END)

    return graph.compile()


def run_md_scene_agent(md_path: str, sample_chars: int = 6000) -> List[Dict[str, Any]]:
    """Утилита для быстрого запуска агента: возвращает список сцен всего файла."""

    app = create_md_scene_agent()
    init_state: MdSceneAgentState = {"md_path": md_path, "sample_chars": sample_chars}
    final_state: MdSceneAgentState = app.invoke(init_state)
    return final_state.get("scenes", [])


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m src.web.agents.md_scene_agent /Users/egorbykov/Desktop/Работа/2025/hackatons/wink/data/parsing/md/1 кейс Сценарии c Таблицами/Челюскин (с таблицей)/ЧЕЛЮСКИН_3С_05.09_ФИНАЛ.md [sample_chars]")
        sys.exit(1)

    path = sys.argv[1]
    sample = int(sys.argv[2]) if len(sys.argv) > 2 else 6000
    result = run_md_scene_agent(path, sample)
    # Выведем краткое резюме
    print(json.dumps({
        "file": path,
        "scenes_count": len(result),
        "scenes": [
            {"id": s.get("id"), "title": s.get("title"), "text_preview": (s.get("text", "")[:140] + ("..." if len(s.get("text", "")) > 140 else ""))}
            for s in result
        ]
    }, ensure_ascii=False, indent=2))


