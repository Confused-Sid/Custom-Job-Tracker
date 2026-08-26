🚀 AI-Powered PSU & Govt Job Tracker

An automated Python bot that uses Google's Gemini AI to scan job feeds, match them against your qualifications, and send deduplicated Telegram alerts.

📂 Repository Structure
 * bot.py: The main execution script.
 * profile.txt: Your plain-English job qualifications. (Required)
 * seen_jobs.txt: Auto-generated memory file to prevent duplicate alerts.
 * .env.example: Template for your API keys.
 * run_bot.yml: GitHub Actions workflow for daily automation.


⚙️ Setup Instructions

Option A: Run via GitHub Actions (Automated & Free)
 * Fork this repository.
 * Go to Settings > Secrets and variables > Actions. Add three New Repository Secrets:
   * TELEGRAM_BOT_TOKEN
   * TELEGRAM_CHAT_ID
   * GEMINI_API_KEY
 * Edit .github/workflows/run_bot.yml to change the daily run time (default is 02:30 UTC).

Option B: Run Locally or on a Server (e.g., PythonAnywhere)
 * Clone or download the repository.
 * Rename .env.example to .env and paste your API keys inside.
 * Install requirements and run: python bot.py.


🎯 Customizing Your Search
Open profile.txt and write your exact qualifications. The Gemini AI strictly uses this text to filter jobs.
Example:
> B.Tech Mechanical Engineering graduate looking for entry-level PSU/Government jobs.
> 
(Note: If profile.txt is missing or empty, the script will throw an error and stop.)
