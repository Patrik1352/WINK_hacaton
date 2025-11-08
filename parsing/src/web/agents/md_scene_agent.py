from typing import TypedDict, List, Dict, Any, Callable, Tuple
import re
import json
import os

import re
from typing import List, Dict, Any, Tuple

def _default_parse_scenes(markdown_text: str) -> List[Dict[str, Any]]:
    """Парсинг сцен в сценарии, включая случаи без явных номеров.

    Поддерживает:
      - **3-1. НАТ. ...**
      - **1.1 НАТ. ...**
      - 1-16. НАТ. ...
      - **1-3-N1. ...**
      - НАТ. ГОРОД. ДЕНЬ
      - ИНТ. КВАРТИРА. ВЕЧЕР
    """

    # Регулярка для формализованных заголовков
    header_regex_numbered = re.compile(
        r"^(?:\*\*)?\s*(?P<id>[0-9]+(?:[.-][0-9A-Za-z]+)*?)\.?\s+(?P<title>(?:НАТ|ИНТ|EXT|INT|EXT)\..+?)\s*(?:\*\*)?$",
        re.IGNORECASE
    )

    # Регулярка для заголовков без номера (начинаются с НАТ., ИНТ., EXT., INT.)
    header_regex_plain = re.compile(
        r"^(?:\*\*)?\s*(?P<title>(?:НАТ|ИНТ|EXT|INT|EXT)\..+?)\s*(?:\*\*)?$",
        re.IGNORECASE
    )

    lines = markdown_text.splitlines()
    headers: List[Tuple[int, str, str]] = []  # (line_idx, id, title)
    auto_counter = 1

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue

        # Сначала пытаемся найти заголовок с номером
        m = header_regex_numbered.match(stripped)
        if m:
            scene_id = m.group("id").strip()
            title = m.group("title").strip()
            headers.append((i, scene_id, title))
            continue

        # Потом ищем заголовки без номера
        m = header_regex_plain.match(stripped)
        if m:
            scene_id = str(auto_counter)
            auto_counter += 1
            title = m.group("title").strip()
            headers.append((i, scene_id, title))

    # Если не нашли ни одного заголовка — возвращаем весь текст одной сценой
    if not headers:
        return [{"id": "0", "title": "FULL", "text": markdown_text.strip()}]

    # Разбиваем текст по найденным заголовкам
    scenes: List[Dict[str, Any]] = []
    for idx, (line_idx, scene_id, title) in enumerate(headers):
        start = line_idx + 1
        end = headers[idx + 1][0] if idx + 1 < len(headers) else len(lines)
        text_block = "\n".join(lines[start:end]).strip()


        match = re.findall(r'\d+', scene_id)
        if match:
            scene_id = int(match[-1])  # Берем последнее число


        scenes.append({
            "id": scene_id,
            "title": title,
            "text": text_block
        })

    return scenes
