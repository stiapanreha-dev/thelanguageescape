# 🔍 CODE AUDIT REPORT - The Language Escape Bot

**Дата аудита:** 2025-10-23
**Аудитор:** Claude Code AI (ultrathink mode)
**Статус:** 15 проблем найдено

---

## 📊 СВОДКА

| Категория | Количество | Статус |
|-----------|------------|--------|
| 🔴 КРИТИЧНЫЕ | 5 | Требуют немедленного исправления |
| 🟡 ВАЖНЫЕ | 5 | Исправить в ближайшее время |
| 🟢 НЕЗНАЧИТЕЛЬНЫЕ | 5 | Улучшения и оптимизации |

---

## 🔴 КРИТИЧНЫЕ ПРОБЛЕМЫ

### 1. ❌ course.py:487 - Missing datetime import

**Проблема:**
Используется `datetime.utcnow()` без импорта модуля `datetime`

**Код:**
```python
completion_date=progress_data.get('course_completed') or datetime.utcnow(),
```

**Ошибка при выполнении:**
```
NameError: name 'datetime' is not defined
```

**Когда упадет:**
При завершении финального дня (day 10) и генерации сертификата

**Исправление:**
```python
# В начале функции generate_and_send_certificate (строка 395)
from datetime import datetime
```

---

### 2. ❌ course.py:141 + tasks.py:307 - Bot parameter не инжектится

**Проблема:**
В aiogram 3.x параметр `bot: Bot` не инжектится автоматически

**Файлы:**
- `course.py`: строки 141, 201, 340
- `tasks.py`: строка 304

**Как исправить:**
```python
# БЫЛО:
async def callback_watch_video(callback: CallbackQuery, session: AsyncSession, bot: Bot):

# СТАЛО:
async def callback_watch_video(callback: CallbackQuery, session: AsyncSession):
    bot = callback.bot  # Получить из callback
```

---

### 3. ❌ start.py:220 - Некорректный вызов после delete()

**Проблема:**
После `callback.message.delete()` вызывается `cmd_help()` который пытается вызвать `message.answer()`

**Код:**
```python
await callback.message.delete()
await cmd_help(callback.message, session)  # Сообщение уже удалено!
```

**Исправление:**
```python
# Использовать edit_text вместо delete + answer
await callback.message.edit_text(help_text, parse_mode="Markdown")
```

---

### 4. ❌ payment.py:237 - Неправильное имя поля

**Проблема:**
Используется `metadata`, но в models.py поле называется `payment_metadata`

**Код:**
```python
metadata={  # НЕПРАВИЛЬНО
    "provider_payment_charge_id": ...,
}
```

**Исправление:**
```python
payment_metadata={  # ПРАВИЛЬНО
    "provider_payment_charge_id": ...,
}
```

---

### 5. ❌ tasks.py:307 - Missing bot parameter в callback_skip_task

**Проблема:**
Вызывается `callback_finish_day(callback, session)` без `bot` параметра

**Исправление:**
```python
async def callback_skip_task(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    # ...
    await callback_finish_day(callback, session, bot)
```

---

## 🟡 ВАЖНЫЕ ПРОБЛЕМЫ

### 6. ⚠️ Отсутствие try/except в database operations

**Проблема:**
Многие операции с БД выполняются без обработки исключений

**Файлы:**
- start.py: строка 36
- course.py: строка 76
- tasks.py: строка 199

**Исправление:**
```python
try:
    result = await session.execute(...)
    # ...
except Exception as e:
    logger.error(f"DB error: {e}", exc_info=True)
    await message.answer("⚠️ Error occurred. Please try again.")
    return
```

---

### 7. ⚠️ admin.py:388 - Broadcast без rate limiting

**Проблема:**
Массовая рассылка может привести к блокировке бота (Telegram limit: 30 msg/sec)

**Исправление:**
```python
import asyncio

for user in users:
    try:
        await message.bot.send_message(...)
        success_count += 1

        # Rate limiting
        if success_count % 30 == 0:
            await asyncio.sleep(1)
    except Exception as e:
        ...
```

---

### 8. ⚠️ course.py:183 - Race condition в start_day

**Проблема:**
Могут создаться два Progress записи при одновременных вызовах

**Исправление:**
```python
try:
    await session.commit()
except Exception as e:
    await session.rollback()
    # Получить существующий progress
    ...
```

---

### 9. ⚠️ payment.py:236 - JSON serialization

**Проблема:**
`provider_payment_charge_id` может быть не JSON-сериализуемым

**Исправление:**
```python
payment_metadata={
    "provider_payment_charge_id": str(value) if value else None,
    "invoice_payload": str(value) if value else None,
}
```

---

### 10. ⚠️ Отсутствие unique constraint для Progress

**Проблема:**
Нет БД constraint для предотвращения дубликатов (user_id, day_number)

**Исправление в models.py:**
```python
from sqlalchemy import UniqueConstraint

class Progress(Base):
    # ...
    __table_args__ = (
        UniqueConstraint('user_id', 'day_number', name='_user_day_uc'),
    )
```

---

## 🟢 НЕЗНАЧИТЕЛЬНЫЕ ПРОБЛЕМЫ

### 11-15. Улучшения

- Добавить индексы на `last_activity`, `day_number`, `is_correct`
- Оптимизировать логику `liberation_code`
- Рефакторинг дублированного кода в `start.py`
- Добавить error handler decorator
- Создать middleware для bot injection

---

## 🎯 ПЛАН ИСПРАВЛЕНИЯ

### Фаза 1 - Критичные (немедленно)
1. ✅ Исправить bot parameter injection во всех handlers
2. ✅ Добавить datetime import в course.py
3. ✅ Исправить callback_help в start.py
4. ✅ Переименовать metadata → payment_metadata
5. ✅ Добавить bot parameter в callback_skip_task

### Фаза 2 - Важные (сегодня)
6. ✅ Добавить try/except во все DB operations
7. ✅ Добавить rate limiting в broadcast
8. ✅ Добавить UniqueConstraint для Progress

### Фаза 3 - Улучшения (по возможности)
9. ⏳ Добавить индексы в БД
10. ⏳ Создать error handler decorator
11. ⏳ Оптимизации

---

## 📂 ФАЙЛЫ ТРЕБУЮЩИЕ ИЗМЕНЕНИЙ

| Файл | Проблем | Приоритет |
|------|---------|-----------|
| bot/handlers/course.py | 4 | 🔴 Критичный |
| bot/handlers/tasks.py | 2 | 🔴 Критичный |
| bot/handlers/start.py | 2 | 🔴 Критичный |
| bot/services/payment.py | 2 | 🔴 Критичный |
| bot/handlers/admin.py | 1 | 🟡 Важный |
| bot/services/course.py | 1 | 🟡 Важный |
| bot/database/models.py | 1 | 🟡 Важный |

---

**СТАТУС:** Готов к исправлению
**ВРЕМЯ НА ИСПРАВЛЕНИЕ:** ~30-40 минут
**КОЛИЧЕСТВО КОММИТОВ:** 3-4 (по фазам)

