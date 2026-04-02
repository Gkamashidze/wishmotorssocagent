# Wish Motors Social Agent — Project Handoff

## Claude-ს ინსტრუქცია სესიის დასაწყისში

ამ ფაილის წაკითხვის შემდეგ მიპასუხე მხოლოდ **"მზად ვარ"** და დაელოდე მომხმარებლის კითხვას.
არ განმეორდე ფაილის შინაარსი. არ სვა კითხვები. არ შეთავაზო ახალი ფუნქციები.

### სამუშაო წესები
- ენა: **ქართული** (კოდი და ტექნიკური ტერმინები ინგლისურად)
- პასუხები: მოკლე და კონკრეტული — 1-2 წინადადება, შემდეგ კოდი
- ყოველი ცვლილების შემდეგ: `git add → commit → push` ავტომატურად
- ერთი ცვლილება = ერთი commit — არ გააერთიანო მრავალი fix
- Railway deploy ხდება push-ზე ავტომატურად
- `/generate` Telegram-ში = ტესტი

### სწრაფი ბმულები
- Facebook Graph API Explorer: https://developers.facebook.com/tools/explorer/
  - Meta App: **Wish Motors** | User or Page: **Wish Motors • ვიშ მოტორს**
  - საჭირო permissions: `pages_manage_posts`, `pages_manage_metadata`, `pages_read_engagement`
- GitHub: https://github.com/Gkamashidze/wishmotorssocagent
- Railway: https://railway.app (project: artistic-wonder, service: wishmotorssocagent)

---

## პროექტის სტატუსი

**Wish Motors** — SsangYong-ის სპეციალიზებული ცენტრი ბათუმში.
Bot ქმნის Facebook პოსტებს (ქართული ტექსტი + AI სურათი) და აქვეყნებს გვერდსა და ჯგუფში.

**ბოლო commit:** ae3b3bb — fix: delete button handler, explicit UTF-8 charset for emoji in caption
**Railway:** Online, worker process, polling რეჟიმი
**სქემა:** SQLite @ `/data/wishmotors.db` (Railway Volume) ან `/tmp/` fallback

---

## ფაილები

| ფაილი | როლი |
|-------|------|
| `src/bot.py` | Telegram bot — scheduler, /generate, /stop, approve/regenerate/retry/delete ღილაკები |
| `src/content.py` | Gemini prompt-ები, PART_EN/PART_KA, markdown გაწმენდა |
| `src/gemini_client.py` | Gemini 2.5-flash ტექსტი + Imagen 4.0 სურათი, retry + client singleton |
| `src/facebook_client.py` | Graph API v21.0, page + group, verify_post, retry |
| `src/image_overlay.py` | Pillow ბანერი — NotoSansGeorgian-Bold.ttf (ქართ.), NotoSans-Regular.ttf |
| `src/database.py` | SQLite + SQLAlchemy, `_resolve_db_url()` — /data/ ან /tmp/ |
| `src/config.py` | .env ცვლადები, frozen dataclass |

---

## ინფრასტრუქტურა

- **GitHub:** main branch → Railway ავტო-deploy
- **Railway:** worker process, `restartPolicyType: ON_FAILURE`
- **Scheduler:** ორშ+ხუთ 06:00 UTC = 10:00 საქართველო, `misfire_grace_time: 60`
- **Railway env variables:** `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `GEMINI_API_KEY`, `FB_PAGE_ID`, `FB_GROUP_ID`, `FB_PAGE_ACCESS_TOKEN`, `FB_USER_ACCESS_TOKEN`
- **Railway Volume:** `/data` — DB-ს ინახავს restart-ებს შორის

---

## ტოკენები

| ცვლადი | ტიპი | ვადა |
|--------|------|------|
| `FB_PAGE_ACCESS_TOKEN` | Permanent Page Token | არ ამოიწურება |
| `FB_USER_ACCESS_TOKEN` | Long-Lived User Token | ~59 დღე (განახლება ქვემოთ) |

### FB_USER_ACCESS_TOKEN განახლება (59 დღეში):
1. [Graph API Explorer](https://developers.facebook.com/tools/explorer/) → Generate Access Token
2. ბრაუზერში გახსენი:
   `https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=1615354862850374&client_secret=NEW_APP_SECRET&fb_exchange_token=SHORT_LIVED_TOKEN`
3. მიღებული `access_token` → Railway-ში `FB_USER_ACCESS_TOKEN`

**App ID:** 1615354862850374 (App Secret ყოველ reset-ზე იცვლება — Meta Dashboard-იდან აიღე)

### მუდმივი გამოსავალი (მომავალში):
Meta Business Manager → System User Token — **არასდროს არ ამოიწურება**

---

## ჯგუფში გამოქვეყნება — მიმდინარე სტატუსი

ჯგუფი: `publish_to_groups` App Review გარეშე არ მუშაობს.
**გამოსავალი (ჯერ სცადე):** Facebook ჯგუფი → Settings → Apps → Add Apps → Wish Motors
ამის შემდეგ `/feed?link=` endpoint-ი უნდა იმუშაოს.

---

## Bot-ის სრული ფლოუ

```
/generate
  → Gemini 2.5-flash → ქართული ტექსტი (PART_EN + PART_KA)
  → Imagen 4.0 → სურათი + Pillow overlay (ბანერი)
  → Telegram: ფოტო + ტექსტი + [✅ გამოაქვეყნე] [🔄 თავიდან]
  (გენერაციის დროს /stop = გაჩერება)

✅ გამოაქვეყნე
  → Facebook page (/photos endpoint, multipart UTF-8)
  → verify_post → permalink URL
  → group share (/feed?link=page_url)
  → Telegram: "✅ გვერდი\n✅/⚠️ ჯგუფი" + [🗑️ პოსტის წაშლა]

❌ Facebook failure
  → Telegram: შეცდომა + [🔁 ხელახლა სცადე]

🔄 თავიდან
  → mark_skipped + ახალი _generate_post იგივე კატეგორიით

🗑️ პოსტის წაშლა
  → DELETE /{post_id} → Telegram დადასტურება
```

---

## გამოსწორებული პრობლემები (ისტორია)

| პრობლემა | გამოსწორება |
|----------|-------------|
| Event loop blocking | `asyncio.to_thread` ყველა blocking call-ზე |
| DB წაიშლებოდა restart-ზე | `_resolve_db_url()` → `/data/` Railway Volume |
| API failures | Exponential backoff retry (3 attempts) Gemini + Facebook |
| გამოსახულებაზე ადამიანი | `personGeneration: dont_allow` + prompt-დან character ამოღება |
| Scheduler გარეშე დღეს | `misfire_grace_time: 60` |
| `/generate` ორჯერ გაშვება | 30-წამიანი rate limit |
| Facebook 400 | `pages_manage_posts` + `pages_manage_metadata` + `pages_read_engagement` |
| Facebook error გაუგებარი | response body parse → ნამდვილი შეცდომა Telegram-ში |
| Publish fail = ახალი generate | `🔁 ხელახლა სცადე` ღილაკი — მხოლოდ repost |
| ბანერზე □ კვადრატი | regex: მხოლოდ Georgian Unicode U+10A0–U+10FF |
| Token expired (1-2 სთ) | Permanent Page Token + Long-Lived User Token |
| ჯგუფი: permalink_url ცარიელი | `/photos` აბრუნებს `post_id` ველს — `data.get("post_id") or data.get("id")` |
| □ emoji ტექსტში | multipart: explicit `charset=utf-8` caption-ზე |
| Delete ღილაკი არ რეაგირებდა | delete handler გადავიტანეთ `_pending` check-ის წინ |
| /stop ბრძანება | `asyncio.Task` cancel — გენერაციის შეჩერება |

---

## ტოკენების დაზოგვის წესები

- **არ წაიკითხო ყველა ფაილი** — მხოლოდ ის, რასაც ეხება ცვლილება
- **diff სტილი** — მთლიანი ფაილი ნუ დაბეჭდავ
- **ახსნა 1-2 წინადადებით** — დეტალები მხოლოდ მოთხოვნისას
- **ერთი commit ერთ ნაბიჯზე** — არ დაელოდო session-ის ბოლოს
- **push ავტომატურად** — მომხმარებელს ხელით push არ სჭირდება
