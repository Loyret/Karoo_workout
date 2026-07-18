# Karoo Trainer — Документация по развёртыванию в промышленную эксплуатацию

## 1. Описание проекта

**Karoo Trainer** — веб-приложение для генерации тренировок в формате ZWO (Zwift Workout) для велосипедных компьютеров Hammerhead Karoo 3. Приложение позволяет пользователям выбирать из готовых шаблонов тренировок, конструировать собственные, а также скачивать сгенерированные файлы `.zwo`.

### Технологический стек

| Компонент | Технология |
|-----------|------------|
| Язык | Python 3.11+ |
| Веб-фреймворк | Flask 3.x |
| ORM | Flask-SQLAlchemy 3.x (SQLAlchemy) |
| Авторизация | Flask-Login 0.6 |
| Валидация форм | Flask-WTF 1.2 + WTForms |
| Rate limiting | Flask-Limiter 3.5 |
| Отправка почты | Flask-Mail 0.9 |
| Шаблонизатор | Jinja2 (встроенный в Flask) |
| Фронтенд | HTML5, CSS3, vanilla JS, Chart.js 4.x (CDN) |
| БД по умолчанию | SQLite 3 (karoo_trainer.db) |
| Сервер в продакшене | Gunicorn (рекомендован) |

### Структура проекта

```
training_karoo/
├── app.py                  # Главный модуль приложения, создание Flask-приложения
├── auth.py                 # Регистрация, вход, верификация email, сброс пароля
├── config.py               # Конфигурации (development/testing/production)
├── dashboard.py            # Личный кабинет пользователя
├── email_service.py        # Отправка email (верификация, сброс пароля)
├── mail.py                 # Инициализация Flask-Mail
├── models.py               # SQLAlchemy-модели: User, WorkoutHistory
├── requirements.txt        # Python-зависимости
├── karoo_trainer.db        # Файл SQLite (только разработка)
├── generator/
│   ├── __init__.py
│   ├── zones.py            # Определение зон тренировки (Z1-Z7)
│   ├── workouts.py         # Шаблоны тренировок (7 встроенных)
│   └── zwo.py              # Генератор ZWO XML-файлов
├── static/
│   ├── css/style.css       # Стили приложения
│   └── js/app.js           # Клиентская логика
├── templates/
│   ├── base.html           # Базовый шаблон
│   ├── index.html          # Главная страница
│   ├── templates.html      # Каталог шаблонов тренировок
│   ├── template_detail.html # Детали шаблона + график
│   ├── builder.html        # Конструктор тренировок
│   ├── education.html      # Обучающий раздел
│   ├── dashboard.html      # Личный кабинет
│   ├── dashboard_settings.html # Настройки профиля
│   ├── auth/
│   │   ├── login.html
│   │   ├── register.html
│   │   ├── forgot_password.html
│   │   └── reset_password.html
│   └── emails/
│       ├── verify.html     # Письмо подтверждения email
│       └── reset.html      # Письмо сброса пароля
└── venv/                   # Виртуальное окружение (не коммитится)
```

---

## 2. Требования к среде

| Компонент | Минимальная версия | Рекомендованная версия |
|-----------|-------------------|----------------------|
| Python | 3.11 | 3.12 |
| pip | 22.x | Последняя |
| PostgreSQL (для прода) | 14 | 16 |
| OpenSSL | 1.1.1 | 3.x |

**Операционные системы:** Linux (Ubuntu 22.04/24.04, Debian 12, RHEL 9), macOS, Windows Server.

---

## 3. Переменные окружения

Все настройки задаются через переменные окружения. Файл `.env` (добавлен в `.gitignore`):

| Переменная | Обязательна | Значение по умолчанию | Описание |
|-----------|-------------|----------------------|----------|
| `SECRET_KEY` | **Да** | `change-me-in-production!` | Секретный ключ Flask (сессии, CSRF) |
| `FLASK_ENV` | Да | `development` | Режим: `development`, `testing`, `production` |
| `DATABASE_URL` | Да | `sqlite:///karoo_trainer.db` | URI подключения к БД |
| `MAIL_SERVER` | Да | `smtp.gmail.com` | SMTP-сервер |
| `MAIL_PORT` | Да | `587` | Порт SMTP |
| `MAIL_USE_TLS` | Да | `true` | Использовать TLS |
| `MAIL_USERNAME` | Да | `` | SMTP логин |
| `MAIL_PASSWORD` | Да | `` | SMTP пароль |
| `MAIL_DEFAULT_SENDER` | Да | `Karoo Trainer <noreply@example.com>` | Адрес отправителя |
| `PORT` | Нет | `5000` | Порт приложения (для gunicorn через gunicorn.conf.py или CLI) |

**Пример `.env`:**
```bash
SECRET_KEY=your-random-64-char-string-here
FLASK_ENV=production
DATABASE_URL=postgresql+psycopg2://karoo_user:secure_password@localhost:5432/karoo_db
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your@gmail.com
MAIL_PASSWORD=app-specific-password
MAIL_DEFAULT_SENDER=Karoo Trainer <your@gmail.com>
```

**Генерация SECRET_KEY:**
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

## 4. Установка зависимостей

### 4.1 Системные пакеты (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3-pip libpq-dev
```

### 4.2 Создание виртуального окружения

```bash
cd /opt/karoo-trainer
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn psycopg2-binary    # Для прода
```

### 4.3 Полный `requirements.txt` для прода

```
flask>=3.0
flask-login>=0.6
flask-sqlalchemy>=3.1
flask-wtf>=1.2
flask-limiter>=3.5
flask-mail>=0.9
werkzeug>=3.0
email-validator>=2.0
gunicorn>=22.0
psycopg2-binary>=2.9
```

---

## 5. Развёртывание

### 5.1 Вариант A: Gunicorn + systemd (Linux, рекомендовано)

#### Создание пользователя

```bash
sudo adduser --system --group --home /opt/karoo-trainer karoo
```

#### Копирование проекта

```bash
sudo cp -r /path/to/training_karoo /opt/karoo-trainer
sudo chown -R karoo:karoo /opt/karoo-trainer
```

#### Создание `.env` файла

```bash
cat > /opt/karoo-trainer/.env << 'EOF'
SECRET_KEY=<сгенерировать>
FLASK_ENV=production
DATABASE_URL=postgresql+psycopg2://karoo_user:password@localhost:5432/karoo_db
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=Karoo Trainer <your@gmail.com>
EOF

chmod 600 /opt/karoo-trainer/.env
```

#### Создание systemd-сервиса

```ini
# /etc/systemd/system/karoo-trainer.service
[Unit]
Description=Karoo Trainer Web Application
After=network.target postgresql.service
Wants=postgresql.service

[Service]
User=karoo
Group=karoo
WorkingDirectory=/opt/karoo-trainer
EnvironmentFile=/opt/karoo-trainer/.env
ExecStart=/opt/karoo-trainer/venv/bin/gunicorn \
    --workers 4 \
    --threads 2 \
    --bind 127.0.0.1:8000 \
    --access-logfile /var/log/karoo/access.log \
    --error-logfile /var/log/karoo/error.log \
    --capture-output \
    --timeout 30 \
    app:create_app()
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

> **Важно:** Gunicorn вызывает `app:create_app()` (factory pattern). Это работает,因为在 `app.py` функция `create_app()` определена на верхнем уровне модуля.

Запуск:
```bash
sudo mkdir -p /var/log/karoo
sudo chown karoo:karoo /var/log/karoo

sudo systemctl daemon-reload
sudo systemctl enable karoo-trainer
sudo systemctl start karoo-trainer
sudo systemctl status karoo-trainer
```

#### Настройка Nginx (reverse proxy + SSL)

```nginx
# /etc/nginx/sites-available/karoo-trainer
server {
    listen 80;
    server_name karoo.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name karoo.example.com;

    ssl_certificate /etc/letsencrypt/live/karoo.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/karoo.example.com/privkey.pem;

    # Безопасность
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Ограничение размера запроса (защита от uploaded file abuse)
    client_max_body_size 1M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;

        # Таймауты
        proxy_connect_timeout 60s;
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
    }

    location /static/ {
        alias /opt/karoo-trainer/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Запрет на доступ к скрытым файлам
    location ~ /\. {
        deny all;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/karoo-trainer /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### SSL через Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d karoo.example.com
```

---

### 5.2 Вариант B: Docker + docker-compose

#### Dockerfile

```dockerfile
FROM python:3.12-slim AS base

RUN groupadd -r karoo && useradd -r -g karoo -d /app karoo

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn psycopg2-binary

COPY . .

RUN chown -R karoo:karoo /app

USER karoo

EXPOSE 8000

CMD ["gunicorn", \
     "--workers", "4", \
     "--threads", "2", \
     "--bind", "0.0.0.0:8000", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--timeout", "30", \
     "app:create_app()"]
```

#### docker-compose.yml

```yaml
version: "3.9"

services:
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: karoo_db
      POSTGRES_USER: karoo_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "127.0.0.1:5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U karoo_user -d karoo_db"]
      interval: 10s
      timeout: 5s
      retries: 5

  web:
    build: .
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
    env_file:
      - .env
    environment:
      DATABASE_URL: postgresql+psycopg2://karoo_user:${DB_PASSWORD}@db:5432/karoo_db
    ports:
      - "127.0.0.1:8000:8000"
    volumes:
      - static_files:/app/static
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/')"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  pgdata:
  static_files:
```

#### .env (для Docker)

```bash
SECRET_KEY=<сгенерировать>
FLASK_ENV=production
DB_PASSWORD=<надёжный пароль>
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=Karoo Trainer <your@gmail.com>
```

Запуск:
```bash
docker compose up -d --build
docker compose logs -f web
```

---

### 5.3 Вариант C: Разработка (ваш текущий режим)

```bash
cd training_karoo
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

export FLASK_ENV=development
export SECRET_KEY=dev-key-change-in-prod
python app.py
```

Приложение доступно по адресу `http://localhost:5000`.

---

## 6. База данных

### 6.1 SQLite (разработка)

При `DATABASE_URL` не заданном или `sqlite:///karoo_trainer.db` приложение автоматически создаёт файл БД. Инициализация таблиц выполняется при первом запуске (`db.create_all()` в `app.py:297`).

**Недостатки SQLite для прода:**
- Одна запись на запись (нет конкурентного доступа)
- Нет аутентификации / контроля доступа
- Нет point-in-time recovery

### 6.2 PostgreSQL (рекомендовано для прода)

```bash
# Создание БД и пользователя
sudo -u postgres psql
CREATE USER karoo_user WITH PASSWORD 'secure_password';
CREATE DATABASE karoo_db OWNER karoo_user;
GRANT ALL PRIVILEGES ON DATABASE karoo_db TO karoo_user;
\q
```

**DATABASE_URL формат:**
```
postgresql+psycopg2://karoo_user:secure_password@localhost:5432/karoo_db
```

### 6.3 Миграции схемы

Текущая схема определена в `models.py`. Таблицы:

| Таблица | Описание | Ключевые столбцы |
|---------|----------|------------------|
| `users` | Пользователи | id, username, email, password_hash, ftp, weight_kg, is_verified, verify_token, reset_token, created_at |
| `workout_history` | История тренировок | id, user_id (FK), template_id, name, ftp_at_time, duration_sec, zwo_content, completed, notes, created_at, completed_at |

Для миграций в продакшене рекомендуется установить Flask-Migrate (Alembic):

```bash
pip install flask-migrate
```

```python
# Добавить в app.py
from flask_migrate import Migrate
migrate = Migrate(app, db)
```

```bash
flask db init
flask db migrate -m "initial"
flask db upgrade
```

---

## 7. Настройка почты

### Gmail

1. Включить 2FA в Google-аккаунте
2. Перейти в [App Passwords](https://myaccount.google.com/apppasswords)
3. Создать пароль приложения для "Mail"
4. Использовать его как `MAIL_PASSWORD`

### Альтернативные SMTP-провайдеры

| Провайдер | MAIL_SERVER | MAIL_PORT | Примечание |
|-----------|------------|-----------|------------|
| Gmail | smtp.gmail.com | 587 | Требует App Password |
| Yandex | smtp.yandex.ru | 465 | Используйте SSL |
| Mail.ru | smtp.mail.ru | 465 | Используйте SSL |
| SendGrid | smtp.sendgrid.net | 587 | API-ключ как пароль |
| Amazon SES | email-smtp.us-east-1.amazonaws.com | 465 | IAM credentials |

Для Yandex/Mail.ru с портом 465 потребуется изменить `MAIL_USE_TLS` на `false` и `MAIL_PORT` на `465` (SSL). Для этого Flask-Mail по умолчанию использует STARTTLS; для SSL-подключения потребуется патч или прокси.

---

## 8. Обеспечение безопасности

### 8.1 Что уже реализовано в коде

| Мера | Реализация | Файл |
|------|-----------|------|
| CSRF-защита | Flask-WTF (`WTF_CSRF_ENABLED=True`) | `config.py:26` |
| HTTP-only cookies | `SESSION_COOKIE_HTTPONLY=True` | `config.py:24` |
| Secure cookies (prod) | `SESSION_COOKIE_SECURE=True` | `config.py:44` |
| SameSite cookies | `SESSION_COOKIE_SAMESITE=Lax` | `config.py:25` |
| Rate limiting | 10/min login, 5/min register | `app.py:49-54` |
| Security headers | X-Content-Type-Options, X-Frame-Options, Referrer-Policy | `app.py:118-123` |
| Пароли | werkzeug `generate_password_hash` (pbkdf2) | `models.py:38` |
| Верификация email | Токен с 24ч TTL | `models.py:43-58` |
| Сброс пароля | Токен с 1ч TTL | `models.py:60-75` |

### 8.2 Дополнительные рекомендации для прода

#### Смена алгоритма хеширования паролей

```python
# В models.py:38 — рекомендуется явно указать алгоритм
from werkzeug.security import generate_password_hash
self.password_hash = generate_password_hash(password, method="pbkdf2:sha256:600000")
```

#### Рекомендуемые HTTP-заголовки (дополнение к Nginx)

```nginx
add_header Content-Security-Policy "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self';" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
```

#### Защита от брутфорса

Flask-Limiter уже настроен на базовый rate-limiting. Для усиления:

```python
# Дополнительно: лимит на IP для всех маршрутов
limiter.limit("100/hour")(app)

# Лимит на скачивание ZWO файлов
limiter.limit("30/minute")(app.view_functions.get("api_download", lambda: None))
```

#### Бэкапы PostgreSQL

```bash
# Ежедневный cron-бэкап
0 2 * * * pg_dump -U karoo_user karoo_db | gzip > /var/backups/karoo/karoo_$(date +\%Y\%m\%d).sql.gz

# Хранение 30 дней
find /var/backups/karoo -name "*.sql.gz" -mtime +30 -delete
```

---

## 9. Мониторинг и логирование

### 9.1 Логи Gunicorn

```
/var/log/karoo/access.log  — access log (запросы)
/var/log/karoo/error.log   — error log (ошибки)
```

### 9.2 Логирование Flask

Добавить в `config.py` (ProductionConfig):

```python
import logging
from logging.handlers import RotatingFileHandler

class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True

    @staticmethod
    def init_app(app):
        handler = RotatingFileHandler('/var/log/karoo/flask.log', maxBytes=10*1024*1024, backupCount=5)
        handler.setLevel(logging.WARNING)
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
        app.logger.addHandler(handler)
```

### 9.3 Health-check endpoint

Добавить в `app.py`:

```python
@app.route("/health")
def health():
    try:
        db.session.execute(db.text("SELECT 1"))
        return jsonify({"status": "healthy"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500
```

---

## 10. API-эндпоинты

### Публичные

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/` | Главная страница |
| GET | `/templates` | Каталог шаблонов тренировок |
| GET | `/template/<id>` | Детали шаблона с графиком |
| GET | `/builder` | Конструктор тренировок |
| GET | `/education` | Обучающий раздел |
| POST | `/api/generate` | Генерация ZWO по template_id + ftp |
| GET | `/api/download/<id>` | Скачивание ZWO файла |
| GET | `/api/zones?ftp=200` | Зоны тренировки для FTP |
| POST | `/api/build_custom` | Генерация кастомной тренировки |

### Требующие аутентификации

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/dashboard` | Личный кабинет |
| POST/GET | `/dashboard/settings` | Настройки профиля (FTP, вес) |
| POST | `/api/workout/save` | Сохранение тренировки в историю |
| POST | `/api/workout/complete/<id>` | Отметка выполнения |
| POST | `/api/workout/delete/<id>` | Удаление из истории |
| GET | `/api/workout/download/<id>` | Скачивание из истории |

### Авторизация

| Метод | URL | Описание |
|-------|-----|----------|
| GET/POST | `/register` | Регистрация |
| GET/POST | `/login` | Вход |
| GET | `/verify/<token>` | Подтверждение email |
| GET | `/resend-verify` | Повторная отправка подтверждения |
| GET/POST | `/forgot-password` | Запрос сброса пароля |
| GET/POST | `/reset/<token>` | Форма сброса пароля |
| GET | `/logout` | Выход |

---

## 11. Встроенные тренировки

| ID | Название | Категория | Сложность | Длительность |
|----|----------|-----------|-----------|-------------|
| `endurance` | Выносливость | Базовая | 2/5 | 75 мин |
| `tempo` | Темповая работа | Базовая | 3/5 | 60 мин |
| `sweetspot` | Sweet Spot | Эффективность | 3/5 | 60 мин |
| `threshold` | Пороговая 2x20 | Развитие силы | 4/5 | 75 мин |
| `vo2max` | VO2max 5x3 | Максимальная мощность | 5/5 | 50 мин |
| `hiit` | HIIT Спринты | Максимальная мощность | 5/5 | 40 мин |
| `recovery` | Активное восстановление | Восстановление | 1/5 | 45 мин |

---

## 12. Тестирование

### Локальное тестирование

```bash
export FLASK_ENV=testing
export TESTING=true
export SECRET_KEY=test-key
python -m pytest tests/ -v   # если есть тесты
```

### Smoke-тест после деплоя

```bash
# Health-check
curl -s https://karoo.example.com/health | python -m json.tool

# Проверка редиректа на HTTPS
curl -I http://karoo.example.com

# Проверка статики
curl -s -o /dev/null -w "%{http_code}" https://karoo.example.com/static/css/style.css
# Должно вернуть 200

# Проверка API
curl -s https://karoo.example.com/api/zones?ftp=250 | python -m json.tool

# Проверка регистрации
curl -s -X POST https://karoo.example.com/api/generate \
  -H "Content-Type: application/json" \
  -d '{"template_id":"endurance","ftp":250}' | python -m json.tool
```

---

## 13. Чек-лист развёртывания

### Перед деплоем

- [ ] Установить Python 3.11+ и зависимости системного уровня
- [ ] Создать виртуальное окружение и установить pip-зависимости
- [ ] Сгенерировать уникальный `SECRET_KEY` (минимум 32 байта)
- [ ] Создать файл `.env` с продакшен-значениями
- [ ] Убедиться, что `FLASK_ENV=production`
- [ ] Настроить PostgreSQL (создать БД и пользователя с ограниченными правами)
- [ ] Указать `DATABASE_URL` в формате `postgresql+psycopg2://...`
- [ ] Настроить SMTP-сервер и проверить отправку писем
- [ ] Убрать `DEBUG=True` (должно быть `False` в ProductionConfig)

### Инфраструктура

- [ ] Gunicorn запущен с 4 workers / 2 threads
- [ ] systemd-сервис создан и включён в автозагрузку
- [ ] Nginx настроен как reverse proxy с SSL
- [ ] SSL-сертификат установлен (Let's Encrypt или коммерческий)
- [ ] HSTS, CSP, X-Frame-Options заголовки настроены
- [ ] Статика раздаётся через Nginx (не через Flask)
- [ ] Файлы `.env` и `karoo_trainer.db` не доступны извне

### Безопасность

- [ ] `SECRET_KEY` — случайная строка, не дефолтная
- [ ] Rate limiting активен (login: 10/min, register: 5/min)
- [ ] Бэкапы БД настроены (cron + проверка целостности)
- [ ] Логи ротируются и не растут бесконечно
- [ ] Порт Gunicorn слушает только `127.0.0.1`
- [ ] Доступ к PostgreSQL ограничен localhost / internal network

### После деплоя

- [ ] Открыть приложение в браузере и проверить главную страницу
- [ ] Зарегистрировать тестовый аккаунт
- [ ] Проверить получение email-подтверждения
- [ ] Сгенерировать тренировку и скачать `.zwo` файл
- [ ] Открыть `.zwo` файл в Hammerhead Dashboard или Zwift для валидации
- [ ] Проверить личный кабинет и историю тренировок
- [ ] Проверить `/health` endpoint
- [ ] Мониторить логи в течение 24-48 часов

---

## 14. Устранение неполадок

| Проблема | Решение |
|----------|---------|
| `OperationalError: no such table` | Запустить `db.create_all()` в контексте приложения или настроить Flask-Migrate |
| `SECRET_KEY` warning в логах | Задать `SECRET_KEY` в `.env` |
| Email не отправляется | Проверить `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS`; для Gmail использовать App Password |
| `502 Bad Gateway` | Проверить, что Gunicorn запущен: `systemctl status karoo-trainer` |
| Медленная загрузка | Убедиться, что статика раздаётся через Nginx (`/static/`) |
| CSRF error при POST | Убедиться, что `WTF_CSRF_ENABLED=True` и клиент отправляет CSRF-токен |
| `SQLAlchemy` URI с `postgres://` | Заменить на `postgresql://` или `postgresql+psycopg2://` |
| Ошибка SSL в Nginx | Проверить пути к сертификатам: `nginx -t` |
| Приложение не стартует через gunicorn | Проверить, что `app:create_app()` вызывается, а не `app.py` |

---

## 15. Шаблоны масштабирования

### Горизонтальное масштабирование

```
                    ┌─────────────┐
                    │    Nginx    │ :443
                    │  (LB/SSL)  │
                    └──────┬──────┘
               ┌───────────┼───────────┐
               │           │           │
         ┌─────┴───┐ ┌─────┴───┐ ┌─────┴───┐
         │Gunicorn │ │Gunicorn │ │Gunicorn │ :8000
         │Worker 1 │ │Worker 2 │ │Worker N │
         └────┬────┘ └────┬────┘ └────┬────┘
              │           │           │
              └───────────┼───────────┘
                    ┌─────┴─────┐
                    │ PostgreSQL│
                    │  (RDS)    │
                    └───────────┘
```

### Кэширование

Для кэширования результатов `api/zones`:

```python
from flask_caching import Cache

cache = Cache(app, config={'CACHE_TYPE': 'RedisCache', 'CACHE_REDIS_URL': 'redis://localhost:6379/0'})

# Декоратор:
@cache.memoize(timeout=3600)
def get_zones(ftp):
    ...
```

### Консультативные рекомендации

| Метрика | Значение |
|---------|----------|
| Рекомендуемое число workers | `2 * CPU_CORES + 1` |
| Макс. время ответа | < 200ms (рендеринг страниц) |
| Макс. время генерации ZWO | < 50ms |
| Хранилище БД (при 1000 пользователей) | ~50-100 MB |
| Рекомендуемый RAM | 512 MB+ (минимум), 2 GB (при 100+ одновременных) |
