import os
from docx import Document
import fitz  # PyMuPDF
from typing import List, Dict, Any


class FileProcessor:
    """Класс для обработки загруженных файлов"""
    
    def __init__(self):
        pass
    
    def extract_text_from_docx(self, filepath: str) -> str:
        """Извлечение текста из DOCX файла"""
        doc = Document(filepath)
        text = []
        for paragraph in doc.paragraphs:
            text.append(paragraph.text)
        return '\n'.join(text)
    
    def extract_text_from_pdf(self, filepath: str, pages: List[int] = None) -> str:
        """Извлечение текста из PDF файла"""
        doc = fitz.open(filepath)
        text = []
        
        if pages:
            page_nums = pages
        else:
            page_nums = range(len(doc))
        
        for page_num in page_nums:
            if 0 <= page_num < len(doc):
                page = doc[page_num]
                text.append(page.get_text())
        
        doc.close()
        return '\n'.join(text)
    
    def process_preview(self, filepath: str, fields: List[str], pages: int = 2) -> Dict[str, Any]:
        """
        Обработка превью для указанного количества страниц.
        ВАЖНО: Пользователь должен реализовать свою логику обработки здесь.
        """
        file_ext = filepath.rsplit('.', 1)[1].lower()
        
        if file_ext == 'docx':
            # Для DOCX извлекаем первые параграфы (приблизительно как 2 страницы)
            text = self.extract_text_from_docx(filepath)
            # Разбиваем на части (приблизительно 2 страницы)
            lines = text.split('\n')
            preview_text = '\n'.join(lines[:100])  # Примерно 2 страницы
        else:  # PDF
            preview_text = self.extract_text_from_pdf(filepath, pages=list(range(min(pages, 2))))
        
        # ЗДЕСЬ ПОЛЬЗОВАТЕЛЬ ДОЛЖЕН ДОБАВИТЬ СВОЮ ЛОГИКУ ОБРАБОТКИ
        # Это пример структуры результата
        preview_result = {
            'pages_processed': pages,
            'fields': fields,
            'preview_data': self._apply_custom_logic(preview_text, fields)
        }
        
        return preview_result
    
    def process_file(self, filepath: str, fields: List[str], options: Dict = None) -> List[Dict[str, Any]]:
        """
        Обработка всего файла.
        ВАЖНО: Пользователь должен реализовать свою логику обработки здесь.
        """
        if options is None:
            options = {}
        
        file_ext = filepath.rsplit('.', 1)[1].lower()
        
        if file_ext == 'docx':
            text = self.extract_text_from_docx(filepath)
        else:  # PDF
            text = self.extract_text_from_pdf(filepath)
        
        # ЗДЕСЬ ПОЛЬЗОВАТЕЛЬ ДОЛЖЕН ДОБАВИТЬ СВОЮ ЛОГИКУ ОБРАБОТКИ
        # Это пример структуры результата
        processed_data = self._apply_custom_logic(text, fields, options)
        
        return processed_data
    
    def _apply_custom_logic(self, text: str, fields: List[str], options: Dict = None) -> List[Dict[str, Any]]:
        """
        Применение пользовательской логики обработки.
        ЭТОТ МЕТОД ДОЛЖЕН БЫТЬ ПЕРЕОПРЕДЕЛЕН ПОЛЬЗОВАТЕЛЕМ.
        
        По умолчанию возвращает примерную структуру данных.
        """
        # Пример: разбиваем текст на части и создаем записи
        # Пользователь должен заменить это на свою логику
        lines = text.split('\n')
        result = []
        
        for i, line in enumerate(lines):
            if line.strip():
                record = {'id': i + 1}
                for field in fields:
                    # Пример заполнения полей
                    record[field] = f"Значение для {field} из строки {i+1}"
                result.append(record)
        
        return result


