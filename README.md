# The Language Escape Bot

Telegram-бот для 10-дневного киберпанк-квеста по изучению английского языка.

## 📋 Описание

**The Language Escape** - интерактивный курс английского языка (уровень A1-A2) в формате киберпанк-квеста. Пользователи проходят 10 дней обучения через видео, брифы и интерактивные задания.

## 🎯 Основные возможности

- Монетизация через YooKassa (999 руб.)
- Последовательная доставка материалов (видео + PDF-брифы + задания)
- Интерактивные задания с немедленной обратной связью
- Система прогресса (Level X/10, сбор кода LIBERATION)
- Автоматические напоминания неактивным пользователям
- Генерация сертификатов по завершению курса
- Админ-панель в Telegram

## 🛠️ Технологический стек

- **Python 3.12**
- **aiogram 3.x** - асинхронный фреймворк для Telegram Bot API
- **PostgreSQL** - база данных
- **asyncpg** - асинхронный драйвер PostgreSQL
- **YooKassa** - платежная система
- **Vosk** - offline распознавание речи
- **Pillow** - генерация сертификатов
- **APScheduler** - планировщик задач для напоминаний

## 📁 Структура проекта

```
.
├── bot/                    # Основной код бота
│   ├── __init__.py
│   ├── main.py            # Точка входа
│   ├── config.py          # Конфигурация из .env
│   ├── handlers/          # Обработчики команд и сообщений
│   │   ├── start.py       # /start, регистрация
│   │   ├── payment.py     # Оплата курса
│   │   ├── course.py      # Доставка материалов
│   │   ├── tasks.py       # Система заданий
│   │   └── admin.py       # Админ-панель
│   ├── middlewares/       # Middleware
│   │   └── auth.py        # Проверка доступа
│   ├── keyboards/         # Клавиатуры
│   │   ├── inline.py      # Inline кнопки
│   │   └── reply.py       # Reply кнопки
│   ├── database/          # Работа с БД
│   │   ├── models.py      # SQLAlchemy модели
│   │   ├── database.py    # Подключение к БД
│   │   └── queries.py     # SQL запросы
│   ├── services/          # Бизнес-логика
│   │   ├── payment.py     # YooKassa интеграция
│   │   ├── course.py      # Логика курса
│   │   ├── tasks.py       # Проверка заданий
│   │   ├── speech.py      # Vosk распознавание
│   │   ├── progress.py    # Трекинг прогресса
│   │   └── certificates.py # Генерация сертификатов
│   ├── scheduler/         # Планировщик
│   │   └── reminders.py   # Напоминания
│   └── utils/             # Утилиты
│       ├── logger.py      # Логирование
│       └── helpers.py     # Вспомогательные функции
├── migrations/            # Миграции БД (Alembic)
├── materials/             # Материалы курса (не в git)
├── certificates/          # Сгенерированные сертификаты
├── logs/                  # Логи
├── tests/                 # Тесты
├── scripts/               # Вспомогательные скрипты
│   ├── parse_materials.py # Парсинг материалов
│   └── setup_db.py        # Инициализация БД
├── requirements.txt       # Python зависимости
├── .env.example          # Пример конфигурации
├── .env                  # Конфигурация (не в git)
├── .gitignore
└── README.md
```

## 🚀 Установка и запуск

### 1. Клонирование репозитория

```bash
git clone git@REHA:stiapanreha-dev/thelanguageescape.git
cd thelanguageescape
```

### 2. Установка зависимостей

```bash
# Установка системных зависимостей (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y postgresql python3-pip python3-venv ffmpeg

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка Python зависимостей
pip install -r requirements.txt
```

### 3. Настройка PostgreSQL

```bash
# Создание базы данных и пользователя
sudo -u postgres psql
CREATE DATABASE language_escape;
CREATE USER bot_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE language_escape TO bot_user;
\q
```

### 4. Конфигурация

Скопируйте `.env.example` в `.env` и заполните:

```bash
cp .env.example .env
nano .env
```

Обязательные параметры:
- `TELEGRAM_BOT_TOKEN` - токен от @BotFather
- `ADMIN_TELEGRAM_ID` - ваш Telegram ID
- `YOOKASSA_SHOP_ID` - Shop ID из YooKassa
- `YOOKASSA_SECRET_KEY` - секретный ключ YooKassa
- `DATABASE_URL` - строка подключения к PostgreSQL

### 5. Инициализация базы данных

```bash
# Применение миграций
alembic upgrade head

# Или через скрипт
python scripts/setup_db.py
```

### 6. Парсинг материалов

```bash
# Парсинг материалов курса из docs/Материалы
python scripts/parse_materials.py
```

### 7. Запуск бота

```bash
# Разработка
python bot/main.py

# Продакшн (через systemd)
sudo systemctl start language-escape-bot
sudo systemctl enable language-escape-bot
```

## 📊 База данных

### Основные таблицы

- **users** - пользователи бота
- **payments** - платежи
- **progress** - прогресс пользователей по дням
- **tasks_results** - результаты выполнения заданий
- **reminders** - история напоминаний
- **certificates** - сгенерированные сертификаты

## 🔐 Безопасность

- Все credentials хранятся в `.env` (не коммитится в Git)
- Пароли БД зашифрованы
- HTTPS для всех API запросов
- Соответствие GDPR

## 📈 Мониторинг

- Логи хранятся в `logs/`
- Метрики: конверсия оплат, прогресс пользователей, отток
- Статистика доступна в админ-панели

## 🧪 Тестирование

```bash
# Запуск тестов
pytest tests/

# С покрытием
pytest --cov=bot tests/
```

## 📝 Разработка

### Структура команд бота

- `/start` - начало работы, регистрация
- `/help` - справка
- `/pay` - оплата курса
- `/progress` - прогресс пользователя
- `/admin` - админ-панель (только для админа)

### Типы заданий

1. **Выбор ответа** - InlineKeyboard с 4 вариантами (A/B/C/D)
2. **Голосовое** - запись фразы, проверка через Vosk
3. **Диалог** - последовательный выбор фраз (3-4 шага)

## 🤝 Контрибьюция

Разработчик: Stiapan Reha (stiapan.reha@gmail.com)

## 📄 Лицензия

Проект создан для курса "The Language Escape".

---

**Статус:** В разработке
**Версия:** 0.1.0
**Python:** 3.12+
