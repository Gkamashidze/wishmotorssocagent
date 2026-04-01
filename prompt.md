# Wish Motors Social Agent — Project Handoff

## 1. პროექტის სტატუსი და სტრუქტურა

პროექტის სახელი: wishmotorssocagent
GitHub: https://github.com/Gkamashidze/wishmotorssocagent
Railway: worker process, auto-deploy main branch-იდან. პოლინგ რეჟიმი (არა webhook).

### ფაილები

src/bot.py — Telegram bot. scheduler (ორშ+ხუთ 10:00 საქ.), /generate ბრძანება, approve/regenerate ღილაკები.
src/content.py — Gemini prompt-ები, PART_EN/PART_KA სისტემა, markdown გაწმენდა, საკონტაქტო ტექსტი.
src/gemini_client.py — Gemini 2.5-flash ტექსტი + Imagen 4.0 სურათი REST API-ით.
src/image_overlay.py — Pillow ბანერი. NotoSansGeorgian-Bold.ttf ქართულისთვის, NotoSans-Regular.ttf WISH MOTORS-ისთვის. ფონტები /tmp/-ში.
src/facebook_client.py — Facebook Graph API v21.0, page + group.
src/database.py — SQLite + SQLAlchemy, /tmp/wishmotors.db.
src/config.py — .env ცვლადები.
requirements.txt — google-genai>=1.0.0, Pillow>=10.0.0, python-telegram-bot[job-queue]>=21.0, requests>=2.32.0, python-dotenv>=1.0.0, sqlalchemy>=2.0.0
Procfile — worker: python -m src.bot

### Railway env variables
TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, GEMINI_API_KEY, FB_PAGE_ID, FB_GROUP_ID, FB_PAGE_ACCESS_TOKEN

---

## 2. ინფრასტრუქტურა

GitHub: main branch. ყველა ცვლილება push-ზე Railway ავტომატურად ხელახლა deploy-ს აკეთებს.
Railway: worker process მუშაობს. polling რეჟიმი. scheduler job_queue-ით: ორშ+ხუთ 06:00 UTC = 10:00 საქართველო.
Facebook: Graph API v21.0. FB_PAGE_ACCESS_TOKEN Railway-ის env-ში.
Gemini API key: Wish Motors Google Cloud პროექტიდან. Gemini API ჩართულია.

---

## 3. სად გავჩერდით / ბოლო ბაგი

ბოლო commit: 23f87d5 — "fix: strip non-Georgian chars from banner text to prevent square glyphs"

პრობლემა იყო: NotoSansGeorgian-Bold.ttf ფონტს მხოლოდ ქართული გლიფები აქვს. "/" ან "—" ან ნებისმიერი ASCII სიმბოლო ბანერზე □ (კვადრატი) გამოდიოდა.

გამოსწორება src/image_overlay.py-ში (სტრიქონი 62-63):
  part_ka = re.sub(r'[^\u10A0-\u10FF\u2D00-\u2D2F\s]', ' ', part_ka)
  part_ka = re.sub(r' {2,}', ' ', part_ka).strip()

ანუ regex ფილტრავს ყველა სიმბოლოს გარდა ქართული Unicode ბლოკისა (U+10A0–U+10FF) და სფეისისა.

fix გაგზავნილია Railway-ზე. საჭიროა: /generate Telegram-ში გაშვება და შემოწმება რომ ბანერზე კვადრატი აღარ ჩანდეს.

თუ კვადრატი კვლავ ჩანს — კიდევ ერთხელ შეამოწმე image_overlay.py სტრ. 62-63 და regex-ის Unicode range.

---

## 4. ტოკენების დაზოგვის წესები ახალ ჩატში

- პასუხები მოკლე და ქართულად.
- მთლიანი ფაილის კოდი ნუ დაბეჭდავ — მხოლოდ შესაბამისი ნაწილი (diff სტილი).
- Read ინსტრუმენტი გამოიყენე მხოლოდ კონკრეტული ფაილისთვის, არ წაიკითხო ყველა ფაილი ერთდროულად.
- ერთ ნაბიჯზე ერთი ცვლილება — არ გაერთიანო მრავალი fix ერთ commit-ში.
- ახსნა-განმარტება 1-2 წინადადებით. ტექნიკური დეტალები მხოლოდ თუ მომხმარებელი ითხოვს.
- checkpoint (git commit) ყოველი მნიშვნელოვანი ცვლილების შემდეგ, არ დაელოდო session-ის ბოლოს.
- Railway-ს deploy-ის შემდეგ ყოველთვის სთხოვე მომხმარებელს /generate-ით გატესტვა — სკრინშოტი ადასტურებს.
