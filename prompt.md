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
Bot ქმნის Facebook პოსტებს (ქართული ტექსტი + AI სურათი) და აქვეყნებს გვერდზე.

**ბოლო commit:** 910f3df — feat: add /retry command to restore pending post after Railway restart
**Railway:** Online, worker process, polling რეჟიმი
**სქემა:** SQLite @ `/data/wishmotors.db` (Railway Volume) ან `/tmp/` fallback

---

## ფაილები

| ფაილი | როლი |
|-------|------|
| `src/bot.py` | Telegram bot — scheduler, /generate, /stop, /retry, approve/regenerate/retry/delete/restore ღილაკები |
| `src/content.py` | Gemini prompt-ები, PART_EN/PART_KA, markdown გაწმენდა, 3 კატეგორია |
| `src/gemini_client.py` | Gemini 2.5-flash ტექსტი + Imagen 4.0 სურათი, retry + client singleton |
| `src/facebook_client.py` | Graph API v21.0, single-step /photos publish, verify_post, retry |
| `src/image_overlay.py` | Pillow ბანერი — NotoSansGeorgian-Bold.ttf (ქართ.), NotoSans-Regular.ttf |
| `src/database.py` | SQLite + SQLAlchemy, `_resolve_db_url()`, `get_last_pending_post()` |
| `src/config.py` | .env ცვლადები, frozen dataclass |

---

## ინფრასტრუქტურა

- **GitHub:** main branch → Railway ავტო-deploy
- **Railway:** worker process, `restartPolicyType: ON_FAILURE`
- **Scheduler:** ორშ+ხუთ 06:00 UTC = 10:00 საქართველო, `misfire_grace_time: 60`
- **Railway env variables:** `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `GEMINI_API_KEY`, `FB_PAGE_ID`, `FB_PAGE_ACCESS_TOKEN`
- **Railway Volume:** `/data` — DB-ს ინახავს restart-ებს შორის

---

## ტოკენები

| ცვლადი | ტიპი | ვადა |
|--------|------|------|
| `FB_PAGE_ACCESS_TOKEN` | Permanent Page Token | არ ამოიწურება |

### FB_PAGE_ACCESS_TOKEN განახლება (საჭიროების შემთხვევაში):
1. [Graph API Explorer](https://developers.facebook.com/tools/explorer/) → Generate Access Token
2. გვერდის long-lived token მიიღე → Railway-ში განაახლე

**App ID:** 1615354862850374

---

## Facebook გამოქვეყნება — მიმდინარე სტატუსი

**ჯგუფი:** Facebook Groups API deprecated (April 2024) — სრულად ამოღებულია სისტემიდან.
**გვერდი:** `/photos` endpoint, single-step, `files=` multipart + explicit `charset=utf-8`.

### Facebook publish კოდი (facebook_client.py)
```python
files=[
    ("message", (None, message, "text/plain; charset=utf-8")),
    ("source", ("photo.jpg", image_file, "image/jpeg")),
]
```
**რატომ ასე:** `data={}` და `params={}` emoji-ს ანგრევდა (□). `files=` ერთადერთი გზაა explicit charset-ის გასაწერად multipart-ში. `attached_media` (two-step approach) ასევე ვცადეთ — error 100 "global id not allowed".

---

## Bot-ის სრული ფლოუ

```
/generate (ან ავტო-განრიგი ორშ/ხუთ 10:00)
  → Gemini 2.5-flash → ქართული ტექსტი (PART_EN + PART_KA)
  → Imagen 4.0 → სურათი + Pillow overlay (ბანერი)
  → Telegram: ფოტო + ტექსტი + [✅ გამოაქვეყნე] [🔄 თავიდან]
  (გენერაციის დროს /stop = გაჩერება)

✅ გამოაქვეყნე
  → Facebook /photos (message UTF-8 + image)
  → verify_post → permalink URL
  → Telegram: "✅ გვერდი: გამოქვეყნდა\n🔗 url" + [🗑️ პოსტის წაშლა]
  → _published cache-ში ინახება 24 სთ

⏰ 24 სთ გავიდა (ავტო-გამოქვეყნება)
  → auto_publish_check job (ყოველ 30 წუთში)
  → Facebook-ზე ავტომატურად გადის
  → Telegram: "⏰ ავტომატურად გამოქვეყნდა" + [🗑️ წაშლა]

❌ Facebook failure
  → Telegram: შეცდომა + [🔁 ხელახლა სცადე]

🔄 თავიდან
  → mark_skipped + ახალი _generate_post იგივე კატეგორიით

🗑️ პოსტის წაშლა
  → DELETE /{post_id}
  → Telegram: "🗑️ წაიშალა" + [♻️ აღდგენა (24 სთ)]

♻️ აღდგენა
  → _published cache-დან ხელახლა publish
  → Telegram: "✅ პოსტი აღდგა" + [🗑️ წაშლა]

/retry (Railway restart-ის შემდეგ)
  → DB-დან ბოლო pending პოსტი
  → Telegram-ში ხელახლა ✅/🔄 ღილაკებით
  (სურათის ფაილი /data volume-ზე უნდა იყოს)
```

---

## კატეგორიები (content.py)

| კატეგორია | თემა |
|-----------|------|
| `maintenance` | ზეთის გამოცვლა, ფილტრები, სამუხრუჭე სითხე, საბურავები, DPF |
| `electrical` | ბატარეა, გენერატორი, OBD/Check Engine, სენსორები, სტარტერი |
| `warning_signs` | ვიბრაცია, კვამლი, სუნი, სითხის წვეთები, გადაბმულობა, სამუხრუჭე ხმები |

ბრუნვა: maintenance → electrical → warning_signs → maintenance → ...

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
| Facebook Groups error 100 | Groups API deprecated (2024) — სრულად ამოღებულია |
| Publish fail = ახალი generate | `🔁 ხელახლა სცადე` ღილაკი — მხოლოდ repost |
| ბანერზე □ კვადრატი | regex: მხოლოდ Georgian Unicode U+10A0–U+10FF |
| Token expired | Permanent Page Token |
| □ emoji Facebook-ზე | `files=[(message, None, "text/plain; charset=utf-8")]` — explicit charset |
| Delete ღილაკი არ რეაგირებდა | delete handler გადავიტანეთ `_pending` check-ის წინ |
| /stop ბრძანება | `asyncio.Task` cancel |
| pending იკარგებოდა restart-ზე | `/retry` ბრძანება — DB-დან ხელახლა წამოღება |
| წაშლილი პოსტის აღდგენა | `_published` cache + ♻️ ღილაკი (24 სთ ფანჯარა) |
| 24 სთ auto-publish | `auto_publish_check` job, 30 წუთში ერთხელ |

---

## ტოკენების დაზოგვის წესები

- **არ წაიკითხო ყველა ფაილი** — მხოლოდ ის, რასაც ეხება ცვლილება
- **diff სტილი** — მთლიანი ფაილი ნუ დაბეჭდავ
- **ახსნა 1-2 წინადადებით** — დეტალები მხოლოდ მოთხოვნისას
- **ერთი commit ერთ ნაბიჯზე** — არ დაელოდო session-ის ბოლოს
- **push ავტომატურად** — მომხმარებელს ხელით push არ სჭირდება
