# 📝 Инструкция по обновлению контента на сервере

Руководство по изменению текстов, заданий и загрузке медиа-файлов для курса The Language Escape.

---

## 🔐 Подключение к серверу

### Через SSH

```bash
ssh -p 49311 root@d2305931f6ab.vps.myjino.ru
# Пароль: 7PD+ZbGtDvSy
```

### Через VS Code Remote SSH

1. Установите расширение "Remote - SSH"
2. Добавьте в `~/.ssh/config`:

```
Host language-escape-bot
    HostName d2305931f6ab.vps.myjino.ru
    Port 49311
    User root
```

3. Connect to Host → language-escape-bot

---

## 📂 Структура файлов на сервере

```
/root/language_escape_bot/
├── materials/                          # Материалы курса
│   ├── videos/                        # Видео-брифинги
│   │   ├── day_01.mp4
│   │   ├── day_02.mp4
│   │   └── ...day_10.mp4
│   ├── briefs/                        # PDF-брифинги
│   │   ├── day_01.pdf
│   │   ├── day_02.pdf
│   │   └── ...day_10.pdf
│   ├── media/                         # Аудио и изображения для заданий
│   │   ├── task_01.mp3
│   │   ├── task_02.mp3
│   │   ├── image_01.jpg
│   │   └── ...
│   ├── day_01.json                    # Контент дня 1
│   ├── day_02.json                    # Контент дня 2
│   └── ...day_10.json                 # Контент дня 10
└── bot/                               # Код бота (не трогаем)
```

---

## 📝 Изменение текстов и заданий

### 1. Редактирование JSON файлов

#### Подключиться к серверу
```bash
ssh -p 49311 root@d2305931f6ab.vps.myjino.ru
```

#### Перейти в папку с материалами
```bash
cd /root/language_escape_bot/materials
```

#### Открыть нужный день для редактирования
```bash
nano day_02.json
# или используйте vim, если знакомы
vim day_02.json
```

### 2. Структура JSON файла

```json
{
  "day": 2,
  "title": "Identity Protocol - Who Are You?",
  "description": "Текст описания дня с [Имя] для подстановки имени пользователя",
  "video": "videos/day_02.mp4",
  "brief": "briefs/day_02.pdf",
  "code_letter": "I",
  "audio": [
    "media/task_02.mp3"
  ],
  "images": [],
  "tasks": [
    {
      "day": 2,
      "task_number": 1,
      "type": "choice",
      "title": "Название задания",
      "question": "Текст вопроса",
      "media": "",
      "options": [
        "A) Вариант 1",
        "B) Вариант 2",
        "C) Правильный вариант",
        "D) Вариант 4"
      ],
      "correct_answer": "C",
      "hints": [],
      "voice_keywords": [],
      "dialog_steps": []
    }
  ]
}
```

### 3. Типы заданий (type)

#### `choice` - Выбор из вариантов
```json
{
  "type": "choice",
  "question": "Вопрос",
  "options": ["A) Вариант 1", "B) Вариант 2", "C) Вариант 3", "D) Вариант 4"],
  "correct_answer": "C"
}
```

#### `audio` - Аудио с вариантами ответа
```json
{
  "type": "audio",
  "question": "Послушай и выбери правильный ответ",
  "media": "media/task_02.mp3",
  "options": ["A) Вариант 1", "B) Вариант 2", "C) Вариант 3", "D) Вариант 4"],
  "correct_answer": "A) Вариант 1"
}
```

#### `video` - Видео с вариантами ответа
```json
{
  "type": "video",
  "question": "Посмотри видео и ответь",
  "media": "media/task_video.mp4",
  "options": ["A) Вариант 1", "B) Вариант 2", "C) Вариант 3", "D) Вариант 4"],
  "correct_answer": "B"
}
```

#### `voice` - Голосовое задание
```json
{
  "type": "voice",
  "question": "Emma: \"Hi, [Имя]! Where are you from?\"\n\n🎤 Ответь голосом: \"I'm from [country]\"",
  "instruction": "Emma: \"Hi, [Имя]! Where are you from?\"",
  "voice_keywords": ["i'm from", "i am from", "from"],
  "hints": [
    "Say: I'm from [your country]",
    "Example: I'm from Russia",
    "Try again! Say: I'm from [country name]"
  ]
}
```

### 4. Сохранение изменений

#### В nano
- `Ctrl + O` → Enter (сохранить)
- `Ctrl + X` (выйти)

#### В vim
- `Esc` → `:wq` → Enter (сохранить и выйти)

### 5. Проверка JSON на ошибки

```bash
python3 -m json.tool day_02.json
# Если нет ошибок - выведет отформатированный JSON
# Если есть ошибки - покажет где проблема
```

### 6. Перезапуск бота (необязательно)

```bash
systemctl restart language-escape-bot
```

**Примечание:** Бот подгружает JSON файлы динамически, перезапуск нужен только при изменении структуры.

---

## 🎬 Загрузка медиа-файлов

### Метод 1: SCP (рекомендуется)

#### Загрузить видео-брифинг
```bash
# С локального компьютера
scp -P 49311 day_03.mp4 root@d2305931f6ab.vps.myjino.ru:/root/language_escape_bot/materials/videos/
```

#### Загрузить PDF-брифинг
```bash
scp -P 49311 day_03.pdf root@d2305931f6ab.vps.myjino.ru:/root/language_escape_bot/materials/briefs/
```

#### Загрузить аудио для задания
```bash
scp -P 49311 task_03.mp3 root@d2305931f6ab.vps.myjino.ru:/root/language_escape_bot/materials/media/
```

#### Загрузить изображение
```bash
scp -P 49311 image_03.jpg root@d2305931f6ab.vps.myjino.ru:/root/language_escape_bot/materials/media/
```

#### Загрузить несколько файлов сразу
```bash
scp -P 49311 *.mp4 root@d2305931f6ab.vps.myjino.ru:/root/language_escape_bot/materials/videos/
scp -P 49311 *.pdf root@d2305931f6ab.vps.myjino.ru:/root/language_escape_bot/materials/briefs/
scp -P 49311 *.mp3 root@d2305931f6ab.vps.myjino.ru:/root/language_escape_bot/materials/media/
```

### Метод 2: SFTP (графический интерфейс)

#### FileZilla
1. Открыть FileZilla
2. Сайт → Менеджер сайтов → Новый сайт
3. Параметры:
   - Протокол: SFTP
   - Хост: `d2305931f6ab.vps.myjino.ru`
   - Порт: `49311`
   - Тип входа: Нормальный
   - Пользователь: `root`
   - Пароль: `7PD+ZbGtDvSy`
4. Перейти в `/root/language_escape_bot/materials`
5. Перетащить файлы в нужную папку

#### WinSCP (Windows)
1. Открыть WinSCP
2. Создать новое подключение:
   - Протокол: SFTP
   - Имя хоста: `d2305931f6ab.vps.myjino.ru`
   - Порт: `49311`
   - Имя пользователя: `root`
   - Пароль: `7PD+ZbGtDvSy`
3. Подключиться
4. Перейти в `/root/language_escape_bot/materials`
5. Скопировать файлы

### Метод 3: Wget (загрузка из интернета)

#### На сервере
```bash
cd /root/language_escape_bot/materials/videos
wget https://example.com/day_04.mp4

cd /root/language_escape_bot/materials/media
wget https://example.com/task_04.mp3
```

---

## 🔧 Проверка загруженных файлов

### Проверить список файлов
```bash
# Видео
ls -lh /root/language_escape_bot/materials/videos/

# PDF
ls -lh /root/language_escape_bot/materials/briefs/

# Медиа
ls -lh /root/language_escape_bot/materials/media/
```

### Проверить размер файла
```bash
du -h /root/language_escape_bot/materials/videos/day_02.mp4
```

### Проверить права доступа
```bash
# Должно быть rw-r--r-- или 644
ls -l /root/language_escape_bot/materials/videos/day_02.mp4
```

### Если нужно исправить права
```bash
chmod 644 /root/language_escape_bot/materials/videos/day_02.mp4
```

---

## 📊 Примеры типичных изменений

### Пример 1: Изменить текст описания дня

```bash
# 1. Подключиться к серверу
ssh -p 49311 root@d2305931f6ab.vps.myjino.ru

# 2. Открыть файл
cd /root/language_escape_bot/materials
nano day_02.json

# 3. Найти строку "description" и изменить текст
# 4. Сохранить: Ctrl+O, Enter, Ctrl+X

# 5. Проверить JSON
python3 -m json.tool day_02.json
```

### Пример 2: Изменить вопрос в задании

```bash
# 1. Подключиться к серверу
ssh -p 49311 root@d2305931f6ab.vps.myjino.ru

# 2. Открыть файл
cd /root/language_escape_bot/materials
nano day_03.json

# 3. Найти нужное задание по task_number
# 4. Изменить поле "question"
# 5. Сохранить: Ctrl+O, Enter, Ctrl+X

# 6. Проверить JSON
python3 -m json.tool day_03.json
```

### Пример 3: Добавить новое аудио-задание

```bash
# 1. Загрузить MP3 файл на сервер
scp -P 49311 new_task.mp3 root@d2305931f6ab.vps.myjino.ru:/root/language_escape_bot/materials/media/

# 2. Подключиться к серверу
ssh -p 49311 root@d2305931f6ab.vps.myjino.ru

# 3. Открыть JSON файл дня
cd /root/language_escape_bot/materials
nano day_05.json

# 4. Добавить новое задание в массив "tasks"
# 5. Указать "media": "media/new_task.mp3"
# 6. Сохранить и проверить JSON
python3 -m json.tool day_05.json
```

### Пример 4: Заменить видео-брифинг

```bash
# 1. Загрузить новое видео
scp -P 49311 day_06_new.mp4 root@d2305931f6ab.vps.myjino.ru:/root/language_escape_bot/materials/videos/

# 2. Подключиться к серверу
ssh -p 49311 root@d2305931f6ab.vps.myjino.ru

# 3. Удалить старое видео и переименовать новое
cd /root/language_escape_bot/materials/videos
rm day_06.mp4
mv day_06_new.mp4 day_06.mp4

# 4. Проверить
ls -lh day_06.mp4
```

---

## 🎯 Важные замечания

### ⚠️ Подстановка имени пользователя

В текстах используйте `[Имя]` для автоматической подстановки имени:

```json
"description": "Привет, [Имя]! Сегодня тебе предстоит..."
"question": "Emma: \"Hi, [Имя]! How are you?\""
```

Бот автоматически заменит `[Имя]` на имя пользователя из голосового задания дня 1.

### ⚠️ Пути к файлам

Всегда используйте относительные пути от папки `materials/`:

```json
✅ "video": "videos/day_02.mp4"
✅ "media": "media/task_03.mp3"
❌ "video": "/root/language_escape_bot/materials/videos/day_02.mp4"
❌ "media": "task_03.mp3"
```

### ⚠️ Форматы медиа-файлов

- **Видео:** `.mp4` (H.264, до 50 MB рекомендуется)
- **Аудио:** `.mp3` или `.ogg` (до 20 MB)
- **Изображения:** `.jpg`, `.png` (до 10 MB)
- **PDF:** до 20 MB

### ⚠️ Именование файлов

Используйте понятные имена без пробелов и спецсимволов:

```
✅ day_03.mp4
✅ task_05_audio.mp3
✅ emma_question.mp3
❌ Day 3 Video.mp4
❌ аудио задание 5.mp3
❌ файл(1).mp3
```

### ⚠️ Проверка JSON

Всегда проверяйте JSON после редактирования:

```bash
python3 -m json.tool day_XX.json
```

Если есть ошибка, вы увидите строку с проблемой.

---

## 🔍 Отладка проблем

### Медиа-файл не отправляется

1. Проверьте путь в JSON:
```bash
cd /root/language_escape_bot/materials
cat day_02.json | grep "media\|video\|brief"
```

2. Проверьте существование файла:
```bash
ls -lh /root/language_escape_bot/materials/videos/day_02.mp4
```

3. Проверьте размер (Telegram лимиты):
```bash
du -h /root/language_escape_bot/materials/videos/day_02.mp4
```

### JSON не загружается

1. Проверьте синтаксис:
```bash
python3 -m json.tool day_02.json
```

2. Проверьте кодировку (должна быть UTF-8):
```bash
file -i day_02.json
```

3. Посмотрите логи бота:
```bash
journalctl -u language-escape-bot -n 50
```

### Текст отображается неправильно

1. Проверьте экранирование кавычек:
```json
✅ "description": "Она сказала: \"Привет!\""
❌ "description": "Она сказала: "Привет!""
```

2. Проверьте переносы строк в JSON:
```json
✅ "question": "Строка 1\n\nСтрока 2"
❌ "question": "Строка 1

Строка 2"
```

---

## 📞 Полезные команды

### Быстрый доступ

```bash
# Перейти в папку с материалами
cd /root/language_escape_bot/materials

# Редактировать день 2
nano day_02.json

# Посмотреть список видео
ls -lh videos/

# Посмотреть список аудио
ls -lh media/

# Проверить JSON
python3 -m json.tool day_02.json

# Перезапустить бота
systemctl restart language-escape-bot

# Посмотреть логи
journalctl -u language-escape-bot -f
```

### Backup перед изменениями

```bash
# Создать backup JSON
cp day_02.json day_02.json.backup

# Создать backup всех JSON
cp *.json ~/backups/

# Восстановить из backup
cp day_02.json.backup day_02.json
```

---

## ✅ Чеклист изменения контента

- [ ] Подключился к серверу
- [ ] Сделал backup файла перед изменением
- [ ] Внес изменения в JSON
- [ ] Проверил JSON на ошибки (`python3 -m json.tool`)
- [ ] Загрузил новые медиа-файлы (если нужно)
- [ ] Проверил пути к файлам в JSON
- [ ] Проверил размеры медиа-файлов
- [ ] Протестировал в боте (отправил команду)
- [ ] Проверил логи на ошибки

---

**Дата создания:** 2025-10-29
**Версия:** 1.0

🤖 *Этот файл создан для упрощения обновления контента курса*
