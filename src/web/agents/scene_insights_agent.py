from __future__ import annotations

from typing import TypedDict, List, Dict, Any
import json
import re

import pandas as pd

from langgraph.graph import StateGraph, START, END

from src.web.connect_openrouter import get_response_llm


class SceneInsightsState(TypedDict, total=False):
    """Состояние графа для извлечения производственных атрибутов сцен."""

    scenes: List[Dict[str, Any]]
    fields: List[str]
    desc_fields: List[str]
    analysis: List[Dict[str, Any]]
    dataframe: pd.DataFrame


def _build_prompt(scene: Dict[str, Any], fields: List[str], desc_fields: List[str]) -> str:
    """Создаёт промпт для анализа конкретной сцены."""

    # Формируем список атрибутов с описаниями
    field_lines_parts = []
    for i, field in enumerate(fields):
        desc = desc_fields[i] if i < len(desc_fields) and desc_fields[i] else ""
        if desc:
            field_lines_parts.append(f"- {field}: {desc}")
        else:
            field_lines_parts.append(f"- {field}")
    
    field_lines = "\n".join(field_lines_parts)
    prompt = (
        "Ты — продюсерский аналитик. Получишь сцену сериального сценария в Markdown и список производственных атрибутов.\n"
        "Твоя задача — вывести структурированные данные.\n\n"
        "Требования:\n"
        "1. Проанализируй сцену и найди информацию по каждому атрибуту.\n"
        "2. Если информации нет, укажи null.\n"
        "3. Верни JSON-объект со следующими ключами: {fields}.\n"
        "4. Каждый ключ должен соответствовать либо строке, либо списку строк (если объектов несколько).\n"
        "5. Не добавляй пояснений вне JSON.\n\n"
        "Перечень атрибутов:\n"
        f"{field_lines}\n\n"
        "Описание сцены:\n"
        f"ID: {scene.get('id', '')}\n"
        f"Заголовок: {scene.get('title', '')}\n"
        "Текст:\n"
        f"{scene.get('text', '')}\n"
    )
    return prompt


def _extract_json(text: str) -> Dict[str, Any]:
    """Пытается извлечь JSON из ответа модели."""
    if not text:
        return {}

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Попытаемся найти JSON-объект внутри текста
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}
    return {}


def _normalize_value(value: Any) -> Any:
    """Нормализует значения: списки -> строки через '; ' для удобства."""

    if isinstance(value, list):
        return "; ".join(str(item).strip() for item in value if str(item).strip())
    if value is None:
        return ""
    return str(value).strip()


def _analyze_scenes(state: SceneInsightsState) -> SceneInsightsState:
    """Выполняет LLM-анализ каждой сцены и формирует список словарей."""

    scenes = state.get("scenes", [])
    fields = state.get("fields", [])
    desc_fields = state.get("desc_fields", [])
    results: List[Dict[str, Any]] = []

    for scene in scenes:
        prompt = _build_prompt(scene, fields, desc_fields)
        llm_answer = get_response_llm(prompt, model = 'minimax/minimax-m2:free')
        data = _extract_json(llm_answer)
        scene_result: Dict[str, Any] = {}
        for field in fields:
            scene_result[field] = _normalize_value(data.get(field)) if isinstance(data, dict) else ""
        results.append(scene_result)

    return {**state, "analysis": results}


def _build_dataframe(state: SceneInsightsState) -> SceneInsightsState:
    """Создаёт pandas DataFrame из результатов анализа."""

    scenes = state.get("scenes", [])
    fields = state.get("fields", [])
    analysis = state.get("analysis", [])

    records: List[Dict[str, Any]] = []
    for idx, scene in enumerate(scenes):
        row: Dict[str, Any] = {
            "scene_id": scene.get("id", f"scene_{idx+1}"),
            "scene_title": scene.get("title", ""),
        }
        extracted = analysis[idx] if idx < len(analysis) else {}
        for field in fields:
            row[field] = extracted.get(field, "")
        records.append(row)

    columns = ["scene_id", "scene_title"] + fields
    dataframe = pd.DataFrame(records, columns=columns)
    return {**state, "dataframe": dataframe}


def create_scene_insights_agent():
    """Создаёт LangGraph-агента с двумя узлами: анализ сцен → построение DataFrame."""

    graph = StateGraph(SceneInsightsState)
    graph.add_node("analyze", _analyze_scenes)
    graph.add_node("dataframe", _build_dataframe)

    graph.add_edge(START, "analyze")
    graph.add_edge("analyze", "dataframe")
    graph.add_edge("dataframe", END)

    return graph.compile()


def run_scene_insights_agent(
    scenes: List[Dict[str, Any]],
    fields: List[str],
    desc_fields: List[str]
) -> pd.DataFrame:
    """Утилита для запуска агента: возвращает DataFrame с извлечёнными атрибутами."""

    app = create_scene_insights_agent()
    init_state: SceneInsightsState = {"scenes": scenes, "fields": fields, 'desc_fields': desc_fields}
    final_state: SceneInsightsState = app.invoke(init_state)
    return final_state.get("dataframe", pd.DataFrame())


if __name__ == "__main__":
    import argparse
    import json as json_module

    parser = argparse.ArgumentParser(description="Агент извлечения производственных атрибутов сцен")
    parser.add_argument("scenes_json", help="Путь к JSON-файлу со списком сцен (id, title, text)")
    parser.add_argument(
        "--fields",
        nargs="*",
        default=[
            "locations",
            "time_of_day",
            "main_characters",
            "secondary_characters",
            "extras",
            "props",
            "stunts_specials",
        ],
        help="Список атрибутов для извлечения",
    )
    args = parser.parse_args()

    with open(args.scenes_json, "r", encoding="utf-8") as fh:
        scenes_input = json_module.load(fh)

    dataframe = run_scene_insights_agent(scenes_input, args.fields)
    print(dataframe.to_json(force_ascii=False, orient="records", indent=2))


