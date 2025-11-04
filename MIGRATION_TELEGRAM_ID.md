# 🔧 Миграция telegram_id: INTEGER → BIGINT

## Проблема

**Ошибка:** `invalid input for query argument $1: 5273817226 (value out of int32 range)`

**Причина:** Telegram ID пользователя `5273817226` превышает максимальное значение для типа `INTEGER` в PostgreSQL.

- **INTEGER** (int32): максимум `2,147,483,647`
- **Telegram ID**: `5,273,817,226` ❌ Слишком большой!

## Решение

Изменить тип данных `telegram_id` с `INTEGER` на `BIGINT`:

- **BIGINT** (int64): максимум `9,223,372,036,854,775,807` ✅

## ✅ Безопасность

Миграция `INTEGER → BIGINT` в PostgreSQL **ПОЛНОСТЬЮ БЕЗОПАСНА**:

- ✅ **Не удаляет данные**
- ✅ **Не изменяет существующие значения**
- ✅ **Только расширяет диапазон**
- ✅ **Автоматический бэкап перед миграцией**
- ✅ **Проверка целостности данных после миграции**

## 📋 Что было исправлено

### 1. Модель данных (bot/database/models.py)

**До:**
```python
telegram_id = Column(Integer, unique=True, nullable=False, index=True)
```

**После:**
```python
telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
```

### 2. Создан безопасный скрипт миграции

Скрипт: `scripts/safe_migrate_telegram_id.sh`

**Что делает:**
1. ✅ Проверяет текущее состояние БД
2. ✅ Создает ПОЛНЫЙ бэкап базы данных
3. ✅ Выполняет миграцию
4. ✅ Проверяет целостность данных
5. ✅ Создает подробный отчет

## 🚀 Инструкция по миграции

### Шаг 1: Обновить код на VPS

```bash
# SSH на VPS
ssh -p 49311 root@d2305931f6ab.vps.myjino.ru

# Перейти в проект
cd /root/language_escape_bot

# Обновить код
git pull origin main
```

### Шаг 2: Выполнить безопасную миграцию

```bash
# Запустить скрипт миграции
./scripts/safe_migrate_telegram_id.sh
```

**Скрипт спросит подтверждение перед миграцией!**

### Шаг 3: Перезапустить бота

```bash
systemctl restart language-escape-bot
```

### Шаг 4: Проверить работу

```bash
# Посмотреть логи
journalctl -u language-escape-bot -f

# Попросить пользователя с ID 5273817226 написать /start
```

## 📊 Что будет в логах миграции

```
╔════════════════════════════════════════════════════════════════╗
║   БЕЗОПАСНАЯ МИГРАЦИЯ TELEGRAM_ID: INTEGER → BIGINT            ║
╚════════════════════════════════════════════════════════════════╝

📋 Шаг 1/5: Проверка текущего состояния БД
Текущий тип telegram_id: integer
Количество пользователей в БД: 15

📦 Шаг 2/5: Создание ПОЛНОГО бэкапа базы данных
✅ Бэкап создан успешно! Размер: 24K

🔍 Шаг 3/5: Проверка безопасности миграции
Продолжить миграцию? (yes/no): yes

🔄 Шаг 4/5: Выполнение миграции
✅ Миграция выполнена успешно!

✅ Шаг 5/5: Проверка результата
Новый тип telegram_id: bigint
✅ Все данные на месте! (15 = 15)

╔════════════════════════════════════════════════════════════════╗
║   ✅ МИГРАЦИЯ ЗАВЕРШЕНА УСПЕШНО!                               ║
╚════════════════════════════════════════════════════════════════╝
```

## 🔄 Откат миграции (если что-то пошло не так)

Если возникли проблемы, можно откатиться из бэкапа:

```bash
# Остановить бота
systemctl stop language-escape-bot

# Восстановить из бэкапа
sudo -u postgres psql language_escape < /root/language_escape_bot/backups/db_backup_before_telegram_id_migration_YYYYMMDD_HHMMSS.sql

# Запустить бота
systemctl start language-escape-bot
```

## 📁 Файлы миграции

- **Безопасный скрипт:** `scripts/safe_migrate_telegram_id.sh`
- **Python скрипт:** `scripts/migrate_telegram_id_to_bigint.py` (альтернатива)
- **Бэкапы:** `/root/language_escape_bot/backups/`
- **Логи:** `/root/language_escape_bot/logs/migration_telegram_id_*.log`

## ❓ FAQ

### Q: Потеряются ли данные пользователей?
**A:** Нет! Миграция только расширяет диапазон значений. Все данные остаются на месте.

### Q: Сколько времени занимает миграция?
**A:** 10-30 секунд для небольших таблиц (до 1000 пользователей).

### Q: Нужно ли останавливать бота?
**A:** Рекомендуется, но не обязательно. PostgreSQL поддерживает ALTER TABLE на живой БД.

### Q: Что если у меня больше не будет таких больших ID?
**A:** Миграция все равно полезна - это предотвратит проблемы в будущем. Telegram выдает большие ID все чаще.

### Q: Будет ли бот работать медленнее после миграции?
**A:** Нет, производительность не изменится. BIGINT работает так же быстро как INTEGER на 64-битных системах.

## ✅ Проверка после миграции

```bash
# Проверить тип telegram_id
sudo -u postgres psql -d language_escape -c "
    SELECT data_type
    FROM information_schema.columns
    WHERE table_name = 'users' AND column_name = 'telegram_id';
"
# Должно быть: bigint

# Проверить количество пользователей
sudo -u postgres psql -d language_escape -c "SELECT COUNT(*) FROM users;"

# Попробовать добавить пользователя с большим ID (тест)
sudo -u postgres psql -d language_escape -c "
    INSERT INTO users (telegram_id, first_name, has_access)
    VALUES (9999999999, 'Test Big ID', false);
"
# Должно работать без ошибок!
```

## 📞 Поддержка

Если возникли проблемы:
1. Проверьте лог миграции в `/root/language_escape_bot/logs/`
2. Проверьте бэкап в `/root/language_escape_bot/backups/`
3. Свяжитесь с разработчиком

---

**Дата создания:** 2025-11-04
**Статус:** Готово к выполнению
**Риск:** Низкий (с автоматическим бэкапом)
