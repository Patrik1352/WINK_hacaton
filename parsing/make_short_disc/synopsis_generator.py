"""
Модуль для генерации коротких синопсисов сцен с использованием языковой модели.
"""

from transformers import AutoModelForCausalLM, AutoTokenizer
from typing import List, Union, Optional
import torch


class SynopsisGenerator:
    """Класс для генерации синопсисов сцен."""
    
    def __init__(
        self,
        model_name: str = "/home/yc-user/EGOR_DONT_ENTER/models/avibe",
        device_map: str = "auto",
        dtype: str = "auto"
    ):
        """
        Инициализация генератора синопсисов.
        
        Args:
            model_name: Путь к модели или название модели в HuggingFace
            device_map: Стратегия размещения модели на устройствах
            dtype: Тип данных для модели
        """
        self.model_name = model_name
        self.model = None
        self.tokenizer = None
        self.device_map = device_map
        self.dtype = dtype
        
    def load_model(self):
        """Загрузка модели и токенизатора."""
        print(f"Загрузка модели из {self.model_name}...")
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            dtype=self.dtype,
            device_map=self.device_map
        )
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        print("Модель загружена успешно!")
        
    def _create_prompt(
        self,
        screen_text: str,
        max_sentences: int = 3,
        max_chars: int = 200
    ) -> str:
        """
        Создание промпта для генерации синопсиса.
        
        Args:
            screen_text: Текст сцены
            max_sentences: Максимальное количество предложений в синопсисе
            max_chars: Максимальное количество символов в синопсисе
            
        Returns:
            Промпт для модели
        """
        prompt = f"""Твоя задача написать короткий синопсис по тесту сцены, который я передаю тебе. Длина синопсиса максимум может составлять {max_sentences} предложения, больше нельзя.
Синопсис должен хорошо и полно описывать происходящие в данной сцене. Примеры как нужно создавать синопсис:
- Пример 1:
    Сцена: 
    ```Мама АЛИСЫ обувается, берет шоппер. Алиса её провожает.
    
    МАМА АЛИСА
    Я сперва к Лауре на массаж, потом в магазин. Буду только к часам 9. 
    
    Мама Алисы выходит.
    
    МАМА АЛИСЫ
    А ты закройся хорошо. На два замка.
    
    Алиса выдыхает, мол иди уже. Закрывает за мамой дверь. Только выходит из кадра, как в дверь звонят. Идет открывать...
    
    АЛИСА
    Мам, ну что еще? Воду в доме перекрыть?
    
    …неожиданно в дверях стоит Антон.
    АНТОН
    Ну вы что? У нас через три минуты видеоконференция!
    Алиса – оценка.
    
    АЛИСА
    В смысле? С кем?
    АНТОН
    Вы что, и сообщения не читали? Трубку тоже не берёте… Войти можно?
    Растерянная Алиса впускает Антона.```
    Синопсис:
    ```Алиса провожает маму в магазин, приходит Антон```

- Пример 2:
    Сцена: 
    ```Стёпа с мамой садятся за столом в Бургерной. Здесь везде американская символика – висит флаг США и т. п.
    МАМА МАССЫ
    Я не пойму, мы дома не могли поесть, что ты меня в эту забегаловку притащил?
    Стёпа кладёт на стол корвалол, валидол.
    СТЕПА
    Ну и это на всякий случай…
    Ставит маленькую бутылочку коньяку.
    МАМА МАССЫ
    Это чё, Степ? Выглядит как наследство твоего отца…
    СТЕПА
    Это чтобы тебе плохо не стало. Вон, смотри.
    Мама Массы видит, как к ней идёт постаревший Масса (в гриме). Он в деловом костюме, пальто, в очках для зрения. Мама Массы встаёт и бежит к нему в объятия.
    МАМА МАССЫ
    Сынок! Родной мой…
    Мама Массы обнимает его. Масса зажмурил глаза, чтобы не проронить слезу, и не повредить грим. Стёпа откровенно утирает глаза.
    СКЛЕЙКА
    Масса очень быстро ест, будто никогда в жизни не ел. Весь стол в пустых упаковках от бургеров, картошки фри, соусов. Мама наблюдает за Массой.
    МАМА МАССЫ
    Ты что в своей Америке голодал?
    МАССА
    (жуя)
    Да не мам, я ж ем еду только для богачей, а по нищебродской соскучился. А дома времени готовить нет, сама понимаешь, дела-дела… То Клинтону позвонить надо, то ещё кому-нибудь.
    Стёпа от такого вранья поперхнулся кофе. Мама в шоке от рассказов.
    МАМА МАССЫ
    А мне? Почему ты мне ни разу не позвонил?!
    МАССА
    Так это, дорого. Америка всё-таки! Межгород!
    (Стёпе)
    Брат, сгоняй ещё пару гамбургеров возьми.
    СТЁПА
    (шёпотом недовольно)
    Слышь, мы – русские, пендосов не кормим!
    МАССА
    Блин, тебе чё жалко? У меня просто всё в баксах.
    МАМА МАССЫ
    (Стёпе)
    Имей совесть!
    (даёт подзатыльник Стёпе)
    К тебе брат из Америки приехал! Кушай, Олежа, кушай!
    Стёпа открывает кошелёк – там осталась пара сотенных купюр.
    СТЁПА
    Так всё! Олегу надо в аэропорт, у него завтра в Нью-Йорке важная встреча!
    МАМА МАССЫ
    Как?! Уже?! Ну я же так соскучилась! Даже пирожками не накормила!
    МАССА
    Да Стёпа, может, я отложу встречу?
    СТЁПА
    (злится)
    Ты говорил, важная встреча! Не улетишь в срок, визы не продлят!
    МАССА
    (загрустил)
    Ну точно… Надо ехать… Пойдём к машине мам, проводишь.```
    Синопсис:
    ```Стёпа с мамой садятся за столом в Бургерной. Мама Массы видит, как к ней идёт постаревший Масса (в гриме).```

- Пример 3:
    Сцена: 
    ```НАБАТОВ, ПЕТЬКА-МЕХАНИК, ГОРЕЛОВ

    Набатов и Петька играют в шахматы. Перед Петькой миска с рагу. За его спиной ненавязчиво мельтешит Горелов. 
    
    НАБАТОВ
    У тебя есть мечта, Петь? 
    
    ПЕТЬКА-МЕХАНИК
    Я ж говорил уже: ботиночки, и на танцы. 
    
    Он съедает очередную набатовскую фигуру. Набатов съедает ответно: обмен. 
    
    НАБАТОВ
    Я о большой мечте. Не может ее не быть у человека. 
    
    Набатов смотрит на рагу, кусает губы. Они уйдут, а Петька останется. Ему неуютно от этой мысли. 
    
    Горелов суетится чуть поодаль.
    
    ПЕТЬКА-МЕХАНИК
    Ну, эта, есть одна. Только ты не говори никому. 
    
    Он осматривается по сторонам. Горелов мутит что-то с лекарствами. Набатов жестами показывает Петьке: мол, я - могила. 
    
    ПЕТЬКА-МЕХАНИК
    Банджо. 
    
    НАБАТОВ
    Банджо? 
    
    ПЕТЬКА-МЕХАНИК
    Я не только танцую. Еще на банджо играю. Нэпман один обучил. И вот мечта, раз уж спросил… 
    
    Он через боль приподнимается на локте, манит Набатова к себе: "дай шепну". Набатов наклоняется к нему. 
    ПЕТЬКА-МЕХАНИК
    Я у Утесова в ансамбле играть хочу. 
    
    Это доверие высшего уровня. Глаза Набатова наполняются слезами. 
    
    Подходит Горелов. В его руках несколько ампул. 
    
    ГОРЕЛОВ
    Ну что, Петр? Уколы себе умеешь ставить? 
    
    ПЕТЬКА-МЕХАНИК
    Дак кто ж не умеет-то? А вы чего спрашиваете: тоже загрипповали? 
    
    Петька доедает рагу, отодвигает миску. Горелов крутит перед его глазами ампулы, чтоб тот запомнил.
    
    ГОРЕЛОВ
    Морфий, Петя.
    
    Кладет ампулы ему под подушку, чтобы тот видел и запомнил. 
    
    ПЕТЬКА-МЕХАНИК
    Морфий? 
    
    Петька готов удивиться, но снотворное действует, и он отключается. 
    
    Набатов смотрит на ампулы. И запоздало понимает: Горелов тоже в сговоре, он собирается уйти из лагеря и оставить Петьку.
    
    НАБАТОВ
    Зачем ему морфий? Вы… Черт. Вы тоже?
    
    Горелов, поняв, что Петька уснул, цинично собирает свои вещи. 
    
    Набатов вскакивает, хватает его за грудки, гвоздит к столбу.
    
    НАБАТОВ 
    Вы не можете! Он же… 
    
    ГОРЕЛОВ
    Сейчас болезнь подавлена вакциной, но, когда бешенство проснется... ты представляешь, как это больно? Гангрена там будет. Не жилец. 
    
    НАБАТОВ
    Вы что… больного бросаете? 
    
    ГОРЕЛОВ
    Так и ты ж тоже, Набатов. У меня сын родился, а жена умерла. Я ребенку своему осиротеть не дам. 
    
    Он сбрасывает руки Набатова. Тот и сам уже ослабил хватку: поверил, впечатлен. 
    ```
    Синопсис:
    ```Горелов подмешивает снотворное в чай. Петька пьет и засыпает. Набатов е выпил чай. Горелов набрасывается на Набатова с тряпкой со снотворным. Но Набатов уворачивается и сам усыпляет Горелова.```


Для данной сцены напиши синопсис:
    Сцена:
    ```{screen_text}```


Повторяю условия, синопсис должен быть:
- краток, максимум {max_sentences} предложения
- полон, максимально полно описать действие в сцене
- должно быть максимум {max_chars} символов
"""
        return prompt
    
    def generate_single(
        self,
        screen_text: str,
        max_sentences: int = 3,
        max_chars: int = 200,
        max_new_tokens: int = 256,
        do_sample: bool = False
    ) -> str:
        """
        Генерация синопсиса для одной сцены.
        
        Args:
            screen_text: Текст сцены
            max_sentences: Максимальное количество предложений в синопсисе
            max_chars: Максимальное количество символов в синопсисе
            max_new_tokens: Максимальное количество новых токенов для генерации
            do_sample: Использовать ли сэмплирование при генерации
            
        Returns:
            Сгенерированный синопсис
        """
        if self.model is None or self.tokenizer is None:
            raise RuntimeError("Модель не загружена. Вызовите load_model() сначала.")
        
        prompt = self._create_prompt(screen_text, max_sentences, max_chars)
        
        messages = [{"role": "user", "content": prompt}]
        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        model_inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)
        
        generated_ids = self.model.generate(
            **model_inputs,
            max_new_tokens=max_new_tokens,
            do_sample=do_sample,
            pad_token_id=self.tokenizer.eos_token_id
        )
        
        # Вырезаем только сгенерированные токены
        generated_ids_trimmed = [
            output_ids[len(input_ids):] 
            for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]
        
        response = self.tokenizer.batch_decode(
            generated_ids_trimmed, 
            skip_special_tokens=True
        )[0]
        
        return response

    def generate_multiple_in_one_prompt(
        self,
        screen_texts: List[str],
        max_sentences: int = 2,
        max_chars: int = 100,
        max_new_tokens: int = 512,
        do_sample: bool = False
    ) -> List[str]:
        if self.model is None or self.tokenizer is None:
            raise RuntimeError("Модель не загружена. Вызовите load_model() сначала.")

        # --- 1. Формируем общий промпт ---
        scenes_block = ""
        for i, scene in enumerate(screen_texts, start=1):
            scenes_block += f"СЦЕНА {i}:\n```\n{scene}\n```\n\n"

        prompt = f"""
Ты — помощник-сценарист. Вот несколько сцен. 
Для КАЖДОЙ сцены напиши краткий синопсис с условиями:
- максимум {max_sentences} предложения
- максимум {max_chars} символов
- описывать действие полно и точно
- не должно быть повторов
Что не нужно указывать:
- время суток, место действия НЕ нужно указывать

Ответ верни строго в формате:

СИНОПСИС 1: <текст>
СИНОПСИС 2: <текст>
...

Вот сцены:
{scenes_block}
"""

        messages = [{"role": "user", "content": prompt}]
        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )

        model_inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)

        generated_ids = self.model.generate(
            **model_inputs,
            max_new_tokens=max_new_tokens,
            do_sample=do_sample,
            pad_token_id=self.tokenizer.eos_token_id
        )

        # Обрезаем только новую часть
        generated_ids_trimmed = [
            output_ids[len(input_ids):]
            for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]

        response = self.tokenizer.batch_decode(
            generated_ids_trimmed,
            skip_special_tokens=True
        )[0]

        # --- 2. Парсим ответ ---
        synopses = []
        current = None

        for line in response.splitlines():
            line = line.strip()
            if line.startswith("СИНОПСИС"):
                # новая запись
                if current is not None:
                    synopses.append(current.strip())
                current = line.split(":", 1)[1].strip()
            else:
                if current is not None and line:
                    current += " " + line

        if current:
            synopses.append(current.strip())

        # Если модель прислала меньше синопсисов, добиваем пустыми
        while len(synopses) < len(screen_texts):
            synopses.append("")

        return synopses

    
    def generate_batch(
        self,
        screen_texts: List[str],
        max_sentences: int = 3,
        max_chars: int = 200,
        max_new_tokens: int = 256,
        do_sample: bool = True,
        batch_size: Optional[int] = None
    ) -> List[str]:
        """
        Генерация синопсисов для нескольких сцен (батч-обработка).
        
        Args:
            screen_texts: Список текстов сцен
            max_sentences: Максимальное количество предложений в синопсисе
            max_chars: Максимальное количество символов в синопсисе
            max_new_tokens: Максимальное количество новых токенов для генерации
            do_sample: Использовать ли сэмплирование при генерации
            batch_size: Размер батча (если None, обрабатывает все сразу)
            
        Returns:
            Список сгенерированных синопсисов
        """
        if self.model is None or self.tokenizer is None:
            raise RuntimeError("Модель не загружена. Вызовите load_model() сначала.")
        
        # Подготовка промптов
        texts = []
        for screen_text in screen_texts:
            prompt = self._create_prompt(screen_text, max_sentences, max_chars)
            messages = [{"role": "user", "content": prompt}]
            text = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
            texts.append(text)
        
        # Обработка батчами или все сразу
        all_responses = []
        
        if batch_size is None:
            # Обрабатываем все сразу
            batches = [texts]
        else:
            # Разбиваем на батчи
            batches = [texts[i:i + batch_size] for i in range(0, len(texts), batch_size)]
        
        for batch_texts in batches:
            model_inputs = self.tokenizer(
                batch_texts,
                return_tensors="pt",
                padding=True,
                truncation=True
            ).to(self.model.device)
            
            generated_ids = self.model.generate(
                **model_inputs,
                max_new_tokens=max_new_tokens,
                do_sample=do_sample,
                pad_token_id=self.tokenizer.eos_token_id
            )
            
            # Вырезаем только сгенерированные токены
            generated_ids_trimmed = [
                output_ids[len(input_ids):] 
                for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
            ]
            
            responses = self.tokenizer.batch_decode(
                generated_ids_trimmed, 
                skip_special_tokens=True
            )
            
            all_responses.extend(responses)
        
        return all_responses

def unload_model(self):
    """Полностью выгружает модель и освобождает занятую VRAM."""
    try:
        # Удаляем объекты модели и токенизатора
        if self.model is not None:
            del self.model
            self.model = None

        if self.tokenizer is not None:
            del self.tokenizer
            self.tokenizer = None

        # Явная сборка мусора
        import gc
        gc.collect()

        # Очистка CUDA памяти
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()

        print("Модель успешно выгружена из памяти, VRAM освобождена.")

    except Exception as e:
        print(f"Ошибка при выгрузке модели: {e}")


# Пример использования
if __name__ == "__main__":
    # Инициализация генератора
    generator = SynopsisGenerator()
    generator.load_model()
    
    # Пример для одной сцены
    screen_text = """Митя и Ариша разговаривают с сотрудницей ЗАГСа.

РАБОТНИЦА ЗАГСА 1
Люда, тут на брак подошли. Несовершеннолетние!

Митя и Арина переглядываются.

МИТЯ
Нет-нет, вы не так поняли.

АРИНА
Я по другому вопросу."""
    
    synopsis = generator.generate_single(screen_text)
    print("Синопсис:", synopsis)
    
    # Пример для нескольких сцен
    screen_texts = [screen_text, screen_text]  # Пример с одинаковыми текстами
    synopses = generator.generate_batch(screen_texts, batch_size=10)
    print("\nСинопсисы:", synopses)

