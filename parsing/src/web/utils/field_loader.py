import os
import json
from typing import List, Dict
# from config import


class FieldLoader:
    """Класс для загрузки полей из файла"""
    
    def __init__(self, default_fields_file: str = None):
        if default_fields_file is None:
            # Путь относительно корня проекта
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            default_fields_file = os.path.join(project_root, 'data', 'fields.json')
        
        self.default_fields_file = default_fields_file
    
    def load_default_fields(self) -> List[Dict[str, str]]:
        """
        Загрузка полей по умолчанию из файла.
        Если файл не существует, возвращает стандартный набор полей.
        """
        if os.path.exists(self.default_fields_file):
            try:
                with open(self.default_fields_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
                    elif isinstance(data, dict) and 'fields' in data:
                        return data['fields']
            except Exception as e:
                print(f"Ошибка при загрузке полей: {e}")
        
        # Возвращаем стандартный набор полей, если файл не найден
        return [
            {'id': 'id', 'name': 'ID', 'type': 'number'},
            {'id': 'title', 'name': 'Заголовок', 'type': 'text'},
            {'id': 'text', 'name': 'Текст', 'type': 'text'},
            {'id': 'date', 'name': 'Дата', 'type': 'date'},
            {'id': 'author', 'name': 'Автор', 'type': 'text'}
        ]
    
    def save_fields(self, fields: List[Dict[str, str]], filepath: str = None):
        """Сохранение полей в файл"""
        if filepath is None:
            filepath = self.default_fields_file
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(fields, f, ensure_ascii=False, indent=2)


