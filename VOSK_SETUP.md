# Настройка Vosk для распознавания речи

## Описание

Vosk - это оффлайн система распознавания речи с открытым исходным кодом. Используется в боте для проверки голосового задания Day 1: "My name is [Name]".

---

## 🔧 Системные требования

### 1. Установка ffmpeg (для конвертации аудио)

```bash
# На сервере
sudo apt-get update
sudo apt-get install -y ffmpeg

# Проверка
ffmpeg -version
```

### 2. Установка Vosk

Vosk уже добавлен в `requirements.txt`:

```bash
pip install vosk
```

---

## 📥 Скачивание модели Vosk

### Рекомендуемая модель для английского языка

**vosk-model-small-en-us-0.15** (~40 MB) - оптимальная для распознавания коротких фраз

```bash
# Создать директорию для моделей
sudo mkdir -p /usr/local/share/vosk-models

# Скачать модель
cd /tmp
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip

# Распаковать
unzip vosk-model-small-en-us-0.15.zip

# Переместить в системную директорию
sudo mv vosk-model-small-en-us-0.15 /usr/local/share/vosk-models/

# Проверить
ls -la /usr/local/share/vosk-models/vosk-model-small-en-us-0.15
```

### Альтернативные модели

Если нужна более высокая точность (но больше размер):

- **vosk-model-en-us-0.22** (~1.8 GB) - высокая точность
- **vosk-model-en-us-0.22-lgraph** (~128 MB) - баланс точность/размер

Скачать с: https://alphacephei.com/vosk/models

---

## ⚙️ Конфигурация в .env

Добавьте в `.env` (опционально, если модель в другом месте):

```env
# Vosk Model Path (по умолчанию: /usr/local/share/vosk-models/vosk-model-small-en-us-0.15)
VOSK_MODEL_PATH=/usr/local/share/vosk-models/vosk-model-small-en-us-0.15
```

---

## 🧪 Тестирование

### 1. Проверка установки ffmpeg

```bash
ffmpeg -version
```

### 2. Проверка модели Vosk

```bash
ls -la /usr/local/share/vosk-models/vosk-model-small-en-us-0.15
```

Должны быть файлы:
- `am/` - акустическая модель
- `graph/` - языковая модель
- `conf/` - конфигурация

### 3. Тестирование в Python

```python
from vosk import Model

model_path = "/usr/local/share/vosk-models/vosk-model-small-en-us-0.15"
model = Model(model_path)
print("Vosk model loaded successfully!")
```

---

## 🎯 Как работает в боте

### Процесс распознавания голоса

1. **Получение голосового сообщения** (OGG/OPUS от Telegram)
2. **Скачивание** во временный файл
3. **Конвертация** OGG → WAV (16kHz, mono) через ffmpeg
4. **Распознавание** текста через Vosk
5. **Проверка фразы** "My name is"
6. **Извлечение имени** через regex
7. **Сохранение** имени в БД (user.first_name)

### Код (bot/services/speech_recognition.py)

```python
from bot.services.speech_recognition import speech_service

# Распознать голос
text, name, has_phrase = await speech_service.process_voice_message('/path/to/audio.ogg')

if has_phrase and name:
    print(f"Recognized: {text}")
    print(f"Name: {name}")
```

---

## 🔍 Поддерживаемые паттерны

Сервис распознает следующие варианты:

- `my name is John`
- `my names John`
- `name is John`
- `i am John`

Имя автоматически капитализируется: `john` → `John`

---

## 📊 Точность распознавания

### Факторы, влияющие на точность:

✅ **Хорошо распознается:**
- Четкая речь без акцента
- Тихий фон
- Правильное произношение

❌ **Плохо распознается:**
- Сильный акцент
- Фоновый шум
- Быстрая/невнятная речь
- Слишком тихая запись

### Советы пользователям (показываются в боте):

> 1. Говори четко и медленно
> 2. Убедись, что произносишь фразу полностью
> 3. Уменьши фоновый шум

---

## 🐛 Возможные ошибки

### Ошибка: "Vosk model not found"

```bash
# Проверить путь к модели
ls /usr/local/share/vosk-models/vosk-model-small-en-us-0.15

# Если не существует - скачать заново
cd /tmp
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
sudo mv vosk-model-small-en-us-0.15 /usr/local/share/vosk-models/
```

### Ошибка: "ffmpeg not found"

```bash
sudo apt-get install -y ffmpeg
```

### Ошибка: "Audio must be WAV format mono PCM, 16kHz"

Это означает, что конвертация через ffmpeg не сработала. Проверьте:

```bash
ffmpeg -i input.ogg -ar 16000 -ac 1 output.wav
```

---

## 📝 Логирование

Все действия логируются:

```
INFO: Transcribed: my name is john
INFO: Extracted name: John
INFO: Successfully extracted name 'John' from voice message (user 123456)
```

Для отладки:

```
WARNING: Could not extract name from: hello there
WARNING: Voice recognition failed for user 123456
```

---

## 🚀 Деплой на VPS

### Полная последовательность команд

```bash
# 1. Подключиться к VPS
ssh -p 49311 root@d2305931f6ab.vps.myjino.ru

# 2. Установить ffmpeg
apt-get update
apt-get install -y ffmpeg

# 3. Скачать Vosk модель
mkdir -p /usr/local/share/vosk-models
cd /tmp
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
mv vosk-model-small-en-us-0.15 /usr/local/share/vosk-models/

# 4. Обновить зависимости
cd /root/language_escape_bot
source venv/bin/activate
pip install vosk

# 5. Перезапустить бота
systemctl restart language-escape-bot

# 6. Проверить логи
journalctl -u language-escape-bot -f
```

---

## ✅ Чеклист готовности

- [ ] ffmpeg установлен (`ffmpeg -version`)
- [ ] Vosk модель скачана и распакована
- [ ] Путь к модели правильный в .env (или используется default)
- [ ] Vosk установлен через pip (`pip show vosk`)
- [ ] Бот перезапущен
- [ ] Тестирование: отправлен голос с фразой "My name is John"
- [ ] Имя сохранилось в БД (user.first_name)

---

**Дата создания:** 2025-10-24
**Статус:** ✅ Готово к тестированию
**Модель:** vosk-model-small-en-us-0.15 (40 MB)
