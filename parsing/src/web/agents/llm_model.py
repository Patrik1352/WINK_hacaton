"""
Модуль для инициализации и управления локальной LLM моделью.
Модель загружается в память при импорте модуля.
"""
from transformers import AutoModelForCausalLM, AutoTokenizer
from typing import Optional, Tuple
import torch


# Путь к локальной модели
# _model_name: str = "/home/yc-user/EGOR_DONT_ENTER/models/QVikhr-3-4B-Instruction"
_model_name: str = "/home/yc-user/EGOR_DONT_ENTER/models/avibe"

# Глобальные переменные для модели и токенизатора
_model: Optional[AutoModelForCausalLM] = None
_tokenizer: Optional[AutoTokenizer] = None


def init_model(model_path: Optional[str] = None) -> Tuple[AutoModelForCausalLM, AutoTokenizer]:
    """
    Инициализирует и загружает локальную модель в память.
    Модель загружается один раз и переиспользуется.
    
    Args:
        model_path: Путь к модели (если None, используется путь по умолчанию)
    
    Returns:
        Кортеж (модель, токенизатор)
    """
    global _model, _tokenizer, _model_name
    
    if _model is None or _tokenizer is None:
        if model_path:
            _model_name = model_path
        
        print(f"Загрузка модели из {_model_name}...")
        
        _model = AutoModelForCausalLM.from_pretrained(
            _model_name,
            torch_dtype=torch.bfloat16,
            device_map="auto"
        )
        
        _tokenizer = AutoTokenizer.from_pretrained(_model_name)
        
        print("Модель успешно загружена в память.")
    
    return _model, _tokenizer


def get_model() -> AutoModelForCausalLM:
    """
    Возвращает инициализированную модель.
    Если модель еще не инициализирована, загружает ее.
    
    Returns:
        Модель
    """
    if _model is None:
        init_model()
    return _model


def get_tokenizer() -> AutoTokenizer:
    """
    Возвращает инициализированный токенизатор.
    Если токенизатор еще не инициализирован, загружает его.
    
    Returns:
        Токенизатор
    """
    if _tokenizer is None:
        init_model()
    return _tokenizer


def get_model_path() -> str:
    """
    Возвращает путь к модели.
    
    Returns:
        Путь к модели
    """
    return _model_name


def call_llm(prompt: str, model: Optional[str] = None, max_new_tokens: int = 1024) -> str:
    """
    Вызывает локальную LLM с заданным промптом.
    
    Args:
        prompt: Текст запроса к LLM
        model: Путь к модели (если None, используется модель по умолчанию)
        max_new_tokens: Максимальное количество новых токенов для генерации
    
    Returns:
        Ответ от LLM
    """
    # Если указан другой путь к модели, перезагружаем
    if model and model != _model_name:
        global _model, _tokenizer
        _model = None
        _tokenizer = None
        init_model(model)
    
    llm_model = get_model()
    tokenizer = get_tokenizer()
    
    # Формируем сообщения для чат-шаблона
    messages = [
        {"role": "user", "content": prompt}
    ]
    
    # Применяем чат-шаблон
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )
    
    # Токенизируем входной текст
    model_inputs = tokenizer([text], return_tensors="pt").to(llm_model.device)
    
    # Генерируем ответ
    generated_ids = llm_model.generate(
        **model_inputs,
        max_new_tokens=max_new_tokens
    )
    
    # Извлекаем только новые токены (без входного промпта)
    generated_ids = [
        output_ids[len(input_ids):] 
        for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
    ]
    
    # Декодируем ответ
    response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
    
    return response


# Инициализируем модель при импорте модуля
init_model()

