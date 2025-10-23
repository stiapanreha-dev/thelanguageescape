# 🚀 Настройка GitHub Actions для автоматического деплоя

## 📋 Текущая ситуация

✅ GitHub Actions workflow уже настроен: `.github/workflows/deploy.yml`
❌ Не хватает GitHub Secrets для автоматического подключения к VPS

---

## 🔧 Настройка GitHub Secrets

### Шаг 1: Откройте настройки репозитория

1. Перейдите на GitHub: https://github.com/stiapanreha-dev/thelanguageescape
2. Откройте: **Settings** → **Secrets and variables** → **Actions**
3. Нажмите: **New repository secret**

### Шаг 2: Добавьте следующие секреты

Добавьте каждый секрет по очереди, нажимая "New repository secret":

#### 1. SSH_PRIVATE_KEY

**Name:** `SSH_PRIVATE_KEY`
**Value:**

Получить приватный ключ с VPS:

```bash
ssh -p 49311 root@d2305931f6ab.vps.myjino.ru 'cat ~/.ssh/id_rsa'
```

Скопируйте весь вывод (включая строки `-----BEGIN OPENSSH PRIVATE KEY-----` и `-----END OPENSSH PRIVATE KEY-----`) и вставьте в поле **Value** в GitHub Secrets.

#### 2. VPS_HOST

**Name:** `VPS_HOST`
**Value:** `d2305931f6ab.vps.myjino.ru`

#### 3. VPS_PORT

**Name:** `VPS_PORT`
**Value:** `49311`

#### 4. VPS_USER

**Name:** `VPS_USER`
**Value:** `root`

#### 5. PROJECT_DIR

**Name:** `PROJECT_DIR`
**Value:** `/root/language_escape_bot`

---

## ✅ Проверка настройки

После добавления всех секретов у вас должно быть **5 секретов**:

- ✅ SSH_PRIVATE_KEY
- ✅ VPS_HOST
- ✅ VPS_PORT
- ✅ VPS_USER
- ✅ PROJECT_DIR

---

## 🎯 Как работает автоматический деплой

### Автоматический деплой при push

Каждый раз, когда вы делаете `git push` в ветку `main`, GitHub Actions:

1. ✅ Подключается к VPS по SSH
2. ✅ Выполняет `git pull` в `/root/language_escape_bot`
3. ✅ Обновляет зависимости (`pip install -r requirements.txt`)
4. ✅ Перезапускает бота (`systemctl restart language-escape-bot`)
5. ✅ Проверяет, что бот запустился успешно

### Ручной деплой

Вы также можете запустить деплой вручную:

1. Откройте: **Actions** → **Deploy to VPS**
2. Нажмите: **Run workflow** → **Run workflow**

---

## 📊 Просмотр логов деплоя

1. Откройте вкладку **Actions** в GitHub
2. Выберите последний запуск **Deploy to VPS**
3. Кликните на Job **Deploy Bot to VPS**
4. Разверните шаги, чтобы увидеть детальные логи

---

## 🔍 Отладка проблем

### Ошибка: "Host key verification failed"

Это нормально при первом запуске. Workflow автоматически добавляет VPS в known_hosts.

### Ошибка: "Permission denied (publickey)"

Проверьте:
1. ✅ SSH_PRIVATE_KEY скопирован полностью (с BEGIN/END строками)
2. ✅ На VPS установлен публичный ключ в `~/.ssh/authorized_keys`

Проверить публичный ключ на VPS:
```bash
ssh -p 49311 root@d2305931f6ab.vps.myjino.ru 'cat ~/.ssh/authorized_keys'
```

### Ошибка: "Bot failed to start"

1. Посмотрите логи в выводе GitHub Actions
2. Или подключитесь к VPS и проверьте:
```bash
sudo journalctl -u language-escape-bot -n 50
```

---

## 🎉 Тестирование автоматического деплоя

После настройки секретов, проверьте работу:

### Вариант 1: Ручной запуск

1. **Actions** → **Deploy to VPS** → **Run workflow**
2. Дождитесь завершения (обычно 1-2 минуты)
3. Проверьте, что все шаги зеленые ✅

### Вариант 2: Commit и push

1. Сделайте любое небольшое изменение (например, в README.md)
2. Закоммитьте и запушьте:
```bash
git add .
git commit -m "Test automatic deployment"
git push origin main
```
3. Откройте **Actions** и следите за процессом деплоя

---

## 📝 Преимущества GitHub Actions

| До (ручной деплой) | После (GitHub Actions) |
|-------------------|----------------------|
| SSH подключение вручную | Автоматически при push |
| `git pull` вручную | Автоматически |
| `pip install` вручную | Автоматически |
| `systemctl restart` вручную | Автоматически |
| Нет проверки успешности | Автоматическая проверка |
| Нет логов деплоя | Полные логи в GitHub |

---

## ⚡ Следующие шаги

После настройки GitHub Actions вы сможете:

1. ✅ Делать изменения в коде локально
2. ✅ `git commit` и `git push`
3. ✅ GitHub автоматически задеплоит на VPS
4. ✅ Проверить статус деплоя во вкладке Actions

**Никаких ручных SSH подключений больше не требуется!** 🎉

---

**Создано:** 2025-10-23
**Статус:** Готово к использованию после добавления GitHub Secrets
