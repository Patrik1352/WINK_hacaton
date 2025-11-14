import re
from typing import List, Dict, Any, Tuple


def _default_parse_scenes(markdown_text: str) -> List[Dict[str, Any]]:
    """Парсинг сцен в сценарии, включая случаи без явных номеров.

    Поддерживает:
      - **3-1. НАТ. ...**
      - **1.1 НАТ. ...**
      - 1-16. НАТ. ...
      - **1-3-N1. ...**
      - **1-4-А. ИНТ. ...**
      - **1-4-В. ИНТ. ...**
      - НАТ. ГОРОД. ДЕНЬ
      - ИНТ. КВАРТИРА. ВЕЧЕР
    """

    # Регулярка для формализованных заголовков с номером
    # Поддерживает буквенные суффиксы (А, В, N1 и т.д.)
    header_regex_numbered = re.compile(
        r"^(?:\*\*)?\s*(?P<id>[0-9]+(?:[.-][0-9A-Za-zА-Яа-я]+)*?)\.?\s+(?P<title>(?:НАТ|ИНТ|EXT|INT)\..+?)\s*(?:\*\*)?$",
        re.IGNORECASE
    )

    # Регулярка для заголовков без номера (начинаются с НАТ., ИНТ., EXT., INT.)
    header_regex_plain = re.compile(
        r"^(?:\*\*)?\s*(?P<title>(?:НАТ|ИНТ|EXT|INT)\..+?)\s*(?:\*\*)?$",
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

        scenes.append({
            "id": scene_id,
            "title": title,
            "text": text_block
        })

    return scenes


# Тест на вашем примере
if __name__ == "__main__":
    test_text = """**1-4-А. ИНТ. КВАРТИРА БОКОВА.ВАННАЯ НОЧЬ 1. **
**МАРИНА (00:12)**

На раковине в ванной – яркое пятно крови. Молодая, очень худая женщина (МАРИНА), кашляет и сплёвывает очередной сгусток, включает воду, смывает кровь, ополаскивает лицо и выходит из ванной.

**1-4-В. ИНТ. КВАРТИРА БОКОВА.КОМНАТА НОЧЬ 1. **
**БОКОВ, МАРИНА, милиционер 1 (01:38)**

Текст второй сцены."""

    scenes = _default_parse_scenes(test_text)

    for scene in scenes:
        print(f"ID: {scene['id']}")
        print(f"Title: {scene['title']}")
        print(f"Text: {scene['text'][:100]}...")
        print("-" * 50)