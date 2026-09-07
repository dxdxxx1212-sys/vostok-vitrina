#!/usr/bin/env bash
# Поднимает НОВЫЙ каталог на поддомене витрина.восток-прицеп.рф (nginx + HTTPS).
# Отдельный /var/www/vitrina с автодеплоем (git pull каждую минуту).
# Старый каталог.восток-прицеп.рф НЕ трогается.
# Запуск на сервере (под root):
#   curl -fsSL https://dxdxxx1212-sys.github.io/vostok-vitrina/subdomain-vitrina.sh | bash
set -euo pipefail

SUB="xn--80adsazqn.xn----ctbklixakchgm2d.xn--p1ai"   # витрина.восток-прицеп.рф (punycode)
WWW="/var/www/vitrina"
REPO="https://github.com/dxdxxx1212-sys/vostok-vitrina.git"
EMAIL="admin@jefwipwero.online"

echo "==> [1/5] Пакеты..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y nginx certbot python3-certbot-nginx git

echo "==> [2/5] Контент каталога (/var/www/vitrina)..."
if [ ! -d "$WWW/.git" ]; then
  rm -rf "$WWW"
  git clone --depth 1 "$REPO" "$WWW"
else
  cd "$WWW" && git pull -q || true
fi
git config --global --add safe.directory "$WWW" || true
chown -R www-data:www-data "$WWW"

echo "==> [3/5] Конфиг nginx для витрина.восток-прицеп.рф..."
cat > /etc/nginx/sites-available/vitrina <<NGINX
server {
    listen 80;
    listen [::]:80;
    server_name ${SUB};
    root ${WWW};
    index index.html;

    location / { try_files \$uri \$uri/ =404; }
    location ~ /\. { deny all; }
    location ~* \.(sh|md|py|json)\$ { deny all; }

    # фото карточек — долгий кэш
    location ~* \.(jpg|jpeg|png|webp|svg|ico)\$ {
        expires 30d;
        add_header Cache-Control "public";
    }
}
NGINX
ln -sf /etc/nginx/sites-available/vitrina /etc/nginx/sites-enabled/vitrina
nginx -t && systemctl reload nginx

echo "==> [4/5] HTTPS (Let's Encrypt)..."
if certbot --nginx -d "${SUB}" --non-interactive --agree-tos -m "${EMAIL}" --redirect; then
  echo "    ✅ HTTPS включён"
  # HTTP/2 для nginx 1.24: параметр в строке listen 443 (идемпотентно).
  sed -i 's/listen 443 ssl;/listen 443 ssl http2;/g; s/listen \[::\]:443 ssl;/listen [::]:443 ssl http2;/g' /etc/nginx/sites-available/vitrina
  if nginx -t 2>/dev/null; then systemctl reload nginx; echo "    ✅ HTTP/2 включён"; else echo "    ⚠️ HTTP/2 не применился — проверь: nginx -t"; fi
else
  echo "    ⚠️ Сертификат пока не выпущен — скорее всего DNS ещё не указывает на сервер"
  echo "       (или есть AAAA/IPv6-запись, которую надо удалить в панели sprinthost)."
  echo "       Сайт уже работает по http://витрина.восток-прицеп.рф"
  echo "       Когда DNS разойдётся:  certbot --nginx -d ${SUB} --redirect"
fi

echo "==> [5/5] Автообновление (git pull каждую минуту)..."
( crontab -l 2>/dev/null | grep -v "cd $WWW && git pull"; echo "* * * * * cd $WWW && git pull -q >/dev/null 2>&1" ) | crontab -

echo "==> Готово! Открой: https://витрина.восток-прицеп.рф"
