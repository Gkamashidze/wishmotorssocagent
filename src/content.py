from __future__ import annotations
import re

CONTACT_INFO = """
🚚 უფასო მიტანა ბათუმში! (📍 თევდორე მღვდლის #6)
📦 უფასო გზავნა მთელ საქართველოში 150 ლარზე ზევით ან 5+ ნაწილის შეძენისას!

დაგვიკავშირდით:
📞 555 966 428
💬 WhatsApp: +995 555 966 428
🔗 შემოგვიერთდით ჯგუფში: https://shorturl.at/wxMWE

Wish Motors — SsangYong-ის სპეციალიზებული ცენტრი ბათუმში! 🚀🌟"""

_EXAMPLE_POST = """📏 იცით თუ არა, რამდენი ლიტრი ზეთი სჭირდება თქვენს SsangYong-ს? ✅

SsangYong-ის მოდელებს შორის ძრავის ზეთის მოცულობა მკვეთრად განსხვავდება.
Wish Motors-ში ვიცავთ მხოლოდ მწარმოებლის (OEM) სტანდარტებს:

🔹 Korando Sports / C / Turismo (2.0/2.2 Diesel): 6.0 ლ — 5W-30 (MB 229.51)
🔹 Rexton G4 / Sports (2.2 Diesel): 8.5 ლ — 5W-30 (MB 229.51)
🔹 Tivoli / XLV (1.6): 5.3 ლ (დიზ) / 4.5 ლ (ბენზ) — 5W-30
🔹 Torres (1.5 Turbo): 5.0 ლ — 0W-20 (C5) ან 5W-30 (C3)

Wish Motors-ში ყველაფერი გამჭვირვალეა — ზუსტად იცით რა ისხმება! ✨"""

_MAINTENANCE_TOPICS = """
ეხებოდეს ერთ-ერთ ამ თემას (ყველაზე სასარგებლოს ამჯამად):
- ძრავის ზეთის გამოცვლა — ზუსტი მოცულობა SsangYong-ის მოდელების მიხედვით
- ჰაერის ფილტრის ან ზეთის ფილტრის გამოცვლა — ნიშნები და სარგებელი
- სამუხრუჭე სითხე ან გამაცივებელი სითხე — როდის და რატომ
- სამუხრუჭე ხუნდები / დისკები — ნახვის სიხშირე, ნიშნები
- DPF ფილტრი — რა არის, SsangYong-ის დიზელ მოდელებზე
- საბურავები — ზეწოლა, ბრუნვა, სეზონური გამოცვლა
"""

_ELECTRICAL_TOPICS = """
ეხებოდეს ერთ-ერთ ამ თემას (ყველაზე სასარგებლოს ამჯამად):
- ავტომობილის ბატარეა — ნიშნები, ვადა, SsangYong-ის სპეციფიკა
- გენერატორი — გაფუჭების სიმპტომები, დიაგნოსტიკა
- OBD/Check Engine — რას ნიშნავს სიგნალი, ჩვენთან დიაგნოსტიკა
- სენსორები (MAF, O2, ტემპერატურა) — რა როლი აქვთ
- სტარტერი — სიმპტომები თუ გაჭირდა ქრა
- ავტომობილის განათება — ნათურები, ენერგოდაზოგვა
- ელ. ფანჯრები / ცენტრ. საკეტი — ხშირი პრობლემები SsangYong-ში
"""

_WARNING_SIGNS_TOPICS = """
ეხებოდეს ერთ-ერთ ამ თემას (ყველაზე სასარგებლოს ამჯამად):
- ძრავის ვიბრაცია ან უცნაური ხმა — კონკრეტულად რომელ ნაწილზე მიუთითებს
- სამუხრუჭე სისტემა — ჩხვლეტა, ვიბრაცია, ხმაური: რა ნაწილი ჭიავს
- საჭე ვიბრირებს ან ავტომობილი ერთ მხარეს იზიდება — სავალი ნაწილის ნიშნები
- შავი, თეთრი ან ლურჯი კვამლი გამონაბოლქვიდან — კონკრეტული მიზეზი
- ზეთის ან გამაცივებელი სითხის წვეთები ქვეშ — სად გვხვდება, რა ნიშნავს
- DPF / Check Engine ნათება — რომელი ნაწილია ბრალი, SsangYong-ის კონტექსტში
- უცნაური სუნი სალონში ან კაპოტქვეშ — მუხრუჭები, ზეთი, გამაცივებელი
- გადაბმულობა / АКПП — სუსტი ჩართვა, ვიბრაცია, სრიალი: პირველი ნიშნები
"""

_BASE_SYSTEM = """შენ ხარ Wish Motors-ის Facebook-ის კოპირაიტერი.
Wish Motors არის SsangYong-ის სპეციალიზებული ცენტრი ბათუმში (თევდორე მღვდლის #6).

დაწერე ინფორმაციული Facebook პოსტი. {topics}

მოთხოვნები:
- ქართულ ენაზე
- SsangYong-ის სპეციფიკური ინფო სადაც შეიძლება (Korando, Rexton, Tivoli, Torres)
- გასაგები ნებისმიერისთვის — ტექნიკური ცოდნა არ სჭირდება
- ასწავლოს, სარგებელი მოუტანოს, ნდობა ჩამოაყალიბოს
- ემოჯი-ებით მდიდარი, სათაური გამოკვეთილი
- 200–350 სიტყვა (არა გრძელი)
- ᲙᲠᲘᲢᲘᲙᲣᲚᲘ: არავითარი markdown სიმბოლოები — **, *, ***, ##, __, -, • არ გამოიყენო. სიაში ელემენტები დაიწყოს ემოჯით (🔹 ან სხვა), არა ვარსკვლავით ან დეფისით. Facebook plain text-ია.
- ᲐᲠ ჩასვა საკონტაქტო ინფო — ცალკე დაემატება ავტომატურად
- ᲐᲠ დაამატო სათაური "✍️ სარეკლამო ქოფირაითინგი" ან "სათაური:" — პოსტი პირდაპირ ემოჯი+სათაურით დაიწყოს

პოსტის ბოლოს, ბოლო სტრიქონზე დაამატე ზუსტად ასე (სხვა ტექსტი არ):
PART_EN: [the specific car part in English, e.g. "brake pads", "engine oil filter", "car battery"]
PART_KA: [იგივე ქართულად, მაგ: "სამუხრუჭე ხუნდები", "ზეთის ფილტრი", "ავტომობილის ბატარეა"]

ნიმუში (ზუსტად ამ სტილით):
{example}"""


_CATEGORIES = ["maintenance", "electrical", "warning_signs"]


def next_category(last_category: str) -> str:
    try:
        idx = _CATEGORIES.index(last_category)
    except ValueError:
        idx = -1
    return _CATEGORIES[(idx + 1) % len(_CATEGORIES)]


def build_text_prompt(category: str, used_topics: list[str] | None = None) -> str:
    if category == "maintenance":
        topics = _MAINTENANCE_TOPICS
    elif category == "electrical":
        topics = _ELECTRICAL_TOPICS
    else:
        topics = _WARNING_SIGNS_TOPICS
    if used_topics:
        topics += f"\n\nᲛᲝᲠᲘᲃᲔᲣᲚᲘ: ეს თემები ბოლოს უკვე გამოვიყენეთ — ამჯერად სხვა თემა აირჩიე: {', '.join(used_topics)}"
    return _BASE_SYSTEM.format(topics=topics, example=_EXAMPLE_POST)


def build_image_prompt(part_en: str, part_ka: str) -> str:
    return (
        f"3D Pixar Disney animation style advertising poster. "
        f"Scene: modern car service garage. "
        f"Main focus: large realistic close-up of {part_en} in the center of the image. "
        f"No text labels or tags on the parts themselves. "
        f"Background: garage walls with large bold sign reading 'WISH MOTORS' in navy blue letters. "
        f"SsangYong car lifted on a hydraulic lift in background. "
        f"No people, no humans, no characters, no faces. "
        f"Colors: navy blue #1B2B5C and cyan #00B4D8, white accents. "
        f"Style: professional, clean, bright, high quality social media poster. "
        f"Format: square 1:1, vibrant colors, sharp details."
    )


def extract_parts_from_text(text: str) -> tuple[str, str]:
    """Extract PART_EN and PART_KA lines from generated text. Returns (part_en, part_ka, clean_text)."""
    part_en = "car part"
    part_ka = "სათადარიგო ნაწილი"
    for line in text.splitlines():
        if line.startswith("PART_EN:"):
            part_en = line.replace("PART_EN:", "").strip()
        elif line.startswith("PART_KA:"):
            part_ka = line.replace("PART_KA:", "").strip()
    return part_en, part_ka


def clean_text(text: str) -> str:
    """Remove PART_EN/PART_KA lines and strip markdown symbols from post text."""
    lines = [l for l in text.splitlines() if not l.startswith("PART_EN:") and not l.startswith("PART_KA:")]
    cleaned = []
    for line in lines:
        # Remove bold/italic markers: **, *, __
        line = re.sub(r'\*{1,3}', '', line)
        line = re.sub(r'_{1,2}', '', line)
        # Replace leading "- " or "*   " bullet with nothing (emoji bullets are kept)
        line = re.sub(r'^\s*\*+\s+', '', line)
        line = re.sub(r'^\s*-\s+', '', line)
        cleaned.append(line)
    return "\n".join(cleaned).strip()
