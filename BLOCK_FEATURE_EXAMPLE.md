# Функция блоков в заданиях

## Описание
Добавлена поддержка необязательного поля `block` в заданиях курса. Это поле позволяет группировать задания в блоки, которые остаются видимыми на экране до перехода к другому блоку.

## Логика работы

### Правила удаления предыдущего задания:
1. **Если у задания НЕТ поля `block`** → считается новым блоком → предыдущее задание удаляется
2. **Если у обоих заданий есть `block` с одинаковым значением** → один блок → предыдущее задание НЕ удаляется
3. **Если у обоих заданий есть `block`, но с разными значениями** → разные блоки → предыдущее задание удаляется

### Визуально:
- ✅ **Задания в одном блоке** = видны все сообщения блока
- ❌ **Переход на другой блок** = предыдущие сообщения удаляются

## Пример использования в JSON

### Вариант 1: Диалог из 3 реплик (один блок)
```json
{
  "tasks": [
    {
      "task_number": 1,
      "type": "choice",
      "block": 1,
      "question": "Эмма: 'Hi! What's your name?'",
      "options": ["A) My name is John", "B) I don't know"],
      "correct_answer": "A"
    },
    {
      "task_number": 2,
      "type": "choice",
      "block": 1,
      "question": "Эмма: 'Nice! Where are you from?'",
      "options": ["A) From Russia", "B) From USA"],
      "correct_answer": "A"
    },
    {
      "task_number": 3,
      "type": "choice",
      "block": 1,
      "question": "Эмма: 'Great! Let's continue.'",
      "options": ["A) OK", "B) Wait"],
      "correct_answer": "A"
    },
    {
      "task_number": 4,
      "type": "choice",
      "question": "Терминал: 'Enter code'",
      "options": ["A) CODE_123", "B) CODE_456"],
      "correct_answer": "A"
    }
  ]
}
```

**Результат:**
- Задания 1-3 остаются на экране (один блок)
- При переходе на задание 4 — задания 1-3 удаляются (новый блок)

### Вариант 2: Два диалога в разных блоках
```json
{
  "tasks": [
    {
      "task_number": 1,
      "type": "choice",
      "block": 1,
      "question": "Эмма: 'What's the code?'",
      "options": ["A) ALPHA", "B) BETA"],
      "correct_answer": "A"
    },
    {
      "task_number": 2,
      "type": "choice",
      "block": 1,
      "question": "Эмма: 'Correct! Now open the door.'",
      "options": ["A) Open", "B) Wait"],
      "correct_answer": "A"
    },
    {
      "task_number": 3,
      "type": "choice",
      "block": 2,
      "question": "Алекс: 'Stop! Who are you?'",
      "options": ["A) I'm a friend", "B) I'm a stranger"],
      "correct_answer": "A"
    },
    {
      "task_number": 4,
      "type": "choice",
      "block": 2,
      "question": "Алекс: 'I see. Follow me.'",
      "options": ["A) Yes", "B) No"],
      "correct_answer": "A"
    }
  ]
}
```

**Результат:**
- Задания 1-2 видны вместе (блок 1)
- При переходе на задание 3 → задания 1-2 удаляются
- Задания 3-4 видны вместе (блок 2)

### Вариант 3: Без блоков (по умолчанию)
```json
{
  "tasks": [
    {
      "task_number": 1,
      "type": "choice",
      "question": "Question 1",
      "options": ["A) Yes", "B) No"],
      "correct_answer": "A"
    },
    {
      "task_number": 2,
      "type": "choice",
      "question": "Question 2",
      "options": ["A) Yes", "B) No"],
      "correct_answer": "A"
    }
  ]
}
```

**Результат:**
- Каждое задание удаляется при переходе к следующему (старое поведение)

## Реализация

### Файл: `bot/handlers/tasks.py`

#### Функции для работы с блоками

**1. Сохранение message_id в блок:**
```python
async def save_block_message_id(state: FSMContext, message_id: int, block_id: int):
    """Save message_id to the current block's message list."""
    data = await state.get_data()
    current_block_messages = data.get('current_block_messages', [])
    current_block_id = data.get('current_block_id')

    # If block changed, reset the list
    if current_block_id != block_id:
        current_block_messages = []

    # Add new message_id
    current_block_messages.append(message_id)

    # Save to state
    await state.update_data(
        current_block_messages=current_block_messages,
        current_block_id=block_id
    )
```

**2. Удаление всех сообщений блока:**
```python
async def delete_block_messages(callback: CallbackQuery, state: FSMContext):
    """Delete all messages from the current block."""
    data = await state.get_data()
    message_ids = data.get('current_block_messages', [])

    for msg_id in message_ids:
        try:
            await callback.bot.delete_message(
                chat_id=callback.message.chat.id,
                message_id=msg_id
            )
        except Exception as e:
            logger.warning(f"Failed to delete message {msg_id}: {e}")

    # Clear the list
    await state.update_data(current_block_messages=[], current_block_id=None)
```

#### Функция проверки блока
```python
def should_delete_previous_task(day_number: int, prev_task_number: int, current_task_number: int) -> bool:
    """
    Check if previous task message should be deleted when transitioning to current task.

    Logic:
    - If previous or current task has no 'block' field → delete (different blocks)
    - If both have 'block' field with same value → don't delete (same block)
    - If both have 'block' field with different values → delete (different blocks)
    """
    prev_task = course_service.get_task(day_number, prev_task_number)
    current_task = course_service.get_task(day_number, current_task_number)

    if not prev_task or not current_task:
        return True  # Delete by default if task not found

    prev_block = prev_task.get('block')
    current_block = current_task.get('block')

    if prev_block is None or current_block is None:
        return True  # Delete if either task has no block

    return prev_block != current_block  # Delete only if different blocks
```

#### Применение в коде
```python
# Auto-transition (правильный ответ)
current_task = course_service.get_task(day_number, task_number)
current_block = current_task.get('block') if current_task else None

# Save current message ID to block before potentially deleting
if current_block is not None:
    await save_block_message_id(state, callback.message.message_id, current_block)

# Check if should delete previous block messages
if should_delete_previous_task(day_number, task_number, next_task_number):
    await delete_block_messages(callback, state)
```

**Ключевое изменение:** Теперь удаляются **ВСЕ сообщения блока**, а не только последнее!

## Тестирование

### Сценарий 1: Диалог из 3 вопросов
1. Добавить `"block": 1` в задания 1-3
2. Запустить день
3. Ответить на задание 1 → задание 2 появится, задание 1 останется
4. Ответить на задание 2 → задание 3 появится, задания 1-2 останутся
5. Ответить на задание 3 → переход к заданию 4, задания 1-3 удалятся

### Сценарий 2: Два блока диалога
1. Добавить `"block": 1` в задания 1-2
2. Добавить `"block": 2` в задания 3-4
3. Запустить день
4. Ответить на задания 1-2 → они останутся видны
5. Ответить на задание 2 → переход к заданию 3, задания 1-2 удалятся
6. Ответить на задания 3-4 → они останутся видны

## Обратная совместимость

✅ **Полная обратная совместимость!**

Если в JSON **нет поля `block`** → работает как раньше (каждое задание удаляется).

Не нужно обновлять все существующие JSON файлы - они продолжат работать как прежде.

## Дата реализации
2025-11-08
