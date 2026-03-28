# Customs Bot — GitHub + Railway Ready

## Что внутри
- `bot.py` — готовый бот с:
  - поиском ТН ВЭД
  - блоком для брокеров
  - платными заявками
  - админ-панелью `/admin`
  - SQLite базой заявок и аналитики
- `product_db_part1..6.json` — база ТН ВЭД
- `requirements.txt`
- `Procfile`
- `railway.json`
- `nixpacks.toml`
- `.env.example`

## Railway Variables
Добавь в Railway:
- `BOT_TOKEN`
- `OPENAI_API_KEY`
- `OPENAI_MODEL=gpt-4.1-mini`
- `ADMIN_CHAT_ID` — твой Telegram user id
- `ANALYTICS_DB_PATH=/data/analytics.db`

## Важно
Для сохранения заявок и аналитики после деплоя добавь в Railway Volume и используй путь `/data/analytics.db`.

## Команды
- `/start` — запуск бота
- `/myid` — узнать свой Telegram ID
- `/analytics` — базовая аналитика
- `/admin` — панель администратора

## Что делает админ-панель
- показывает новые заявки
- показывает заявки в работе
- показывает завершённые заявки
- позволяет взять заявку в работу
- позволяет закрыть заявку
- показывает контакт клиента
