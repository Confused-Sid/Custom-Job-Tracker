import os
import time
import requests
import feedparser
import json
import urllib.parse
from bs4 import BeautifulSoup
from google import genai
from googlenewsdecoder import gnewsdecoder
from dotenv import load_dotenv  # <--- Add this import

# Load environment variables from the hidden .env file (if it exists)
load_dotenv()  # <--- Execute it right away

# --- CONFIGURATION & CREDENTIALS ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not all([TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, GEMINI_API_KEY]):
    raise ValueError("Missing credentials! Please set up your .env file or GitHub Secrets.")

client = genai.Client(api_key=GEMINI_API_KEY)
HISTORY_FILE = "seen_jobs.txt"

# Local pre-filter to skip non-recruitment noise
IGNORE_TITLE_KEYWORDS = [
    "cutoff", "cut off", "syllabus", "exam date", "answer key", "admit card",
    "analysis", "how to crack", "college-wise", "offer", "round-wise", 
    "placements, fees", "coaching", "curriculum", "scholarship", "cleaning service",
    "keyboard", "switch type", "gaming"
]

def decode_google_news_url(url):
    """Decodes encrypted Google News URLs into the actual publisher URLs."""
    if "news.google.com/rss/articles" in url:
        try:
            decoded = gnewsdecoder(url, interval=0)
            if decoded and decoded.get("status"):
                return decoded.get("decoded_url")
        except Exception:
            pass
    return url

def load_seen_jobs():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return set(line.strip().lower() for line in f if line.strip())
    return set()

def save_seen_job(identifier):
    if identifier:
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(identifier.strip().lower() + "\n")

def load_profile_and_generate_feeds():
    dynamic_feeds = ["https://www.freejobalert.com/feed/"]
    evaluation_criteria = "B.Tech Mechanical Engineering graduate looking for entry-level PSU/Government jobs."
    
    if os.path.exists("profile.txt"):
        with open("profile.txt", "r", encoding="utf-8") as f:
            content = f.read()
            
        if "[SEARCH_KEYWORDS]" in content and "[EVALUATION_CRITERIA]" in content:
            parts = content.split("[EVALUATION_CRITERIA]")
            keywords_block = parts[0].replace("[SEARCH_KEYWORDS]", "").strip()
            evaluation_criteria = parts[1].strip()
            
            for line in keywords_block.splitlines():
                kw = line.strip()
                if kw:
                    encoded_query = urllib.parse.quote(kw)
                    feed_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
                    dynamic_feeds.append(feed_url)
        else:
            evaluation_criteria = content.strip()
            
    return dynamic_feeds, evaluation_criteria

def send_telegram_alert(data, is_test=False):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    if is_test:
        message = "✅ **PSU & Govt Job Tracker is Online!**\nScanning feeds using smart pre-filtering, AI matching, and deduplication..."
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    else:
        title = data.get("title", "Government / PSU Recruitment")
        eligibility = data.get("eligibility", "B.Tech / B.E. Mechanical")
        vacancies = data.get("vacancies", "Refer Notification")
        salary = data.get("salary", "As per Govt / PSU Pay Scale")
        deadline = data.get("deadline_formatted", "Refer Notification")
        
        official_link = data.get("official_link", "").strip()
        source_url = data.get("source_url", "").strip()
        calendar_url = data.get("calendar_url", "")

        # Build clean link lines
        official_text = f"[Official Portal]({official_link})" if official_link else "Check Notification"
        source_text = f"[Source Article]({source_url})" if source_url else "N/A"

        message = (
            f"🏛️ *{title}*\n\n"
            f"🎓 *Eligibility:* {eligibility}\n"
            f"📌 *Vacancies:* {vacancies}\n"
            f"💰 *Pay Scale:* {salary}\n"
            f"🗓️ *Last Date:* {deadline}\n\n"
            f"🌐 *Official Link:* {official_text}\n"
            f"📰 *Post Link:* {source_text}"
        )

        # Build interactive inline buttons
        button_row_1 = []
        if official_link:
            button_row_1.append({"text": "🌐 Official Portal", "url": official_link})
        if source_url:
            button_row_1.append({"text": "📰 Source Post", "url": source_url})

        buttons = []
        if button_row_1:
            buttons.append(button_row_1)
        if calendar_url:
            buttons.append([{"text": "📅 Set Reminder", "url": calendar_url}])

        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }
        if buttons:
            payload["reply_markup"] = {"inline_keyboard": buttons}
    
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"--> Telegram Connection Error: {e}")

def get_page_details_and_links(url):
    """Extracts page text and discovers candidate official links."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        text_content = soup.get_text(separator=' ', strip=True)[:2500]
        
        found_links = set()
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href'].strip()
            if href.startswith("http") and any(domain in href.lower() for domain in ['.gov.in', '.nic.in', 'ojas', 'iocl', 'drdo', 'isro', 'bhel', 'ongc', 'digialm', 'apply', 'career', 'recruitment']):
                found_links.add(href)
                
        links_block = "\nFound Outbound Links:\n" + "\n".join(list(found_links)[:10])
        return text_content + links_block
    except:
        return ""

def create_calendar_url(title, date_str):
    if not date_str or len(date_str) != 8:
        return None
    base_url = "https://calendar.google.com/calendar/render?action=TEMPLATE"
    return f"{base_url}&text={urllib.parse.quote('Deadline: ' + title)}&dates={date_str}/{date_str}"

def batch_evaluate_with_gemini(jobs_list, user_profile):
    if not jobs_list:
        return []
        
    prompt = f"""USER PROFILE & CRITERIA:
{user_profile}

Evaluate each job posting below against the user profile.
For any job that matches (YES):
1. Extract a normalized unique 'job_key'.
2. Extract the clean Title, Eligibility, Vacancies, Pay Scale/Salary, and Deadline.
3. If an official portal link is present, extract it as 'official_link'.

Return a raw JSON array containing ONLY matched jobs. If none match, return `[]`.

Required JSON format:
[
  {{
    "job_id": <the integer ID from prompt>,
    "job_key": "UNIQUE_RECRUITMENT_KEY",
    "title": "Clean Role & Organization Name",
    "eligibility": "B.E. / B.Tech Mechanical Engineering",
    "vacancies": "e.g., 470 Posts",
    "salary": "e.g., Rs. 50,000 - 1,60,000",
    "deadline_formatted": "e.g., 31 August 2026",
    "deadline_date": "YYYYMMDD",
    "official_link": "https://..."
  }}
]

JOB POSTINGS TO EVALUATE:
"""
    for i, job in enumerate(jobs_list):
        prompt += f"\n--- JOB ID: {i} ---\nSource URL: {job['source_url']}\nTitle: {job['title']}\nContent & Links:\n{job['details']}\n"

    try:
        print("--> Evaluating batch with gemini-3.5-flash...")
        chat = client.chats.create(model='gemini-3.5-flash')
        response = chat.send_message(prompt)
        
        clean_text = response.text.replace('```json', '').replace('```', '').strip()
        matched_jobs = json.loads(clean_text)
        print(f"    [Gemini API] Found {len(matched_jobs)} match(es) out of {len(jobs_list)} items.")
        return matched_jobs
    except Exception as e:
        print(f"    [Gemini API Error]: {e}")
        return []

def check_for_jobs():
    print("Starting PSU & Govt Job Tracker...")
    feeds_list, user_profile = load_profile_and_generate_feeds()
    seen_jobs = load_seen_jobs()
    
    print(f"--> Loaded {len(seen_jobs)} previously tracked identifiers.")
    send_telegram_alert(None, is_test=True)
    
    jobs_to_evaluate = []
    original_jobs_data = {}
    job_counter = 0
    
    print("\nGathering unread postings across feeds...")
    for feed_url in feeds_list:
        print(f"--- Scraping: {feed_url} ---")
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            r = requests.get(feed_url, headers=headers, timeout=10)
            feed = feedparser.parse(r.text)
        except:
            continue
            
        for entry in feed.entries[:8]:
            raw_job_link = entry.link
            job_title = entry.title
            
            if raw_job_link.lower() in seen_jobs:
                continue
                
            title_lower = job_title.lower()
            if any(junk in title_lower for junk in IGNORE_TITLE_KEYWORDS):
                continue
            
            job_link = decode_google_news_url(raw_job_link)
            
            if job_link.lower() in seen_jobs and job_link != raw_job_link:
                continue

            full_details = get_page_details_and_links(job_link)
            if not full_details:
                full_details = getattr(entry, 'summary', '')
                
            jobs_to_evaluate.append({
                "title": job_title,
                "source_url": job_link,
                "details": full_details
            })
            
            original_jobs_data[job_counter] = {
                "title": job_title,
                "source_url": job_link,
                "raw_source_url": raw_job_link
            }
            job_counter += 1

    if not jobs_to_evaluate:
        print("No eligible unread jobs found to evaluate.")
        return
        
    print(f"\nEvaluating {len(jobs_to_evaluate)} pre-filtered jobs in ONE batch call...")
    matches = batch_evaluate_with_gemini(jobs_to_evaluate, user_profile)
    
    for match in matches:
        job_id = match.get("job_id")
        job_key = match.get("job_key", "").lower().strip()
        official_link = match.get("official_link", "").lower().strip()
        
        if job_key and job_key in seen_jobs:
            continue
        if official_link and official_link in seen_jobs:
            continue

        if job_id is not None and job_id in original_jobs_data:
            job_info = original_jobs_data[job_id]
            match["source_url"] = job_info["source_url"]
            deadline_date = match.get("deadline_date", "")
            
            cal_url = create_calendar_url(match.get("title", job_info["title"]), deadline_date)
            match["calendar_url"] = cal_url
            
            send_telegram_alert(match)
            
            save_seen_job(job_info["source_url"])
            seen_jobs.add(job_info["source_url"].lower())
            save_seen_job(job_info["raw_source_url"])
            seen_jobs.add(job_info["raw_source_url"].lower())
            
            if official_link:
                save_seen_job(official_link)
                seen_jobs.add(official_link)
            if job_key:
                save_seen_job(job_key)
                seen_jobs.add(job_key)
                
            print(f"    --> Dispatched Alert: {match.get('title')}")

if __name__ == "__main__":
    check_for_jobs()
