#!/usr/bin/env bash
#
#   Скрипт исправления проблем после деплоя:
#     1. Права доступа — Nginx не видит CSS/JS
#     2. Миграция БД — нет колонки is_admin и таблицы admin_logs
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

INSTALL_DIR="/opt/karoo-trainer"

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Запусти от root: sudo ./fix_deploy.sh${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Исправление проблем деплоя...${NC}"
echo ""

# ─────────────────────── 1. ПРАВА ДОСТУПА ───────────────────────
echo "1. Исправление прав доступа..."

chown -R karoo:karoo "$INSTALL_DIR"

chmod 755 "$INSTALL_DIR"
find "$INSTALL_DIR/static" -type d -exec chmod 755 {} \;
find "$INSTALL_DIR/static" -type f -exec chmod 644 {} \;
find "$INSTALL_DIR/templates" -type d -exec chmod 755 {} \;
find "$INSTALL_DIR/templates" -type f -exec chmod 644 {} \;
chmod 755 "$INSTALL_DIR/generator" 2>/dev/null || true
find "$INSTALL_DIR/generator" -type f -name "*.py" -exec chmod 644 {} \;
chmod 600 "$INSTALL_DIR/.env" 2>/dev/null || true

usermod -aG karoo www-data 2>/dev/null || true

echo -e "  ${GREEN}✓ Права исправлены${NC}"
echo ""

# ─────────────────────── 2. МИГРАЦИЯ БД ───────────────────────
echo "2. Миграция базы данных..."

sudo -u karoo bash << 'MIGRATE_EOF'
set -e
cd /opt/karoo-trainer
source venv/bin/activate

python3 -c "
from app import create_app
from models import db

app = create_app()
with app.app_context():
    inspector = db.inspect(db.engine)

    # Добавить is_admin если нет
    users_cols = {c['name'] for c in inspector.get_columns('users')}
    if 'is_admin' not in users_cols:
        db.session.execute(db.text('ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE'))
        db.session.commit()
        print('  ✓ Колонка is_admin добавлена')
    else:
        print('  ✓ Колонка is_admin уже есть')

    # Создать admin_logs если нет
    tables = {t for t in inspector.get_table_names()}
    if 'admin_logs' not in tables:
        db.session.execute(db.text(\"\"\"
            CREATE TABLE admin_logs (
                id INTEGER PRIMARY KEY,
                admin_id INTEGER NOT NULL REFERENCES users(id),
                action VARCHAR(50) NOT NULL,
                target_type VARCHAR(50) NOT NULL,
                target_id INTEGER,
                details TEXT DEFAULT '',
                ip_address VARCHAR(45),
                created_at DATETIME
            )
        \"\"\"))
        db.session.commit()
        print('  ✓ Таблица admin_logs создана')
    else:
        print('  ✓ Таблица admin_logs уже есть')
"
MIGRATE_EOF

echo -e "  ${GREEN}✓ Миграция завершена${NC}"
echo ""

# ─────────────────────── 3. ПЕРЕЗАПУСК ───────────────────────
echo "3. Перезапуск сервисов..."

systemctl restart karoo-trainer 2>/dev/null && echo -e "  ${GREEN}✓ karoo-trainer перезапущен${NC}" || echo -e "  ${YELLOW}⚠ karoo-trainer не найден (dev-режим?)${NC}"
systemctl reload nginx 2>/dev/null && echo -e "  ${GREEN}✓ nginx перезагружен${NC}" || echo -e "  ${YELLOW}⚠ nginx не найден${NC}"

echo ""
echo -e "${GREEN}Готово!${NC}"
echo ""
