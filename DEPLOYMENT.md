# 🚀 Deployment Guide - GitHub Actions

Полная инструкция по настройке автоматического деплоя через GitHub.

---

## 📋 Содержание

1. [Подготовка VPS](#1-подготовка-vps)
2. [Настройка GitHub Secrets](#2-настройка-github-secrets)
3. [Первичный деплой](#3-первичный-деплой)
4. [Автоматический деплой](#4-автоматический-деплой)
5. [Troubleshooting](#5-troubleshooting)

---

## 1. Подготовка VPS

### Шаг 1.1: Подключитесь к VPS

```bash
ssh root@d2305931f6ab.vps.myjino.ru -p 49311
```

Пароль: `7PD+ZbGtDvSy`

### Шаг 1.2: Сгенерируйте SSH ключ для GitHub

```bash
# Генерация ключа
ssh-keygen -t ed25519 -C "deploy@the-language-escape.ru" -f ~/.ssh/github_deploy -N ""

# Просмотр публичного ключа
cat ~/.ssh/github_deploy.pub
```

**Скопируйте публичный ключ** (весь вывод команды выше).

### Шаг 1.3: Добавьте Deploy Key в GitHub

1. Откройте: https://github.com/stiapanreha-dev/thelanguageescape/settings/keys
2. Нажмите **"Add deploy key"**
3. Title: `VPS Deploy Key`
4. Key: *вставьте скопированный публичный ключ*
5. ✅ Поставьте галочку **"Allow write access"**
6. Нажмите **"Add key"**

### Шаг 1.4: Запустите начальную настройку

```bash
# Скачать скрипт
wget https://raw.githubusercontent.com/stiapanreha-dev/thelanguageescape/main/scripts/initial_setup.sh

# Сделать исполняемым
chmod +x initial_setup.sh

# Запустить
bash initial_setup.sh
```

**Следуйте инструкциям на экране.**

---

## 2. Настройка GitHub Secrets

### Шаг 2.1: Откройте настройки Secrets

Перейдите: https://github.com/stiapanreha-dev/thelanguageescape/settings/secrets/actions

### Шаг 2.2: Добавьте следующие Secrets

Нажмите **"New repository secret"** для каждого:

#### `SSH_PRIVATE_KEY`
```bash
# На VPS выполните:
cat ~/.ssh/github_deploy

# Скопируйте ВЕСЬ вывод (включая -----BEGIN и -----END)
```

**Value:** Вставьте приватный ключ

---

#### `VPS_HOST`
**Value:** `d2305931f6ab.vps.myjino.ru`

---

#### `VPS_PORT`
**Value:** `49311`

---

#### `VPS_USER`
**Value:** `root`

---

#### `PROJECT_DIR`
**Value:** `/root/language_escape_bot`

---

### Итого должно быть 5 secrets:
- ✅ SSH_PRIVATE_KEY
- ✅ VPS_HOST
- ✅ VPS_PORT
- ✅ VPS_USER
- ✅ PROJECT_DIR

---

## 3. Первичный деплой

### Шаг 3.1: Push кода в GitHub

На вашем локальном компьютере:

```bash
cd /home/lexun/work/KWORK/viktorsmith

# Добавить все файлы
git add .

# Коммит
git commit -m "Setup GitHub Actions deployment"

# Push в main
git push origin main
```

### Шаг 3.2: Проверьте Actions

1. Откройте: https://github.com/stiapanreha-dev/thelanguageescape/actions
2. Вы увидите запущенный workflow **"Deploy to VPS"**
3. Кликните на него, чтобы посмотреть лог

### Шаг 3.3: Настройте .env на VPS

После первого деплоя:

```bash
# SSH на VPS
ssh root@d2305931f6ab.vps.myjino.ru -p 49311

# Перейти в проект
cd /root/language_escape_bot

# Редактировать .env
nano .env
```

**Обязательно заполните:**
```env
TELEGRAM_BOT_TOKEN=8289801372:AAHfFISNCTRJ7Cmv5DsW4XEkv0GKaz0REdE
ADMIN_TELEGRAM_ID=ваш_telegram_id
YOOKASSA_PROVIDER_TOKEN=ваш_provider_token
```

**Сохраните:** `Ctrl+O`, `Enter`, `Ctrl+X`

### Шаг 3.4: Запустите бота

```bash
# Перезапуск сервиса
sudo systemctl restart language-escape-bot

# Проверка статуса
sudo systemctl status language-escape-bot

# Просмотр логов
journalctl -u language-escape-bot -f
```

---

## 4. Автоматический деплой

### Теперь при каждом push в main:

```bash
# Локально внесите изменения
git add .
git commit -m "Your changes"
git push origin main

# GitHub Actions автоматически:
# 1. Подключится к VPS
# 2. Обновит код (git pull)
# 3. Установит зависимости
# 4. Перезапустит бота
# 5. Проверит статус
```

### Мониторинг деплоя:

Откройте: https://github.com/stiapanreha-dev/thelanguageescape/actions

Вы увидите:
- ✅ Зеленая галочка - деплой успешен
- ❌ Красный крестик - ошибка (смотрите логи)

### Ручной запуск деплоя:

1. Откройте: https://github.com/stiapanreha-dev/thelanguageescape/actions
2. Выберите **"Deploy to VPS"**
3. Нажмите **"Run workflow"**
4. Выберите branch: `main`
5. Нажмите **"Run workflow"**

---

## 5. Troubleshooting

### Ошибка: "Permission denied (publickey)"

**Проблема:** SSH ключ не добавлен в GitHub Deploy Keys

**Решение:**
1. Проверьте публичный ключ: `cat ~/.ssh/github_deploy.pub`
2. Добавьте его в GitHub: https://github.com/stiapanreha-dev/thelanguageescape/settings/keys
3. ✅ Включите "Allow write access"

---

### Ошибка: "Bot failed to start"

**Проблема:** Ошибка в коде или неправильная конфигурация

**Решение:**
```bash
# SSH на VPS
ssh root@d2305931f6ab.vps.myjino.ru -p 49311

# Проверить логи
journalctl -u language-escape-bot -n 100

# Проверить .env
cat /root/language_escape_bot/.env

# Проверить вручную
cd /root/language_escape_bot
source venv/bin/activate
python3 bot/main.py
```

---

### Ошибка: "Database connection failed"

**Проблема:** PostgreSQL не запущен или неправильные credentials

**Решение:**
```bash
# Проверить PostgreSQL
systemctl status postgresql

# Запустить PostgreSQL
systemctl start postgresql

# Проверить подключение
sudo -u postgres psql -d language_escape -c "SELECT 1;"
```

---

### GitHub Actions "зависает"

**Проблема:** SSH не может подключиться

**Решение:**
1. Проверьте SSH_PRIVATE_KEY secret
2. Проверьте VPS_HOST, VPS_PORT, VPS_USER
3. Попробуйте подключиться вручную:
   ```bash
   ssh -p 49311 root@d2305931f6ab.vps.myjino.ru
   ```

---

## 📊 Полезные команды

### На VPS:

```bash
# Статус бота
systemctl status language-escape-bot

# Перезапуск
systemctl restart language-escape-bot

# Остановка
systemctl stop language-escape-bot

# Запуск
systemctl start language-escape-bot

# Логи (последние 100 строк)
journalctl -u language-escape-bot -n 100

# Логи (в реальном времени)
journalctl -u language-escape-bot -f

# Обновить код вручную
cd /root/language_escape_bot
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
systemctl restart language-escape-bot
```

### Локально:

```bash
# Проверить статус GitHub Actions
# Откройте: https://github.com/stiapanreha-dev/thelanguageescape/actions

# Push изменений
git add .
git commit -m "Update"
git push origin main
```

---

## ✅ Checklist готовности

Перед первым деплоем убедитесь:

- [ ] SSH ключ сгенерирован на VPS
- [ ] Публичный ключ добавлен в GitHub Deploy Keys
- [ ] Все 5 GitHub Secrets настроены
- [ ] PostgreSQL установлен и запущен на VPS
- [ ] .env файл заполнен на VPS
- [ ] Материалы загружены в docs/Материалы/
- [ ] Systemd service создан

---

## 🎉 Готово!

Теперь при каждом push в `main` бот автоматически обновится на VPS!

**Мониторинг:** https://github.com/stiapanreha-dev/thelanguageescape/actions

---

**Вопросы?** Проверьте раздел [Troubleshooting](#5-troubleshooting)
