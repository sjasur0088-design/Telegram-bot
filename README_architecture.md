# Final Full Customs Bot

Files:
- bot.py
- product_db_final_full.json
- requirements.txt

Railway variables:
- BOT_TOKEN
- ADMIN_CHAT_ID
- ADMIN_PHONE
- PRODUCT_DB_PATH=product_db_final_full.json
- ANALYTICS_DB_PATH=analytics.db
- OPENAI_API_KEY=your_openai_api_key   # optional but required for AI enhancement
- OPENAI_MODEL=gpt-4.1-mini            # optional

What this version does:
- stronger TN VED template DB from uploaded Excel
- customs duty template from PP-3818
- VAT 12%
- excise hints from Tax Code arts. 289¹–289³
- util fee hints from Resolution 347
- broker PRO requests
- analytics (/analytics, /stats for admin)
- optional OpenAI enhancement if OPENAI_API_KEY is set
