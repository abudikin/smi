# SMI — новостной дайджест

## Структура проекта

```
smi/
  digest.py          — скрипт дайджеста (Python)
  sources.json       — список RSS/Telegram-источников
  scraper/           — GitHub Actions-скрапер Telegram-каналов
  admin/             — Next.js-админка
  .github/workflows/ — автоматизация
```

---

## Быстрый старт (digest.py)

```bash
pip install -r requirements.txt
cp .env.example .env   # заполните ключи
python digest.py --verbose
```

Флаги: `--limit N`, `--format html|json|text`, `--output file`.

---

## Telegram-скрапер (GitHub Actions → GitHub Pages)

Скрапер обходит `t.me/s/{channel}` на серверах GitHub (за рубежом) и публикует
RSS-фиды на GitHub Pages. Ваш digest.py и админка читают эти фиды — VPN не нужен.

### Разовая настройка

1. Запушьте репозиторий на GitHub.
2. Откройте **Settings → Pages → Source** и выберите **GitHub Actions**.
3. В **Settings → Variables → Repository variables** добавьте:
   ```
   FEED_BASE_URL = https://<user>.github.io/<repo>
   ```
4. Запустите workflow вручную: **Actions → Telegram Feeds → Run workflow**.
5. Через ~1 минуту проверьте `https://<user>.github.io/<repo>/meduzalive.xml`.

### Подключение к digest.py

В файле `.env`:
```
TG_FEED_BASE=https://<user>.github.io/<repo>
```

Скрипт поставит ваш фид первым в списке кандидатов для каждого Telegram-канала.
Если фид недоступен — автоматически упадёт на публичные мосты (tg.i-c-a.su и др.).

### Добавить/убрать канал

Отредактируйте `scraper/channels.json`:
```json
[
  { "channel": "meduzalive", "label": "Meduza Live" },
  { "channel": "rian_ru",    "label": "RIA News" }
]
```
Следующий запуск workflow подхватит изменения автоматически.

---

## Админка Next.js (admin/)

```bash
cd admin
cp .env.example .env   # заполните DATABASE_URL
npm install
npm run prisma:migrate
npm run dev
```

Доступна на `http://localhost:3000`.
Переменная `TG_FEED_BASE` в `admin/.env` подключает GitHub Pages-фиды к административному
интерфейсу так же, как и в digest.py.
