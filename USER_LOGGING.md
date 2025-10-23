# 📊 User Action Logging

Система полного логирования действий пользователей с возможностью включения/выключения через конфигурацию.

---

## 🎯 Возможности

### Что логируется:
- ✅ **Все сообщения пользователей**
  - Текстовые сообщения (первые 100 символов)
  - Голосовые сообщения (с длительностью)
  - Фото, видео, документы

- ✅ **Все callback-запросы**
  - Нажатия на inline-кнопки
  - Данные callback (например: `start_day_1`, `answer_2_1_A`)

- ✅ **Информация о пользователе**
  - Telegram ID
  - Username (если есть)
  - Имя пользователя
  - Временная метка действия

### Формат логов:

```
[2025-10-23 21:15:42] User 12345678 (@username) [Иван] | Action: message | text='/start'
[2025-10-23 21:15:45] User 12345678 (@username) [Иван] | Action: callback | data='buy_course'
[2025-10-23 21:16:02] User 12345678 (@username) [Иван] | Action: message | type=voice, duration=15s
[2025-10-23 21:16:15] User 12345678 (@username) [Иван] | Action: callback | data='answer_1_1_B'
```

---

## ⚙️ Настройка

### Включить логирование (по умолчанию)

В `.env` файле:
```env
LOG_USER_ACTIONS=True
```

Или любое из значений: `True`, `1`, `yes`, `on` (регистр не важен)

### Выключить логирование

В `.env` файле:
```env
LOG_USER_ACTIONS=False
```

Или любое из значений: `False`, `0`, `no`, `off`

---

## 📝 Использование

### Просмотр логов пользователей

#### На VPS через journalctl:
```bash
# Все логи бота
journalctl -u language-escape-bot -f

# Только действия пользователей
journalctl -u language-escape-bot | grep "Action:"

# Действия конкретного пользователя
journalctl -u language-escape-bot | grep "User 12345678"

# Последние 100 действий
journalctl -u language-escape-bot | grep "Action:" -n 100
```

#### В файловых логах:
```bash
# Весь лог
cat /root/language_escape_bot/logs/bot.log

# Только действия пользователей
cat /root/language_escape_bot/logs/bot.log | grep "Action:"

# Действия за сегодня
cat /root/language_escape_bot/logs/bot.log | grep "$(date +%Y-%m-%d)" | grep "Action:"
```

### Фильтрация по типу действия

#### Только текстовые сообщения:
```bash
journalctl -u language-escape-bot | grep "Action: message" | grep "text="
```

#### Только callback-кнопки:
```bash
journalctl -u language-escape-bot | grep "Action: callback"
```

#### Только голосовые сообщения:
```bash
journalctl -u language-escape-bot | grep "type=voice"
```

---

## 🔍 Примеры аналитики

### Количество активных пользователей сегодня:
```bash
journalctl -u language-escape-bot --since today | grep "Action:" | awk '{print $5}' | sort -u | wc -l
```

### Топ-10 самых активных пользователей:
```bash
journalctl -u language-escape-bot | grep "Action:" | awk '{print $5}' | sort | uniq -c | sort -rn | head -10
```

### Количество нажатий на кнопку "купить":
```bash
journalctl -u language-escape-bot | grep "Action: callback" | grep "data='buy_course'" | wc -l
```

### Статистика по типам сообщений:
```bash
journalctl -u language-escape-bot | grep "Action: message" | grep -oP 'type=\w+' | sort | uniq -c
```

---

## 🔒 Безопасность и Приватность

### Что НЕ логируется:
- ❌ Полное содержимое длинных сообщений (только первые 100 символов)
- ❌ Файлы и медиа-контент (только метаданные)
- ❌ Личная информация пользователей из других источников
- ❌ Пароли и токены

### Рекомендации:
1. **Включайте логирование только при необходимости**
   - Для отладки
   - Для аналитики поведения пользователей
   - Для выявления проблем

2. **Регулярно очищайте старые логи**
   ```bash
   # Удалить логи старше 30 дней
   journalctl --vacuum-time=30d
   ```

3. **Ограничьте доступ к логам**
   ```bash
   # Только root может читать логи
   chmod 600 /root/language_escape_bot/logs/bot.log
   ```

---

## 🛠️ Технические детали

### Архитектура

**Middleware:** `bot/middlewares/user_logger.py`
- Перехватывает все Update события
- Извлекает информацию о пользователе и действии
- Форматирует и записывает в лог
- Работает на уровне `dp.update.middleware()` - раньше всех остальных

### Порядок middleware:
1. **UserActionLogger** - логирует действие (если включено)
2. **ActivityMiddleware** - обновляет last_activity в БД
3. **AdminMiddleware** - проверяет права администратора

### Производительность:
- Минимальное влияние на скорость обработки
- Асинхронная запись в лог
- Не блокирует основной поток выполнения

---

## 📊 Интеграция с аналитикой

### Экспорт логов для анализа:

#### В CSV формат:
```bash
journalctl -u language-escape-bot | grep "Action:" | \
awk -F'[][]' '{print $2","$4}' | \
awk -F'|' '{print $1","$2","$3}' > user_actions.csv
```

#### В JSON формат (для продвинутой аналитики):
```bash
journalctl -u language-escape-bot -o json | \
grep "Action:" > user_actions.json
```

---

## 🔧 Настройка уровня детализации

В будущих версиях можно добавить уровни детализации:

```env
# Минимальное логирование (только команды)
LOG_USER_ACTIONS_LEVEL=minimal

# Стандартное (текущее поведение)
LOG_USER_ACTIONS_LEVEL=standard

# Полное (включая содержимое сообщений)
LOG_USER_ACTIONS_LEVEL=full
```

---

## ✅ Проверка работы

### После включения логирования:

1. Перезапустите бота:
   ```bash
   systemctl restart language-escape-bot
   ```

2. Проверьте, что логирование включено:
   ```bash
   journalctl -u language-escape-bot | grep "User action logging"
   ```

   Должно быть: `✅ User action logging enabled`

3. Отправьте команду боту и проверьте лог:
   ```bash
   journalctl -u language-escape-bot -f
   ```

---

## 🎯 Кейсы использования

### 1. Отладка проблем
Пользователь жалуется, что бот не отвечает:
```bash
journalctl -u language-escape-bot | grep "User 12345678" | tail -20
```

### 2. Анализ конверсии
Сколько людей дошло от /start до покупки:
```bash
START_COUNT=$(journalctl -u language-escape-bot | grep "text='/start'" | wc -l)
BUY_COUNT=$(journalctl -u language-escape-bot | grep "data='buy_course'" | wc -l)
echo "Conversion: $((BUY_COUNT * 100 / START_COUNT))%"
```

### 3. Популярные функции
Какие команды используются чаще всего:
```bash
journalctl -u language-escape-bot | grep "Action: message" | \
grep -oP "text='[^']+'" | sort | uniq -c | sort -rn | head -10
```

---

**Создано:** 2025-10-23
**Версия:** 1.0
**Статус:** ✅ Готово к использованию
