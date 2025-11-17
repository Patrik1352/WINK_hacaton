import sys
sys.path.append("../")
from agents.md_scene_agent import _default_parse_scenes
import json

def markdown_to_scenes(markdown_text: str, output_path: str):
    """
    Преобразует текст в markdown в список сцен и сохраняет в файл
    """
    scenes = _default_parse_scenes(markdown_text)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(scenes, f, ensure_ascii=False, indent=4)

    return scenes