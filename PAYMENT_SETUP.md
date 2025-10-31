# 💳 Инструкция по настройке оплаты (Telegram Payments + YooKassa)

Полное пошаговое руководство по интеграции платежной системы в бота.

---

## 📋 Содержание

1. [Регистрация в YooKassa](#1-регистрация-в-yookassa)
2. [Получение Provider Token](#2-получение-provider-token)
3. [Настройка бота](#3-настройка-бота)
4. [Тестирование](#4-тестирование)
5. [Переход в production](#5-переход-в-production)
6. [Troubleshooting](#6-troubleshooting)

---

## 1. Регистрация в YooKassa

### Шаг 1.1: Создание аккаунта

1. Перейдите на https://yookassa.ru/
2. Нажмите **"Подключиться"** → **"Зарегистрироваться"**
3. Заполните форму:
   - Тип бизнеса (ИП / ООО / Самозанятый)
   - Контактные данные
   - Банковские реквизиты для выплат

### Шаг 1.2: Верификация (1-3 дня)

YooKassa проверит ваши данные:
- Документы (ИНН, ОГРН для ООО, паспорт для ИП)
- Банковские реквизиты
- Вид деятельности

**Важно:** Пока идет проверка, можно использовать **тестовый режим**.

---

## 2. Получение Provider Token

### Шаг 2.1: Войти в личный кабинет YooKassa

После регистрации войдите в ЛК: https://yookassa.ru/my/

### Шаг 2.2: Перейти в раздел Telegram

**Путь 1:**
https://yookassa.ru/my/merchant/integration/payment-gateway/payments-solutions/telegram

**Путь 2:**
1. Личный кабинет → **Настройки**
2. **Платежные решения** → **Способы приема платежей**
3. Найдите **Telegram** → Нажмите **Настроить**

### Шаг 2.3: Получить Provider Token

На странице Telegram вы увидите:

```
Provider Token (Тестовый): 1234567890:TEST-ABCDEFG...
Provider Token (Боевой): 1234567890:LIVE-HIJKLMN...
```

**Для разработки** используйте **Тестовый токен**.

---

## 3. Настройка бота

### Шаг 3.1: Добавить токен в `.env`

Скопируйте `.env.example` в `.env`:

```bash
cp .env.example .env
```

Откройте `.env` и заполните:

```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=8289801372:AAHfFISNCTRJ7Cmv5DsW4XEkv0GKaz0REdE

# YooKassa Provider Token (Telegram Payments)
YOOKASSA_PROVIDER_TOKEN=1234567890:TEST-your_test_token_here
YOOKASSA_TEST_MODE=True

# Admin
ADMIN_TELEGRAM_ID=your_telegram_id

# Price
COURSE_PRICE=999
COURSE_CURRENCY=RUB
```

### Шаг 3.2: Структура платежной системы

Бот уже настроен! Вот как это работает:

```
Пользователь → /start
      ↓
Видит "💰 Buy Course - 999 RUB"
      ↓
Нажимает кнопку
      ↓
Бот отправляет Invoice (счет)
      ↓
Telegram показывает форму оплаты
      ↓
Пользователь вводит данные карты
      ↓
Pre-checkout validation (проверка)
      ↓
Оплата через YooKassa
      ↓
Successful payment → Доступ открыт ✅
```

---

## 4. Тестирование

### Шаг 4.1: Тестовые карты YooKassa

При `YOOKASSA_TEST_MODE=True` используйте тестовые карты:

| Карта | Номер | CVV | Срок | Результат |
|-------|-------|-----|------|-----------|
| **Успех** | `5555 5555 5555 4444` | 123 | 12/24 | ✅ Платеж успешен |
| **Отклонение** | `4111 1111 1111 1111` | 123 | 12/24 | ❌ Недостаточно средств |
| **3DS** | `5555 5555 5555 5599` | 123 | 12/24 | 🔐 Требуется 3DS (код: 12345) |

### Шаг 4.2: Запуск бота

```bash
# Установить зависимости
pip install -r requirements.txt

# Запустить бота
python bot/main.py
```

### Шаг 4.3: Тестовый сценарий

1. Отправьте боту `/start`
2. Нажмите **"💰 Buy Course"**
3. В открывшейся форме введите:
   - Карта: `5555 5555 5555 4444`
   - Срок: `12/24`
   - CVV: `123`
   - Email: `test@example.com`
4. Нажмите **"Оплатить"**
5. Бот должен ответить:
   ```
   🎉 Payment Successful!
   Welcome to The Language Escape!
   ```

### Шаг 4.4: Проверка в БД

```bash
# Войти в PostgreSQL
psql -U bot_user -d language_escape

# Проверить платеж
SELECT * FROM payments ORDER BY created_at DESC LIMIT 1;

# Проверить доступ пользователя
SELECT telegram_id, has_access, current_day FROM users;
```

---

## 5. Переход в production

### Шаг 5.1: Дождаться верификации YooKassa

Убедитесь, что ваш аккаунт YooKassa **полностью верифицирован**.

### Шаг 5.2: Получить боевой Provider Token

1. Откройте https://yookassa.ru/my/merchant/integration/payment-gateway/payments-solutions/telegram
2. Скопируйте **Provider Token (Боевой)**
3. Обновите `.env`:

```env
YOOKASSA_PROVIDER_TOKEN=1234567890:LIVE-your_live_token_here
YOOKASSA_TEST_MODE=False
```

### Шаг 5.3: Проверка комиссий

YooKassa берет комиссию:
- **Банковские карты:** 2.8% + 10₽
- **YooMoney:** 1%
- **SBP (Система быстрых платежей):** 0.4-0.7%

**Telegram не берет комиссию** при использовании Telegram Payments API.

### Шаг 5.4: Настройка уведомлений

В ЛК YooKassa настройте webhook для уведомлений (опционально):

1. **Настройки** → **Уведомления**
2. Укажите URL: `https://your-domain.com/webhook/yookassa`
3. Включите события:
   - `payment.succeeded`
   - `payment.canceled`
   - `refund.succeeded`

**Примечание:** При использовании Telegram Payments webhook не обязателен, т.к. Telegram сам присылает `successful_payment`.

---

## 6. Troubleshooting

### Проблема: "Payment system is currently unavailable"

**Причина:** Provider Token не настроен.

**Решение:**
1. Проверьте `.env`: `YOOKASSA_PROVIDER_TOKEN` заполнен?
2. Перезапустите бота
3. Проверьте логи: `tail -f logs/bot.log`

---

### Проблема: "Invalid payment request"

**Причина:** Неверный формат payload или несовпадение user_id.

**Решение:**
1. Убедитесь, что пользователь использует актуальную версию Telegram
2. Проверьте логи бота на ошибки
3. Попросите пользователя отправить `/start` заново

---

### Проблема: "Pre-checkout validation failed"

**Причина:** Пользователь уже имеет доступ или не зарегистрирован.

**Решение:**
1. Проверьте БД: `SELECT * FROM users WHERE telegram_id = user_id;`
2. Если `has_access = TRUE`, пользователь уже оплатил
3. Если пользователя нет, попросите отправить `/start`

---

### Проблема: Оплата прошла, но доступ не открылся

**Причина:** Ошибка при обработке `successful_payment`.

**Решение:**
1. Проверьте логи: `grep "Successful payment" logs/bot.log`
2. Проверьте БД:
   ```sql
   SELECT * FROM payments WHERE telegram_payment_charge_id = 'payment_id';
   SELECT * FROM users WHERE telegram_id = user_id;
   ```
3. Вручную предоставьте доступ:
   ```sql
   UPDATE users SET has_access = TRUE, current_day = 1 WHERE telegram_id = user_id;
   ```

---

### Проблема: Тестовые карты не работают

**Причина:** Используется боевой токен вместо тестового.

**Решение:**
1. Убедитесь: `.env` → `YOOKASSA_TEST_MODE=True`
2. Используйте **тестовый Provider Token**
3. Перезапустите бота

---

## 📚 Дополнительные ресурсы

### Официальная документация

- [Telegram Payments API](https://core.telegram.org/bots/payments)
- [YooKassa Docs](https://yookassa.ru/developers)
- [YooKassa + Telegram Integration](https://yookassa.ru/developers/payment-acceptance/integration-scenarios/quick-start#telegram)
- [aiogram Payments Guide](https://docs.aiogram.dev/en/latest/dispatcher/filters/magic_filters.html#f-successful-payment)

### Поддержка

- **YooKassa Support:** support@yookassa.ru, +7 (495) 739-37-77
- **Telegram:** @YooKassaSupport

---

## ✅ Чеклист готовности к production

- [ ] Аккаунт YooKassa верифицирован
- [ ] Получен **боевой** Provider Token
- [ ] `.env` обновлен с боевыми credentials
- [ ] `YOOKASSA_TEST_MODE=False`
- [ ] Протестирована оплата реальной картой (минимальная сумма)
- [ ] Настроены уведомления в YooKassa (опционально)
- [ ] Проверены логи на ошибки
- [ ] База данных работает стабильно
- [ ] Есть план резервного копирования БД
- [ ] Документированы процедуры возврата средств

---

**Готово!** Ваш бот теперь принимает платежи через Telegram Payments + YooKassa 🎉

Если возникнут вопросы, проверьте секцию Troubleshooting или обратитесь в поддержку YooKassa.
