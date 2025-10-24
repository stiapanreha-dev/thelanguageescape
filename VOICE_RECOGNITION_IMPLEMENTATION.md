# Реализация распознавания голоса через Vosk

## 📋 Обзор

Реализована система распознавания голосовых сообщений для голосового задания Day 1: "My name is [Name]".

**Дата:** 2025-10-24
**Статус:** ✅ Готово к тестированию

---

## 🎯 Что было сделано

### 1. Создан сервис распознавания речи

**Файл:** `bot/services/speech_recognition.py`

**Основные возможности:**
- Конвертация OGG (Telegram) → WAV (16kHz, mono) через ffmpeg
- Распознавание речи через Vosk (оффлайн)
- Извлечение имени из фразы "My name is [Name]"
- Поддержка нескольких вариантов фразы

**Методы:**

```python
class SpeechRecognitionService:
    async def transcribe_audio(file_path: str) -> Optional[str]
        # Распознает аудио файл в текст

    async def _convert_to_wav(input_file: str) -> Optional[str]
        # Конвертирует OGG/OPUS в WAV через ffmpeg

    def extract_name_from_text(text: str) -> Optional[str]
        # Извлекает имя из распознанного текста

    def check_phrase(text: str, phrase: str) -> bool
        # Проверяет наличие фразы в тексте

    async def process_voice_message(file_path: str) -> Tuple[str, str, bool]
        # Полная обработка: возвращает (текст, имя, есть_фраза)
```

**Поддерживаемые паттерны:**
- `my name is John` ✅
- `my names John` ✅
- `name is John` ✅
- `i am John` ✅

### 2. Интегрировано в обработчик голосовых сообщений

**Файл:** `bot/handlers/tasks.py` (функция `handle_voice_message`)

**Процесс обработки:**

1. ✅ Получение голосового сообщения от пользователя
2. ✅ Показ сообщения "🎧 Обрабатываю голосовое сообщение..."
3. ✅ Скачивание OGG файла во временную директорию
4. ✅ Конвертация OGG → WAV (16kHz, mono)
5. ✅ Распознавание текста через Vosk
6. ✅ Проверка наличия фразы "My name is"
7. ✅ Извлечение имени через regex
8. ✅ Сохранение имени в `user.first_name`
9. ✅ Удаление временных файлов
10. ✅ Показ результата пользователю

**Сообщения об ошибках:**

```markdown
❌ **Не удалось распознать речь**

Попробуй еще раз:
1. Говори четко и медленно
2. Убедись, что произносишь фразу полностью
3. Уменьши фоновый шум
```

```markdown
❌ **Фраза 'My name is' не обнаружена**

Я услышал: _hello there_

Пожалуйста, произнеси фразу **'My name is [твоё имя]'**
```

```markdown
❌ **Не удалось извлечь имя**

Я услышал: _my name is_

Убедись, что после 'My name is' произносишь свое имя
```

**Сообщение об успехе:**

```markdown
✅ **Отлично, John!**

Ты успешно прошёл голосовое задание.

🔑 **Фрагмент кода:** `L` (если это последнее задание дня)
```

### 3. Добавлены зависимости

**Файл:** `requirements.txt`

```
vosk==0.3.45                    # Распознавание речи (уже было)
pydub==0.25.1                   # Обработка аудио (уже было)
# Note: ffmpeg must be installed system-wide for audio conversion
```

### 4. Создана документация

**Файлы:**
- `VOSK_SETUP.md` - Полная инструкция по настройке Vosk на сервере
- `VOICE_RECOGNITION_IMPLEMENTATION.md` - Этот файл (обзор реализации)

---

## 🔧 Настройка на сервере

### Системные требования

```bash
# 1. Установить ffmpeg
sudo apt-get update
sudo apt-get install -y ffmpeg

# 2. Скачать Vosk модель (~40 MB)
sudo mkdir -p /usr/local/share/vosk-models
cd /tmp
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
sudo mv vosk-model-small-en-us-0.15 /usr/local/share/vosk-models/

# 3. Установить Python зависимости
pip install vosk

# 4. Перезапустить бота
systemctl restart language-escape-bot
```

### Переменные окружения (опционально)

```env
# По умолчанию: /usr/local/share/vosk-models/vosk-model-small-en-us-0.15
VOSK_MODEL_PATH=/usr/local/share/vosk-models/vosk-model-small-en-us-0.15
```

---

## 🧪 Тестирование

### Локальное тестирование

1. ✅ Запустить бота локально: `./run_local.sh`
2. ✅ Начать Day 1 задания
3. ✅ Пройти задание #1 (выбор ответа)
4. ✅ Отправить голосовое сообщение с фразой "My name is John"
5. ✅ Проверить, что:
   - Текст распознан
   - Имя извлечено
   - Имя сохранено в БД
   - Показано сообщение успеха с именем
   - Переход к следующему заданию

### Проверка в БД

```sql
-- Проверить, что имя сохранилось
SELECT telegram_id, first_name, username FROM users WHERE telegram_id = 120962578;

-- Проверить распознанный текст в результате задания
SELECT recognized_text FROM task_results
WHERE user_id = (SELECT id FROM users WHERE telegram_id = 120962578)
  AND day_number = 1
  AND task_number = 2;
```

### Логи

```bash
# Успешное распознавание
INFO: Transcribed: my name is john
INFO: Extracted name: John
INFO: Successfully extracted name 'John' from voice message (user 120962578)
INFO: Voice message from user 120962578, duration: 3s, name: John, accepted

# Ошибки распознавания
WARNING: Could not extract name from: hello there
WARNING: Voice recognition failed for user 120962578
```

---

## 📊 Поток данных

```
[Telegram Voice Message (OGG)]
           ↓
[Download to temp file]
           ↓
[FFmpeg: OGG → WAV (16kHz, mono)]
           ↓
[Vosk: WAV → Text]
           ↓
[Regex: Extract name from text]
           ↓
[Save to DB: user.first_name]
           ↓
[Save task result: recognized_text]
           ↓
[Show success message with name]
           ↓
[Auto-transition to next task]
```

---

## 🔍 Детали реализации

### Конвертация аудио (FFmpeg)

```python
cmd = [
    'ffmpeg',
    '-i', input_file,      # Входной OGG
    '-ar', '16000',        # Sample rate: 16kHz
    '-ac', '1',            # Channels: mono
    '-y',                  # Overwrite
    output_file            # Выходной WAV
]
```

### Распознавание (Vosk)

```python
from vosk import Model, KaldiRecognizer
import wave

model = Model(model_path)
wf = wave.open(wav_path, "rb")
rec = KaldiRecognizer(model, wf.getframerate())

while True:
    data = wf.readframes(4000)
    if len(data) == 0:
        break
    if rec.AcceptWaveform(data):
        result = json.loads(rec.Result())
        text = result.get('text', '')
```

### Извлечение имени (Regex)

```python
patterns = [
    r'my\s+names?\s+is\s+([a-zA-Z]+)',  # my name is John
    r'my\s+names?\s+([a-zA-Z]+)',       # my names John
    r'name\s+is\s+([a-zA-Z]+)',         # name is John
    r'i\s+am\s+([a-zA-Z]+)',            # i am John
]

for pattern in patterns:
    match = re.search(pattern, text.lower())
    if match:
        name = match.group(1).capitalize()
        return name
```

---

## 🎨 Пользовательский опыт

### Сценарий успеха

1. **Пользователь:** Отправляет голос "My name is Alex"
2. **Бот:** 🎧 Обрабатываю голосовое сообщение...
3. **Бот:** ✅ **Отлично, Alex!** Ты успешно прошёл голосовое задание.
4. **Бот:** [Показывает следующее задание]

### Сценарий ошибки #1: Фраза не распознана

1. **Пользователь:** Отправляет голос "Hello there"
2. **Бот:** 🎧 Обрабатываю голосовое сообщение...
3. **Бот:** ❌ **Фраза 'My name is' не обнаружена**
   - Я услышал: _hello there_
   - Пожалуйста, произнеси фразу **'My name is [твоё имя]'**

### Сценарий ошибки #2: Имя не извлечено

1. **Пользователь:** Отправляет голос (невнятно) "My name is..."
2. **Бот:** 🎧 Обрабатываю голосовое сообщение...
3. **Бот:** ❌ **Не удалось извлечь имя**
   - Я услышал: _my name is_
   - Убедись, что после 'My name is' произносишь свое имя

---

## 📝 Использование имени в дальнейших заданиях

После успешного извлечения имени, оно сохраняется в `user.first_name` и может использоваться:

### В текущем дне:

```python
user = await session.get(User, telegram_id=user_id)
user_name = user.first_name or "Субъект X"

# В сообщениях
success_text = f"✅ **Отлично, {user_name}!**"
```

### В следующих днях:

Имя автоматически подставляется вместо `[Имя]` во всех заданиях и сообщениях курса.

**Примеры:**
- `"Привет, [Имя]!"` → `"Привет, Alex!"`
- `"Отличная работа, [Имя]"` → `"Отличная работа, Alex"`

---

## 🐛 Известные ограничения

### Точность распознавания

**Хорошо работает:**
- ✅ Четкая речь
- ✅ Английские имена (John, Alex, Maria)
- ✅ Тихий фон
- ✅ Нормальная громкость

**Плохо работает:**
- ❌ Сильный акцент
- ❌ Фоновый шум
- ❌ Нестандартные имена
- ❌ Очень тихая/громкая запись

### Модель Vosk

**vosk-model-small-en-us-0.15** (40 MB):
- ✅ Быстрая работа
- ✅ Малый размер
- ⚠️ Средняя точность для коротких фраз

Для улучшения точности можно использовать:
- **vosk-model-en-us-0.22-lgraph** (128 MB) - лучше
- **vosk-model-en-us-0.22** (1.8 GB) - максимальная точность

---

## ✅ Чеклист готовности к продакшену

**Локальная разработка:**
- [x] Сервис speech_recognition.py создан
- [x] Интеграция в handle_voice_message
- [x] Обработка всех ошибок
- [x] Сохранение имени в БД
- [x] Логирование всех действий
- [x] Временные файлы удаляются

**Серверная настройка:**
- [ ] ffmpeg установлен на VPS
- [ ] Vosk модель скачана на VPS
- [ ] Vosk установлен через pip
- [ ] Бот перезапущен
- [ ] Протестировано с реальным голосом
- [ ] Проверены логи на ошибки
- [ ] Проверено сохранение имени в БД

**Документация:**
- [x] VOSK_SETUP.md создан
- [x] VOICE_RECOGNITION_IMPLEMENTATION.md создан
- [x] CLAUDE.md обновлён

---

## 🚀 Следующие шаги

1. **Настроить Vosk на VPS** (см. VOSK_SETUP.md)
2. **Протестировать с реальными голосовыми сообщениями**
3. **Проверить распознавание разных акцентов**
4. **Собрать статистику точности распознавания**
5. **При необходимости - переключиться на более крупную модель**

---

## 📚 Ссылки

- **Vosk Models:** https://alphacephei.com/vosk/models
- **Vosk Documentation:** https://alphacephei.com/vosk/
- **FFmpeg Documentation:** https://ffmpeg.org/documentation.html

---

**Автор:** Claude Code
**Дата:** 2025-10-24
**Версия:** 1.0
**Статус:** ✅ Реализовано и готово к тестированию
