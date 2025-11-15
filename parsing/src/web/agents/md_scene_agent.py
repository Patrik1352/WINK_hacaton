import re
from typing import List, Dict, Any, Tuple

def _default_parse_scenes(markdown_text: str) -> List[Dict[str, Any]]:
    """Парсинг сцен с игнорированием заголовков, содержащих 'УДАЛЕНА'."""

    header_regex_numbered = re.compile(
        r"^\s*(?P<id>[0-9]+(?:[.\-][0-9A-Za-zА-Яа-я]+)*)\.?\s*(?P<title>(?:НАТ|ИНТ|EXT|INT)(?:/ИНТ)?\..*)$",
        re.IGNORECASE
    )

    header_regex_plain = re.compile(
        r"^\s*(?P<title>(?:НАТ|ИНТ|EXT|INT)(?:/ИНТ)?\..*)$",
        re.IGNORECASE
    )

    lines = markdown_text.splitlines()
    headers: List[Tuple[int, str, str]] = []
    auto_counter = 1

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue

        # Убираем ВСЕ звездочки внутри номера и названия сцены
        cleaned = re.sub(r'\*+', '', stripped)

        # Заголовок с номером
        m = header_regex_numbered.match(cleaned)
        if m:
            scene_id = m.group("id").strip()
            title = m.group("title").strip()
            if "УДАЛЕНА" in title.upper():
                continue  # Пропускаем такие сцены
            headers.append((i, scene_id, title))
            continue

        # Заголовок без номера
        m = header_regex_plain.match(cleaned)
        if m:
            title = m.group("title").strip()
            if "УДАЛЕНА" in title.upper():
                continue  # Пропускаем такие сцены
            scene_id = str(auto_counter)
            auto_counter += 1
            headers.append((i, scene_id, title))

    if not headers:
        return [{"id": "0", "title": "FULL", "text": markdown_text.strip()}]

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

    _check_scene_order(scenes)
    return scenes

def _check_scene_order(scenes: List[Dict[str, Any]]) -> None:
    def parse_scene_id(scene_id: str) -> Tuple[List[int], str]:
        parts = re.split(r'[.\-]', scene_id)
        numbers = []
        suffix = ""
        for part in parts:
            if part.isdigit():
                numbers.append(int(part))
            else:
                m = re.match(r'^(\d+)', part)
                if m:
                    numbers.append(int(m.group(1)))
                    suffix = part[len(m.group(1)):]
                else:
                    suffix = part
        return numbers, suffix

    prev_numbers = None
    prev_suffix = ""
    prev_id = None

    for scene in scenes:
        scene_id = scene["id"]
        if scene_id.isdigit():
            continue
        numbers, suffix = parse_scene_id(scene_id)
        if prev_numbers is not None and numbers:
            if len(numbers) >= 1 and len(prev_numbers) >= 1:
                if numbers[0] < prev_numbers[0]:
                    print(f"⚠️  WARNING: Нарушен порядок нумерации сцен: '{prev_id}' -> '{scene_id}'")
                elif numbers[0] == prev_numbers[0] and len(numbers) > 1 and len(prev_numbers) > 1:
                    if numbers[1] < prev_numbers[1]:
                        print(f"⚠️  WARNING: Нарушен порядок подномеров: '{prev_id}' -> '{scene_id}'")
        if numbers:
            prev_numbers = numbers
            prev_suffix = suffix
            prev_id = scene_id

# Тесты
if __name__ == "__main__":
    # Тест 1: Оригинальный пример
    test_text1 = """**1-4-А. ИНТ. КВАРТИРА БОКОВА.ВАННАЯ НОЧЬ 1. **
**МАРИНА (00:12)**

На раковине в ванной – яркое пятно крови.

**1-4-В. ИНТ. КВАРТИРА БОКОВА.КОМНАТА НОЧЬ 1. **
**БОКОВ, МАРИНА, милиционер 1 (01:38)**

Текст второй сцены."""

    print("=== ТЕСТ 1: Оригинальный пример ===")
    scenes1 = _default_parse_scenes(test_text1)
    for scene in scenes1:
        print(f"ID: {scene['id']}, Title: {scene['title']}")
    print()

    # Тест 2: Проблемные случаи
    test_text2 = """**7-****1****. ИНТ. БОЛЬНИЦА.ПАЛАТА ЛЕНЫ ЕФИМОВОЙ. **
Текст первой сцены.

**7-****2****. ИНТ. кабинет ****РАЙКИНОЙ. ДЕНЬ**
Текст второй сцены.

**1-****6.ИНТ****. ЭКСПОЦЕНТР / ЦДП. ФОЙЕ. ДЕНЬ 2.**
Текст третьей сцены."""

    print("=== ТЕСТ 2: Звездочки внутри номера ===")
    scenes2 = _default_parse_scenes(test_text2)
    for scene in scenes2:
        print(f"ID: {scene['id']}, Title: {scene['title']}")
    print()

    # Тест 3: Десятичная точка в номере
    test_text3 = """**3.0-N1. ИНТ. МОСКВА. РАДИОСТАНЦИЯ. НОЧЬ. СД 2. 00:30**
Текст сцены."""

    print("=== ТЕСТ 3: Десятичная точка ===")
    scenes3 = _default_parse_scenes(test_text3)
    for scene in scenes3:
        print(f"ID: {scene['id']}, Title: {scene['title']}")
    print()

    # Тест 4: Ложное срабатывание
    test_text4 = """интересам? Я бы вступила

ПСИХОЛОГ

Тебе помогает сладкое? Тебе с ним лучше?

**1. ИНТ. КВАРТИРА. ДЕНЬ**
Настоящая сцена."""

    print("=== ТЕСТ 4: Избегание ложных срабатываний ===")
    scenes4 = _default_parse_scenes(test_text4)
    for scene in scenes4:
        print(f"ID: {scene['id']}, Title: {scene['title']}")
    print()

    # Тест 5: Нарушение порядка нумерации
    test_text5 = """**3-1. ИНТ. СЦЕНА ОДИН. **
Текст.

**2-5. ИНТ. СЦЕНА ДВА. **
Текст.

**4-1. ИНТ. СЦЕНА ТРИ. **
Текст."""

    print("=== ТЕСТ 5: Проверка порядка нумерации ===")
    scenes5 = _default_parse_scenes(test_text5)
    for scene in scenes5:
        print(f"ID: {scene['id']}, Title: {scene['title']}")
    print()