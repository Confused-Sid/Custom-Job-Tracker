Option A: Run on GitHub Actions (Free & Automated)

​Fork this repository.
​Go to your repository Settings -> Secrets and variables -> Actions.
​Add three new repository secrets: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, and GEMINI_API_KEY.
​To change the notification time: Open .github/workflows/run_bot.yml and edit the cron schedule on line 5 (default is 02:30 UTC / 08:00 AM IST).

​Option B: Run Locally or on a Server

​Clone or download this repository.
​Rename .env.example to .env and paste your API keys inside.
​Update profile.txt with your specific job search criteria.
​Run python bot.py.
