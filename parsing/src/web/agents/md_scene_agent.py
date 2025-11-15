import re
import json
from typing import List, Dict, Any, Tuple, Optional
from .llm_model import call_llm
from tqdm.auto import tqdm
import datetime


def _parse_scene_id(scene_id: str) -> Tuple[List[int], Optional[str]]:
    """
    Парсит ID сцены и возвращает числовые части и буквенный суффикс.

    Примеры:
        "1" -> ([1], None)
        "1-4" -> ([1, 4], None)
        "1-4-А" -> ([1, 4], "А")
        "3-1" -> ([3, 1], None)

    Args:
        scene_id: ID сцены в формате строки

    Returns:
        Кортеж (список числовых частей, буквенный суффикс или None)
    """
    # Разделяем по дефисам и точкам
    parts = re.split(r'[.-]', scene_id)
    numbers = []
    suffix = None

    for part in parts:
        part = part.strip()
        # Проверяем, является ли часть числом
        if part.isdigit():
            numbers.append(int(part))
        elif part and not part.isdigit():
            # Если это не число, это может быть буквенный суффикс
            # Проверяем, содержит ли только буквы
            if re.match(r'^[A-Za-zА-Яа-я]+$', part):
                suffix = part
            else:
                # Если содержит и цифры и буквы, пытаемся извлечь число
                num_match = re.search(r'\d+', part)
                if num_match:
                    numbers.append(int(num_match.group()))

    return (numbers, suffix)


def _get_next_expected_id(current_id: str) -> Optional[str]:
    """
    Определяет следующий ожидаемый ID на основе текущего.

    Args:
        current_id: Текущий ID сцены

    Returns:
        Следующий ожидаемый ID или None, если невозможно определить
    """
    numbers, suffix = _parse_scene_id(current_id)

    if not numbers:
        return None

    # Если есть буквенный суффикс, инкрементируем его
    if suffix:
        # Русские буквы
        if suffix in ['А', 'а']:
            next_suffix = 'Б'
        elif suffix in ['Б', 'б']:
            next_suffix = 'В'
        elif suffix in ['В', 'в']:
            next_suffix = 'Г'
        elif suffix in ['Г', 'г']:
            next_suffix = 'Д'
        else:
            # Для других букв или английских - инкрементируем последнее число
            numbers[-1] += 1
            next_suffix = None
    else:
        # Если нет суффикса, инкрементируем последнее число
        numbers[-1] += 1
        next_suffix = None

    # Формируем следующий ID
    if len(numbers) == 1:
        result = str(numbers[0])
    else:
        result = '-'.join(map(str, numbers))

    if next_suffix:
        result += f'-{next_suffix}'

    return result


def _detect_gaps_in_numbering(scenes: List[Dict[str, Any]]) -> List[Tuple[int, int]]:
    """
    Обнаруживает пропуски в нумерации сцен.

    Args:
        scenes: Список словарей сцен с полями 'id', 'title', 'text'

    Returns:
        Список кортежей (индекс_текущей_сцены, индекс_следующей_сцены) для сцен с пропусками
    """
    gaps = []

    for i in range(len(scenes) - 1):
        current_id = scenes[i]['id']
        next_id = scenes[i + 1]['id']

        # Пропускаем автоматически сгенерированные ID (просто числа)
        if current_id.isdigit() and next_id.isdigit():
            current_num = int(current_id)
            next_num = int(next_id)
            if next_num - current_num > 1:
                gaps.append((i, i + 1))
            continue

        # Для составных ID пытаемся определить ожидаемый следующий ID
        expected_next = _get_next_expected_id(current_id)
        if expected_next:
            # Нормализуем ID для сравнения (убираем точки, приводим к одному формату)
            expected_normalized = expected_next.replace('.', '-')
            next_normalized = next_id.replace('.', '-')

            # Если ожидаемый ID не совпадает со следующим, проверяем детальнее
            if expected_normalized != next_normalized:
                current_parsed = _parse_scene_id(current_id)
                next_parsed = _parse_scene_id(next_id)
                expected_parsed = _parse_scene_id(expected_next)

                # Проверяем, есть ли пропуск в числовой последовательности
                if len(current_parsed[0]) > 0 and len(next_parsed[0]) > 0:
                    # Если структура ID одинаковая (одинаковое количество уровней)
                    if len(current_parsed[0]) == len(next_parsed[0]):
                        # Проверяем все уровни кроме последнего - они должны совпадать
                        if current_parsed[0][:-1] == next_parsed[0][:-1]:
                            # Если разница в последнем числе больше 1, это пропуск
                            if next_parsed[0][-1] - current_parsed[0][-1] > 1:
                                gaps.append((i, i + 1))
                        # Если уровни не совпадают, но ожидаемый следующий ID отличается от реального
                        elif expected_parsed[0] != next_parsed[0]:
                            # Проверяем, не является ли следующий ID просто продолжением другой ветки
                            # Например, после "1-4-А" идет "1-5" - это не пропуск, а новая ветка
                            # Но если после "1-4" идет "1-6", это пропуск
                            if len(current_parsed[0]) >= 2 and len(next_parsed[0]) >= 2:
                                # Если первые уровни совпадают, но последний уровень пропущен
                                if (current_parsed[0][:-1] == next_parsed[0][:-1] and
                                        next_parsed[0][-1] - current_parsed[0][-1] > 1):
                                    gaps.append((i, i + 1))

    return gaps


def _split_text_by_headers(
        text: str,
        headers_info: List[Dict[str, Any]],
        current_scene_id: str,
        next_scene_id: str
) -> List[Dict[str, Any]]:
    """
    Разбивает исходный текст по найденным заголовкам сцен.
    Ищет заголовки в тексте по их содержимому и разбивает текст между ними.

    Args:
        text: Исходный текст для разбиения
        headers_info: Список словарей с информацией о заголовках (id, title)
        current_scene_id: ID текущей сцены
        next_scene_id: ID следующей сцены

    Returns:
        Список словарей с под-сценами
    """
    if not headers_info:
        # Если заголовки не найдены, возвращаем весь текст как одну сцену
        expected_id = _get_next_expected_id(current_scene_id) or f"{current_scene_id}-1"
        return [{
            "id": expected_id,
            "title": "UNKNOWN",
            "text": text
        }]

    scenes = []
    lines = text.splitlines()

    # Находим позиции заголовков в тексте по их содержимому
    header_positions = []
    for header_info in headers_info:
        title = header_info.get("title", "").strip()
        if not title:
            continue

        # Всегда используем заголовок от LLM, так как он уже правильный
        found_title = title

        # Ищем позицию заголовка в тексте
        # Создаем варианты заголовка для поиска (с учетом форматирования)
        title_variants = [
            title,
            title.upper(),
            title.lower(),
            f"**{title}**",
            f"**{title.upper()}**",
            title.replace(".", ". "),
            title.replace(". ", "."),
        ]

        found_position = None
        found_line_idx = None

        # Ищем заголовок в тексте по символам (более точный поиск)
        for variant in title_variants:
            # Ищем точное вхождение заголовка в тексте
            text_upper = text.upper()
            variant_upper = variant.upper()

            # Ищем первое вхождение заголовка
            pos = text_upper.find(variant_upper)
            if pos != -1:
                # Находим номер строки, в которой находится заголовок
                # Считаем количество переводов строк до позиции
                found_line_idx = text[:pos].count('\n')
                found_position = pos
                break

        # Если не нашли точное совпадение, ищем по ключевым словам
        if found_position is None:
            title_keywords = title.split()[:3]  # Первые 3 слова
            if len(title_keywords) >= 2:
                # Ищем строку, которая содержит первые два ключевых слова
                keyword1 = title_keywords[0].upper()
                keyword2 = title_keywords[1].upper() if len(title_keywords) > 1 else ""

                for line_idx, line in enumerate(lines):
                    line_upper = line.upper()
                    if keyword1 in line_upper and (not keyword2 or keyword2 in line_upper):
                        # Проверяем, что это действительно заголовок сцены
                        if any(kw in ["НАТ.", "ИНТ.", "EXT.", "INT."] for kw in [keyword1]):
                            found_line_idx = line_idx
                            # Вычисляем позицию символа начала строки
                            found_position = sum(len(lines[i]) + 1 for i in range(line_idx))  # +1 для \n
                            break

        # Если все еще не нашли, пытаемся найти хотя бы по первому слову
        if found_position is None:
            first_word = title.split()[0] if title else ""
            if first_word:
                for line_idx, line in enumerate(lines):
                    line_upper = line.upper()
                    if first_word.upper() in line_upper and any(
                            kw in line_upper for kw in ["НАТ.", "ИНТ.", "EXT.", "INT."]):
                        found_line_idx = line_idx
                        found_position = sum(len(lines[i]) + 1 for i in range(line_idx))
                        break

        if found_line_idx is not None:
            header_positions.append({
                "id": header_info.get("id", ""),
                "title": found_title,
                "line_idx": found_line_idx
            })

    # Сортируем заголовки по позиции
    header_positions.sort(key=lambda x: x["line_idx"])

    # Если заголовки не найдены, возвращаем весь текст как одну сцену
    if not header_positions:
        expected_id = _get_next_expected_id(current_scene_id) or f"{current_scene_id}-1"
        return [{
            "id": expected_id,
            "title": headers_info[0].get("title", "UNKNOWN") if headers_info else "UNKNOWN",
            "text": text
        }]

    # Разбиваем текст по найденным заголовкам
    for idx, header_pos in enumerate(header_positions):
        start_line = header_pos["line_idx"]
        end_line = header_positions[idx + 1]["line_idx"] if idx + 1 < len(header_positions) else len(lines)

        title = header_pos["title"]

        # Извлекаем текст сцены
        scene_lines = []

        # Обрабатываем строку с заголовком - извлекаем текст после заголовка
        if start_line < len(lines):
            header_line = lines[start_line]
            # Удаляем заголовок из строки, оставляя только текст после него
            header_line_clean = header_line.replace("**", "").strip()

            # Ищем позицию заголовка в строке
            title_variants = [
                title,
                title.upper(),
                title.lower(),
                f"**{title}**",
                f"**{title.upper()}**",
            ]

            text_after_title = ""
            for variant in title_variants:
                if variant in header_line_clean:
                    # Находим позицию после заголовка
                    pos = header_line_clean.upper().find(variant.upper())
                    if pos != -1:
                        text_after_title = header_line_clean[pos + len(variant):].strip()
                        break

            # Если не нашли заголовок в строке, берем всю строку (возможно, заголовок был в другой строке)
            if not text_after_title and header_line_clean:
                # Проверяем, не является ли вся строка заголовком
                if not any(kw in header_line_clean.upper() for kw in ["НАТ.", "ИНТ.", "EXT.", "INT."]):
                    text_after_title = header_line_clean
                # Иначе строка - это заголовок, пропускаем её

            if text_after_title:
                scene_lines.append(text_after_title)

        # Добавляем остальные строки до следующего заголовка
        scene_lines.extend(lines[start_line + 1:end_line])

        scene_text = "\n".join(scene_lines).strip()

        scenes.append({
            "id": header_pos["id"],
            "title": title,
            "text": scene_text
        })

    return scenes


def _split_scene_with_llm(text: str, current_scene_id: str, next_scene_id: str) -> List[Dict[str, Any]]:
    """
    Использует LLM для поиска заголовков сцен в тексте, затем разбивает текст по найденным заголовкам.
    LLM находит только заголовки, разбиение текста выполняется локально для ускорения.

    Args:
        text: Текст для разбиения
        current_scene_id: ID текущей сцены
        next_scene_id: ID следующей сцены

    Returns:
        Список словарей с под-сценами
    """
    prompt = f"""Ты анализируешь сценарий фильма. Между сценой {current_scene_id} и сценой {next_scene_id} обнаружен пропуск в нумерации. 

Текст между этими сценами:
{text}

Твоя задача - найти в тексте заголовки сцен (которые могут быть без явной нумерации).

Заголовки сцен обычно начинаются с:
- НАТ. (натура, внешняя сцена)
- ИНТ. (интерьер, внутренняя сцена)
- EXT. или INT. (английские варианты)

Формат заголовка: НАТ./ИНТ./EXT./INT. [описание места и времени]

Правила нумерации ID:
- После {current_scene_id} должна идти следующая сцена в последовательности
- Если {current_scene_id} содержит буквенный суффикс (например, "1-4-А"), следующая должна быть "1-4-Б", затем "1-4-В" и т.д.
- Если {current_scene_id} не содержит буквенного суффикса, следующая должна инкрементировать последнее число

Верни результат в формате JSON массива, где каждый элемент содержит:
- "id": ID сцены (строка), который заполняет пропуск в нумерации
- "title": заголовок сцены (строка, точно как он написан в тексте, начинается с НАТ./ИНТ./EXT./INT.)

ВАЖНО: 
- Верни ТОЛЬКО заголовки, которые реально есть в тексте
- НЕ генерируй текст сцен, только заголовки!
- Заголовок должен быть точно таким, как он написан в исходном тексте

Если текст представляет собой одну сцену без скрытых заголовков, верни массив с одним элементом с ID, который заполняет пропуск, и title на основе контекста текста.

Пример ответа:
[
  {{
    "id": "1-4-Б",
    "title": "ИНТ. КВАРТИРА. КОМНАТА. ДЕНЬ"
  }},
  {{
    "id": "1-4-В",
    "title": "ИНТ. КВАРТИРА. ВАННАЯ. ДЕНЬ"
  }}
]

Верни только валидный JSON массив, без дополнительных комментариев и markdown форматирования."""

    try:
        response = call_llm(prompt,
                            max_new_tokens=256)  # Уменьшаем количество токенов, так как генерируем только заголовки
        # Очищаем ответ от markdown форматирования, если есть
        response = response.strip()
        if response.startswith('```'):
            # Удаляем markdown блоки кода
            lines = response.split('\n')
            response = '\n'.join(lines[1:-1]) if len(lines) > 2 else response
        if response.startswith('```json'):
            lines = response.split('\n')
            response = '\n'.join(lines[1:-1]) if len(lines) > 2 else response

        headers_info = json.loads(response)
        if not isinstance(headers_info, list):
            headers_info = [headers_info]

        print(f"LLM ответила: {response}\n\n\n")

        # Разбиваем исходный текст по найденным заголовкам
        scenes = _split_text_by_headers(text, headers_info, current_scene_id, next_scene_id)

        return scenes
    except Exception as e:
        # В случае ошибки возвращаем текст как одну сцену
        print(f"Ошибка при разбиении сцены через LLM: {e}")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"/home/yc-user/EGOR_DONT_ENTER/WINK_hacaton/logs/llm_error_{timestamp}.txt"
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(response)
            print(f"Исходный текст сохранён в файл: {filename}")
        except Exception as file_error:
            print(f"Не удалось сохранить файл: {file_error}")
        return [{
            "id": f"{current_scene_id}-missing",
            "title": "UNKNOWN",
            "text": text
        }]


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

    # Проверяем наличие пропусков в нумерации
    gaps = _detect_gaps_in_numbering(scenes)

    # Обрабатываем пропуски, начиная с конца, чтобы индексы не сбивались
    for current_idx, next_idx in tqdm(reversed(gaps)):
        current_scene = scenes[current_idx]
        next_scene = scenes[next_idx]

        # Берем текст текущей сцены для анализа
        # LLM будет искать в нем скрытые заголовки сцен и разбивать текст
        text_to_split = current_scene['text']

        # Если текст пустой или очень короткий, пропускаем
        if not text_to_split or len(text_to_split.strip()) < 50:
            continue

        # Вызываем LLM для разбиения
        sub_scenes = _split_scene_with_llm(
            text_to_split,
            current_scene['id'],
            next_scene['id']
        )

        # Заменяем текущую сцену на разбитые под-сцены
        # Первая под-сцена заменяет текущую, остальные вставляются после
        if sub_scenes and len(sub_scenes) > 0:
            # Если LLM вернула только одну сцену с тем же ID, оставляем как есть
            if len(sub_scenes) == 1 and sub_scenes[0]['id'] == current_scene['id']:
                continue

            scenes[current_idx] = sub_scenes[0]
            # Вставляем остальные под-сцены после текущей
            for i, sub_scene in enumerate(sub_scenes[1:], start=1):
                scenes.insert(current_idx + i, sub_scene)

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