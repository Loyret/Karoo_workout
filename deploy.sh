#!/usr/bin/env bash
#
#   ╔══════════════════════════════════════════════════════════╗
#   ║         KAROO TRAINER — АВТОМАТИЧЕСКИЙ ДЕПЛОЙ          ║
#   ║    Запусти этот скрипт на чистой Ubuntu/Debian VM      ║
#   ╚══════════════════════════════════════════════════════════╝
#
#   Использование:
#     1. Скопируй этот файл на VM
#     2. chmod +x deploy.sh
#     3. sudo ./deploy.sh
#
#   Скрипт сам спросит домен и настроит ВСЁ:
#     - Безопасность Linux (SSH, Firewall, Fail2ban, Sysctl)
#     - Python + зависимости
#     - PostgreSQL
#     - Gunicorn (процесс-менеджер)
#     - Nginx (веб-сервер)
#     - SSL-сертификат (Let's Encrypt)
#

set -e  # Остановка при ошибке

# ─────────────────────── ЦВЕТА ДЛЯ ВЫВОДА ───────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# ─────────────────────── УТИЛИТЫ ───────────────────────
print_header() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║  $1${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
    echo ""
}

print_ok()      { echo -e "${GREEN}  ✓ $1${NC}"; }
print_warn()    { echo -e "${YELLOW}  ⚠ $1${NC}"; }
print_error()   { echo -e "${RED}  ✗ $1${NC}"; }
print_step()    { echo -e "${BLUE}  → $1${NC}"; }

check_ok() {
    if [ $? -eq 0 ]; then
        print_ok "$1"
    else
        print_error "$1 — ОШИБКА!"
        exit 1
    fi
}

# ─────────────────────── ПРОВЕРКА ROOT ───────────────────────
if [ "$EUID" -ne 0 ]; then
    print_error "Запусти скрипт от root: sudo ./deploy.sh"
    exit 1
fi

# ─────────────────────── СБОР ИНФОРМАЦИИ ───────────────────────
clear
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                                        ║${NC}"
echo -e "${CYAN}║       🚴  KAROO TRAINER — ДЕПЛОЙ С НУЛЯ  🚴           ║${NC}"
echo -e "${CYAN}║                                                        ║${NC}"
echo -e "${CYAN}║   Этот скрипт установит и настроит ВСЁ автоматически   ║${NC}"
echo -e "${CYAN}║   Включая полную безопасность Linux                    ║${NC}"
echo -e "${CYAN}║                                                        ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

read -p "Введи домен (например karoo.example.com): " DOMAIN
if [ -z "$DOMAIN" ]; then
    print_error "Домен не может быть пустым!"
    exit 1
fi

read -p "Введи email для SSL-сертификата: " EMAIL
if [ -z "$EMAIL" ]; then
    print_error "Email не может быть пустым!"
    exit 1
fi

read -p "Введи SMTP email (для отправки писем, например user@gmail.com): " MAIL_USER
read -s -p "Введи SMTP пароль (пароль приложения Gmail): " MAIL_PASS
echo ""

# SSH: спрашиваем про смену порта
echo ""
echo -e "${YELLOW}  SSH-безопасность: рекомендуется сменить порт SSH с 22 на другой.${NC}"
echo -e "${YELLOW}  Это защитит от автоматических атак. Порт 2222 — популярный выбор.${NC}"
echo ""
read -p "Сменить SSH порт? (y/n, рекомендуется y): " SSH_CHANGE
if [ "$SSH_CHANGE" = "y" ] || [ "$SSH_CHANGE" = "Y" ]; then
    read -p "Новый порт SSH (по умолчанию 2222): " SSH_PORT
    SSH_PORT=${SSH_PORT:-2222}
else
    SSH_PORT="22"
fi

echo ""
echo -e "${YELLOW}Будет установлено:${NC}"
echo "  Домен:      $DOMAIN"
echo "  Email SSL:  $EMAIL"
echo "  SMTP:       $MAIL_USER"
echo "  SSH порт:   $SSH_PORT"
echo "  Проект:     /opt/karoo-trainer"
echo "  Порты:      80 (HTTP), 443 (HTTPS), 8000 (Gunicorn)"
echo ""
echo -e "${RED}  ⚠ ВНИМАНИЕ: Если ты подключён по SSH — убедись, что у тебя${NC}"
echo -e "${RED}    есть доступ к консоли VM на случай ошибки!${NC}"
echo ""
read -p "Продолжить? (y/n): " CONFIRM
if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo "Отмена."
    exit 0
fi

# ═══════════════════════════════════════════════════════════════════
#                     БЕЗОПАСНОСТЬ LINUX
# ═══════════════════════════════════════════════════════════════════

# ─────────────────────── ШАГ 0: ГЕНЕРАЦИЯ ПАРОЛЕЙ ───────────────────────
print_header "Шаг 0/13 — Генерация секретных ключей"

SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || openssl rand -hex 32)
print_ok "SECRET_KEY сгенерирован"

DB_PASSWORD=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 24)
print_ok "Пароль БД сгенерирован"

# ─────────────────────── ШАГ 1: ОБНОВЛЕНИЕ СИСТЕМЫ ───────────────────────
print_header "Шаг 1/13 — Установка системных пакетов"

export DEBIAN_FRONTEND=noninteractive

apt-get update -qq
print_ok "Список пакетов обновлён"

apt-get install -y -qq \
    python3 python3-venv python3-pip python3-dev \
    postgresql postgresql-contrib \
    nginx \
    certbot python3-certbot-nginx \
    libpq-dev gcc \
    curl git ufw fail2ban unattended-upgrades \
    >/dev/null 2>&1
print_ok "Все пакеты установлены"

# ─────────────────────── ШАГ 2: SSH HARDENING ───────────────────────
print_header "Шаг 2/13 — Настройка безопасности SSH"

SSHD_CONFIG="/etc/ssh/sshd_config"
SSHD_BACKUP="/etc/ssh/sshd_config.bak.$(date +%s)"

# Бэкап конфига
cp "$SSHD_CONFIG" "$SSHD_BACKUP"
print_ok "Бэкап SSH-конфига: $SSHD_BACKUP"

# Отключение root login
sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' "$SSHD_CONFIG"
if ! grep -q "^PermitRootLogin" "$SSHD_CONFIG"; then
    echo "PermitRootLogin no" >> "$SSHD_CONFIG"
fi
print_ok "Вход под root запрещён"

# Отключение парольной аутентификации
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' "$SSHD_CONFIG"
if ! grep -q "^PasswordAuthentication" "$SSHD_CONFIG"; then
    echo "PasswordAuthentication no" >> "$SSHD_CONFIG"
fi
print_ok "Парольная аутентификация отключена (только SSH-ключи)"

# Смена порта
if [ "$SSH_PORT" != "22" ]; then
    sed -i 's/^#\?Port .*/Port '"$SSH_PORT"'/' "$SSHD_CONFIG"
    if ! grep -q "^Port " "$SSHD_CONFIG"; then
        echo "Port $SSH_PORT" >> "$SSHD_CONFIG"
    fi
    print_ok "SSH-порт изменён на $SSH_PORT"
fi

# Отключение пустых паролей
sed -i 's/^#\?PermitEmptyPasswords.*/PermitEmptyPasswords no/' "$SSHD_CONFIG"
if ! grep -q "^PermitEmptyPasswords" "$SSHD_CONFIG"; then
    echo "PermitEmptyPasswords no" >> "$SSHD_CONFIG"
fi
print_ok "Пустые пароли запрещены"

# Максимум 3 попытки аутентификации
sed -i 's/^#\?MaxAuthTries.*/MaxAuthTries 3/' "$SSHD_CONFIG"
if ! grep -q "^MaxAuthTries" "$SSHD_CONFIG"; then
    echo "MaxAuthTries 3" >> "$SSHD_CONFIG"
fi
print_ok "Максимум 3 попытки аутентификации"

# Таймаут отключения
sed -i 's/^#\?ClientAliveInterval.*/ClientAliveInterval 300/' "$SSHD_CONFIG"
sed -i 's/^#\?ClientAliveCountMax.*/ClientAliveCountMax 2/' "$SSHD_CONFIG"
if ! grep -q "^ClientAliveInterval" "$SSHD_CONFIG"; then
    echo "ClientAliveInterval 300" >> "$SSHD_CONFIG"
    echo "ClientAliveCountMax 2" >> "$SSHD_CONFIG"
fi
print_ok "Таймаут неактивных сессий: 10 минут"

# Отключение X11 forwarding
sed -i 's/^#\?X11Forwarding.*/X11Forwarding no/' "$SSHD_CONFIG"
if ! grep -q "^X11Forwarding" "$SSHD_CONFIG"; then
    echo "X11Forwarding no" >> "$SSHD_CONFIG"
fi
print_ok "X11 forwarding отключён"

# Перезапуск SSH (осторожно — не теряем соединение!)
systemctl reload sshd 2>/dev/null || systemctl reload ssh 2>/dev/null || true
print_ok "SSH перезапущен"

if [ "$SSH_PORT" != "22" ]; then
    echo ""
    echo -e "${RED}  ╔═══════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}  ║  ⚠ ВАЖНО: SSH-порт изменён на $SSH_PORT!             ║${NC}"
    echo -e "${RED}  ║  Следующее подключение:                               ║${NC}"
    echo -e "${RED}  ║  ssh -p $SSH_PORT user@${DOMAIN}                       ║${NC}"
    echo -e "${RED}  ║                                                       ║${NC}"
    echo -e "${RED}  ║  Убедись, что у тебя есть SSH-ключ!                   ║${NC}"
    echo -e "${RED}  ╚═══════════════════════════════════════════════════════╝${NC}"
    echo ""
fi

# ─────────────────────── ШАГ 3: FIREWALL (UFW) ───────────────────────
print_header "Шаг 3/13 — Настройка файрвола (UFW)"

# Сброс правил
ufw --force reset >/dev/null 2>&1

# Политики по умолчанию
ufw default deny incoming >/dev/null 2>&1
ufw default allow outgoing >/dev/null 2>&1
print_ok "Политика: блокировать входящие, разрешить исходящие"

# SSH
ufw allow "$SSH_PORT/tcp" comment "SSH" >/dev/null 2>&1
print_ok "Порт SSH ($SSH_PORT) открыт"

# HTTP + HTTPS
ufw allow 80/tcp comment "HTTP" >/dev/null 2>&1
ufw allow 443/tcp comment "HTTPS" >/dev/null 2>&1
print_ok "Порты HTTP (80) и HTTPS (443) открыты"

# Включаем файрвол
ufw --force enable >/dev/null 2>&1
print_ok "UFW файрвол активирован"

ufw status verbose | head -20

# ─────────────────────── ШАГ 4: FAIL2BAN ───────────────────────
print_header "Шаг 4/13 — Настройка Fail2ban (защита от брутфорса)"

# Конфигурация Fail2ban для SSH
cat > /etc/fail2ban/jail.local << 'F2B_EOF'
[DEFAULT]
# Время блокировки: 1 час
bantime  = 3600
# Окно наблюдения: 10 минут
findtime = 600
# Максимум неудачных попыток
maxretry = 3
# Действие при блокировке: добавить правило в UFW
banaction = ufw

[sshd]
enabled = true
port    = ssh
filter  = sshd
logpath = /var/log/auth.log
maxretry = 3
F2B_EOF

# Обновляем порт SSH в fail2ban если он изменился
if [ "$SSH_PORT" != "22" ]; then
    sed -i "s/^port    = ssh/port    = $SSH_PORT/" /etc/fail2ban/jail.local
fi

systemctl enable fail2ban >/dev/null 2>&1
systemctl restart fail2ban >/dev/null 2>&1
print_ok "Fail2ban активирован (бан после 3 неудачных попыток)"

# ─────────────────────── ШАГ 5: SYSCTL HARDENING ───────────────────────
print_header "Шаг 5/13 — Усиление безопасности ядра (sysctl)"

cat > /etc/sysctl.d/99-karoo-security.conf << 'SYSCTL_EOF'
# ════════════════════════════════════════════════
# Karoo Trainer — Security Hardening
# ════════════════════════════════════════════════

# Защита от IP-спуфинга
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1

# Игнорирование ICMP-редиректов (защита от MITM)
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv6.conf.all.accept_redirects = 0
net.ipv6.conf.default.accept_redirects = 0

# Не отправлять ICMP-редиректы
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0

# Игнорирование source-routed пакетов
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0
net.ipv6.conf.all.accept_source_route = 0
net.ipv6.conf.default.accept_source_route = 0

# Логирование подозрительных пакетов
net.ipv4.conf.all.log_martians = 1
net.ipv4.conf.default.log_martians = 1

# Защита от SYN-flood атак
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_max_syn_backlog = 2048
net.ipv4.tcp_synack_retries = 2

# Игнорирование широковещательных ICMP (ping flood)
net.ipv4.icmp_echo_ignore_broadcasts = 1

# Защита от ICMP timing attacks
net.ipv4.icmp_ratemask = 88089

# Включить IP-форвардинг только если нужен (обычно НЕ нужен)
# net.ipv4.ip_forward = 0

# ASLR — случайнаяизация адресного пространства
kernel.randomize_va_space = 2

# Ограничение dmesg для обычных пользователей
kernel.dmesg_restrict = 1

# Ограничение ptrace
kernel.yama.ptrace_scope = 1

# Ограничение core dumps
fs.suid_dumpable = 0
SYSCTL_EOF

sysctl -p /etc/sysctl.d/99-karoo-security.conf >/dev/null 2>&1
print_ok "Sysctl-настройки безопасности применены"

# ─────────────────────── ШАГ 6: АВТООБНОВЛЕНИЯ БЕЗОПАСНОСТИ ───────────────────────
print_header "Шаг 6/13 — Настройка автообновлений безопасности"

cat > /etc/apt/apt.conf.d/20auto-upgrades << 'AUTO_EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
AUTO_EOF

cat > /etc/apt/apt.conf.d/50unattended-upgrades << 'UNATTENDED_EOF'
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}";
    "${distro_id}:${distro_codename}-security";
    "${distro_id}ESMApps:${distro_codename}-apps-security";
};

Unattended-Upgrade::Package-Blacklist {
};

Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "false";
UNATTENDED_EOF

dpkg-reconfigure -f noninteractive unattended-upgrades >/dev/null 2>&1
print_ok "Автообновления безопасности настроены"

# ─────────────────────── ШАГ 7: ПОЛЬЗОВАТЕЛЬ + ПРАВА ───────────────────────
print_header "Шаг 7/13 — Создание пользователя и настройка прав"

INSTALL_DIR="/opt/karoo-trainer"

if ! id "karoo" &>/dev/null; then
    adduser --system --group --home "$INSTALL_DIR" --shell /bin/bash karoo
    print_ok "Пользователь karoo создан"
else
    print_warn "Пользователь karoo уже существует — пропускаю"
fi

# ─────────────────────── ШАГ 8: КОПИРОВАНИЕ ПРОЕКТА ───────────────────────
print_header "Шаг 8/13 — Установка проекта"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$SCRIPT_DIR/app.py" ]; then
    SOURCE_DIR="$SCRIPT_DIR"
elif [ -f "$(pwd)/app.py" ]; then
    SOURCE_DIR="$(pwd)"
else
    print_error "Не могу найти проект! Положи deploy.sh в папку с проектом."
    exit 1
fi

if [ "$SOURCE_DIR" != "$INSTALL_DIR" ]; then
    mkdir -p "$INSTALL_DIR"
    cp -r "$SOURCE_DIR"/* "$SOURCE_DIR"/.gitignore "$INSTALL_DIR/" 2>/dev/null || true
    cp -r "$SOURCE_DIR"/.git "$INSTALL_DIR/" 2>/dev/null || true
    print_ok "Проект скопирован в $INSTALL_DIR"
else
    print_warn "Проект уже в $INSTALL_DIR — пропускаю копирование"
fi

# Убираем dev-файлы
rm -f "$INSTALL_DIR/karoo_trainer.db"
rm -rf "$INSTALL_DIR/__pycache__" "$INSTALL_DIR"/venv

# Права на файлы
chown -R karoo:karoo "$INSTALL_DIR"
chmod 750 "$INSTALL_DIR"
chmod 600 "$INSTALL_DIR/.env" 2>/dev/null || true
print_ok "Права на файлы установлены (750 проект, 600 .env)"

# Защита от выполнения скриптов в static/
find "$INSTALL_DIR/static" -name "*.py" -delete 2>/dev/null || true
print_ok "Python-файлы из static/ удалены"

# ─────────────────────── ШАГ 9: VIRTUALENV + ЗАВИСИМОСТИ ───────────────────────
print_header "Шаг 9/13 — Установка Python-зависимостей"

sudo -u karoo bash << 'DEPS_EOF'
set -e
cd /opt/karoo-trainer

python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
pip install gunicorn psycopg2-binary flask-migrate --quiet

echo "✓ Зависимости установлены"
DEPS_EOF
check_ok "Python-окружение готово"

# ─────────────────────── ШАГ 10: POSTGRESQL ───────────────────────
print_header "Шаг 10/13 — Настройка PostgreSQL"

systemctl start postgresql 2>/dev/null || true
systemctl enable postgresql 2>/dev/null || true

# Ограничиваем доступ PostgreSQL только localhost
PG_HBA=$(find /etc/postgresql -name pg_hba.conf 2>/dev/null | head -1)
if [ -n "$PG_HBA" ]; then
    # Убеждаемся что PostgreSQL слушает только localhost
    PG_CONF=$(find /etc/postgresql -name postgresql.conf 2>/dev/null | head -1)
    if [ -n "$PG_CONF" ]; then
        sed -i "s/^#\?listen_addresses.*/listen_addresses = 'localhost'/" "$PG_CONF"
        print_ok "PostgreSQL слушает только localhost"
    fi
fi

# Создаём БД и пользователя
sudo -u postgres psql << SQL_EOF
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'karoo_user') THEN
        CREATE USER karoo_user WITH PASSWORD '${DB_PASSWORD}';
    END IF;
END
\$\$;

SELECT 'CREATE DATABASE karoo_db OWNER karoo_user'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'karoo_db')\gexec

GRANT ALL PRIVILEGES ON DATABASE karoo_db TO karoo_user;
SQL_EOF
check_ok "База данных karoo_db создана"

systemctl restart postgresql 2>/dev/null || true
print_ok "PostgreSQL перезапущен"

# ─────────────────────── ШАГ 11: .env ФАЙЛ ───────────────────────
print_header "Шаг 11/13 — Создание конфигурации (.env)"

cat > "$INSTALL_DIR/.env" << EOF
# ══════════════════════════════════════════════
# Karoo Trainer — Конфигурация
# Создано автоматически: $(date)
# ══════════════════════════════════════════════

# Flask
SECRET_KEY=${SECRET_KEY}
FLASK_ENV=production

# База данных
DATABASE_URL=postgresql+psycopg2://karoo_user:${DB_PASSWORD}@localhost:5432/karoo_db

# Почта (SMTP)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=${MAIL_USER}
MAIL_PASSWORD=${MAIL_PASS}
MAIL_DEFAULT_SENDER=Karoo Trainer <${MAIL_USER}>
EOF

chmod 600 "$INSTALL_DIR/.env"
chown karoo:karoo "$INSTALL_DIR/.env"
print_ok "Файл .env создан (права 600 — только владелец)"

# ─────────────────────── ШАГ 12: GUNICORN + SYSTEMD ───────────────────────
print_header "Шаг 12/13 — Настройка Gunicorn (процесс-сервер)"

cat > /etc/systemd/system/karoo-trainer.service << EOF
[Unit]
Description=Karoo Trainer — Генератор тренировок
After=network.target postgresql.service
Wants=postgresql.service

[Service]
User=karoo
Group=karoo
WorkingDirectory=/opt/karoo-trainer
EnvironmentFile=/opt/karoo-trainer/.env

# Gunicorn
ExecStart=/opt/karoo-trainer/venv/bin/gunicorn \\
    --workers 3 \\
    --threads 2 \\
    --bind 127.0.0.1:8000 \\
    --access-logfile /var/log/karoo/access.log \\
    --error-logfile /var/log/karoo/error.log \\
    --capture-output \\
    --timeout 30 \\
    app:create_app()

ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always
RestartSec=5

# ══════════════════════════════════════════════
#  БЕЗОПАСНОСТЬ SYSTEMD
# ══════════════════════════════════════════════

# Запрет на запись в системные директории
ProtectSystem=strict
# Запрет на доступ к /home
ProtectHome=true
# Запрет на получение новых привилегий
NoNewPrivileges=true
# Запрет на изменение namespace
ProtectControlGroups=true
ProtectKernelModules=true
ProtectKernelTunables=true
# Ограничение доступа к /tmp
PrivateTmp=true
# Запрет на запись в /boot, /etc
ReadWritePaths=/opt/karoo-trainer /var/log/karoo /tmp
# Ограничение доступа к устройствам
ProtectDevices=true
# Ограничение системных вызовов
SystemCallFilter=@system-service
SystemCallArchitectures=native
# Ограничение IPC
RestrictNamespaces=true
RestrictRealtime=true
RestrictSUIDSGID=true
# Запрет на переключение на другой пользователь
User=karoo
Group=karoo

[Install]
WantedBy=multi-user.target
EOF

mkdir -p /var/log/karoo
chown karoo:karoo /var/log/karoo
chmod 750 /var/log/karoo

systemctl daemon-reload
print_ok "Systemd-сервис создан с максимальными ограничениями"

# ─────────────────────── ШАГ 13: NGINX ───────────────────────
print_header "Шаг 13/13 — Настройка Nginx (веб-сервер)"

cat > /etc/nginx/sites-available/karoo-trainer << EOF
server {
    listen 80;
    server_name ${DOMAIN};

    # Безопасность: скрытие версии Nginx
    server_tokens off;

    # Безопасные заголовки
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self';" always;

    # Ограничение размера запроса (защита от DoS)
    client_max_body_size 1M;
    client_body_buffer_size 16k;
    client_header_buffer_size 1k;
    large_client_header_buffers 4 8k;

    # Таймауты (защита от slowloris)
    client_body_timeout 12;
    client_header_timeout 12;
    keepalive_timeout 15;
    send_timeout 10;

    # Статика (кэширование)
    location /static/ {
        alias /opt/karoo-trainer/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # Запрет на скрытые файлы (.git, .env, etc.)
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }

    # Запрет на доступ к .env
    location = /.env {
        deny all;
    }

    # Проксирование на Gunicorn
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;

        # Таймауты проксирования
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 120s;
    }
}
EOF

ln -sf /etc/nginx/sites-available/karoo-trainer /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

nginx -t
check_ok "Nginx конфигурация валидна"

systemctl reload nginx
print_ok "Nginx перезапущен"

# ─────────────────────── SSL (Let's Encrypt) ───────────────────────
print_header "Получение SSL-сертификата"

echo ""
echo -e "${YELLOW}  Для SSL-сертификата нужно, чтобы DNS вашего домена${NC}"
echo -e "${YELLOW}  уже указывал на IP этой VM. Если DNS ещё не настроен —${NC}"
echo -e "${YELLOW}  нажми n, чтобы пропустить и настроить позже.${NC}"
echo ""
read -p "Получить SSL-сертификат сейчас? (y/n): " SSL_CONFIRM

if [ "$SSL_CONFIRM" = "y" ] || [ "$SSL_CONFIRM" = "Y" ]; then
    certbot --nginx \
        -d "$DOMAIN" \
        --non-interactive \
        --agree-tos \
        --email "$EMAIL" \
        --redirect
    check_ok "SSL-сертификат установлен"

    systemctl enable certbot.timer
    print_ok "Автообновление SSL настроено"
else
    print_warn "SSL пропущен. Настрой потом: sudo certbot --nginx -d $DOMAIN"
fi

# ─────────────────────── ЛОГРОТЕЙТ ───────────────────────
print_header "Настройка ротации логов"

cat > /etc/logrotate.d/karoo-trainer << 'LOGROTATE_EOF'
/var/log/karoo/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 karoo karoo
    sharedscripts
    postrotate
        systemctl reload karoo-trainer > /dev/null 2>&1 || true
    endscript
}
LOGROTATE_EOF
print_ok "Ротация логов настроена (14 дней)"

# ─────────────────────── ИНИЦИАЛИЗАЦИЯ БД ───────────────────────
print_header "Инициализация базы данных"

# Спрашиваем данные первого администратора
echo ""
echo -e "${YELLOW}  Создание первого администратора:${NC}"
echo ""
read -p "  Имя администратора (по умолчанию admin): " ADMIN_USER
ADMIN_USER=${ADMIN_USER:-admin}
read -p "  Email администратора: " ADMIN_EMAIL
read -s -p "  Пароль администратора: " ADMIN_PASS
echo ""

if [ -z "$ADMIN_EMAIL" ] || [ -z "$ADMIN_PASS" ]; then
    print_error "Email и пароль администратора обязательны!"
    exit 1
fi

# Передаём данные через переменные окружения
ADMIN_USER="$ADMIN_USER" ADMIN_EMAIL="$ADMIN_EMAIL" ADMIN_PASS="$ADMIN_PASS" \
sudo -u karoo bash << 'INIT_EOF'
set -e
cd /opt/karoo-trainer
source venv/bin/activate
python3 -c "
import os
from app import create_app
from models import db, User

app = create_app()
with app.app_context():
    db.create_all()
    print('✓ Таблицы БД созданы')

    admin_username = os.environ.get('ADMIN_USER', 'admin')
    admin_email = os.environ.get('ADMIN_EMAIL', '')
    admin_pass = os.environ.get('ADMIN_PASS', '')

    if admin_email and admin_pass:
        existing = User.query.filter(
            (User.username == admin_username) | (User.email == admin_email)
        ).first()

        if existing:
            print(f'⚠ Пользователь {admin_username} уже существует — пропускаю')
        else:
            admin = User(
                username=admin_username,
                email=admin_email,
                ftp=250,
                is_verified=True,
                is_admin=True,
            )
            admin.set_password(admin_pass)
            db.session.add(admin)
            db.session.commit()
            print(f'✓ Администратор {admin_username} создан')
"
INIT_EOF
check_ok "База данных инициализирована, администратор создан"

# ─────────────────────── ЗАПУСК ───────────────────────
print_header "Запуск приложения"

systemctl enable karoo-trainer
systemctl start karoo-trainer
check_ok "Karoo Trainer запущен"

# ─────────────────────── ФИНАЛЬНАЯ ПРОВЕРКА ───────────────────────
print_header "Проверка безопасности"

# Проверка что Gunicorn слушает только localhost
GUNICORN_BIND=$(ss -tlnp | grep gunicorn | awk '{print $4}' | head -1)
if echo "$GUNICORN_BIND" | grep -q "127.0.0.1"; then
    print_ok "Gunicorn слушает только 127.0.0.1 (не доступен снаружи)"
else
    print_warn "Gunicorn: проверь привязку — $GUNICORN_BIND"
fi

# Проверка PostgreSQL
PG_BIND=$(ss -tlnp | grep postgres | awk '{print $4}' | head -1)
if echo "$PG_BIND" | grep -q "127.0.0.1"; then
    print_ok "PostgreSQL слушает только 127.0.0.1"
else
    print_warn "PostgreSQL: проверь привязку — $PG_BIND"
fi

# Проверка прав .env
ENV_PERMS=$(stat -c "%a" "$INSTALL_DIR/.env" 2>/dev/null || stat -f "%Lp" "$INSTALL_DIR/.env" 2>/dev/null)
if [ "$ENV_PERMS" = "600" ]; then
    print_ok ".env имеет правильные права (600)"
else
    print_warn ".env права: $ENV_PERMS (рекомендуется 600)"
fi

# Проверка UFW
UFW_STATUS=$(ufw status 2>/dev/null | head -1)
if echo "$UFW_STATUS" | grep -q "active"; then
    print_ok "UFW файрвол активен"
else
    print_warn "UFW: статус неизвестен"
fi

# Проверка Fail2ban
F2B_STATUS=$(systemctl is-active fail2ban 2>/dev/null || echo "inactive")
if [ "$F2B_STATUS" = "active" ]; then
    print_ok "Fail2ban активен"
else
    print_warn "Fail2ban: $F2B_STATUS"
fi

# ─────────────────────── ФИНАЛ ───────────────────────
clear
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                        ║${NC}"
echo -e "${GREEN}║          ✅  DEPLOY ЗАВЕРШЁН УСПЕШНО!  ✅              ║${NC}"
echo -e "${GREEN}║                                                        ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${CYAN}Ваш сайт:${NC}      https://${DOMAIN}"
echo -e "  ${CYAN}Админ-панель:${NC}  https://${DOMAIN}/admin"
echo -e "  ${CYAN}Локальный:${NC}     http://127.0.0.1:8000"
echo -e "  ${CYAN}SSH:${NC}           ssh -p $SSH_PORT user@${DOMAIN}"
echo -e "  ${CYAN}Логи:${NC}          /var/log/karoo/"
echo -e "  ${CYAN}Конфиг:${NC}         /opt/karoo-trainer/.env"
echo -e "  ${CYAN}Код:${NC}            /opt/karoo-trainer/"
echo ""
echo -e "  ${YELLOW}═══ Администратор ═══${NC}"
echo "    Логин:    ${ADMIN_USER}"
echo "    Email:    ${ADMIN_EMAIL}"
echo "    Пароль:   ${ADMIN_PASS}"
echo ""
echo -e "  ${RED}⚠ Сохрани пароль администратора — он больше не будет показан!${NC}"
echo ""
echo -e "  ${YELLOW}═══ Безопасность ═══${NC}"
echo "    UFW:             $(ufw status | head -2 | tail -1)"
echo "    Fail2ban:        $(systemctl is-active fail2ban)"
echo "    SSH порт:        $SSH_PORT"
echo "    SSH ключи:       парольная аутентификация ВЫКЛЮЧЕНА"
echo ""
echo -e "  ${YELLOW}═══ Полезные команды ═══${NC}"
echo "    systemctl status karoo-trainer    — статус сервиса"
echo "    systemctl restart karoo-trainer   — перезапуск"
echo "    journalctl -u karoo-trainer -f    — логи в реальном времени"
echo "    nano /opt/karoo-trainer/.env      — изменить настройки"
echo "    fail2ban-client status sshd       — забаненные IP"
echo "    ufw status                        — правила файрвола"
echo ""
echo -e "  ${YELLOW}═══ Данные БД ═══${NC}"
echo "    База:    karoo_db"
echo "    Юзер:    karoo_user"
echo "    Пароль:  ${DB_PASSWORD}"
echo ""
echo -e "  ${RED}⚠ Сохрани пароль БД — он больше не будет показан!${NC}"
echo ""
echo -e "  ${RED}⚠ ВАЖНО: Если ты подключён по SSH — переподключись${NC}"
echo -e "  ${RED}  по новому порту (${SSH_PORT}) ТЕПЕРЬ, пока не закрыл сессию!${NC}"
echo ""
