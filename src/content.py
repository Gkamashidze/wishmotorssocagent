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

# Ordered topic lists — picked one by one, never repeated until full cycle
TOPIC_LISTS: dict[str, list[str]] = {
    "maintenance": [
        "ძრავის ზეთის გამოცვლა — ზუსტი მოცულობები SsangYong-ის თითოეული მოდელისთვის (Korando, Rexton, Tivoli, Torres)",
        "ჰაერის ფილტრის გამოცვლა — როდის საჭიროა, რა შეიცვლება",
        "ზეთის ფილტრის გამოცვლა — სწორი ბრენდი და სიხშირე SsangYong-ისთვის",
        "სამუხრუჭე ხუნდების შემოწმება — ნახვის სიხშირე, ნიშნები, ვადა",
        "სამუხრუჭე დისკების მდგომარეობა — განსხვავება ხუნდებთან, გამოცვლის ნიშნები",
        "DPF ფილტრის მოვლა — რეგენერაცია, SsangYong-ის დიზელ მოდელები",
        "საბურავების ზეწოლის კონტროლი — სწორი მნიშვნელობები, სეზონური მოწმება",
        "საბურავების ბრუნვა — სარგებელი, სიხშირე, სწორი სქემა",
        "სამუხრუჭე სითხის შეცვლა — ვადა, ნიშნები, DOT სტანდარტი",
        "გამაცივებელი სითხის კონცენტრაცია — ზამთრის მომზადება SsangYong-ისთვის",
        "ტრანსმისიის ზეთი — МКПП და АКПП სხვაობა, SsangYong-ის სპეციფიკა",
        "ჰიდრომანიჟარას (power steering) სითხე — შემოწმება და შეცვლა",
        "წინა საყრდენი ბუჩქები (сайлентблоки) — ნიშნები, გამოცვლის სიხშირე",
        "სარემინო ბელტი (timing belt/chain) — ვადა SsangYong-ის მოდელებში",
        "კონდიციონერის სალონის ფილტრი — გამოცვლა, სარგებელი",
        "ანთების სანთლები (spark plugs) — ვადა, ნიშნები ბენზინიანი SsangYong-ისთვის",
        "ვარცხნა (wheel alignment) — ნიშნები, როდის გასაკეთებელია",
        "ბალანსირება — ვიბრაციის ნიშნები, სიხშირე",
        "ხელის მუხრუჭის (handbrake) შემოწმება და რეგულირება",
        "სუფთა ინჟექტორები — მოვლა, დაბინძურების ნიშნები, SsangYong",
    ],
    "electrical": [
        "ავტომობილის ბატარეა — ვადა, ნიშნები, SsangYong-ის სპეციფიკა",
        "გენერატორი — გაფუჭების სიმპტომები, სწრაფი დიაგნოსტიკა",
        "OBD/Check Engine — რას ნიშნავს სიგნალი, Wish Motors-ში დიაგნოსტიკა",
        "MAF სენსორი — რა ეფექტი აქვს ძრავზე, ნიშნები",
        "O2 (ლამბდა) სენსორი — ეფექტი საწვავის მოხმარებაზე",
        "ტემპერატურის სენსორი — ბოლქვი მაჩვენებელი, SsangYong",
        "სტარტერი — გაჩერების ნიშნები, ვადა",
        "ელ. ფანჯრები — ხშირი გაფუჭება, SsangYong-ის გამოსავალი",
        "ცენტრალური საკეტი — ნიშნები, სწრაფი გამოსწორება",
        "ABS სისტემა — სენსორები, ნათება, უსაფრთხოება",
        "ESP ელექტრონული სტაბილიზაცია — SsangYong-ში როგორ მუშაობს",
        "კონდიციონერის კომპრესორი — ელ. ნაწილი, ნიშნები",
        "Torres DST ჰიბრიდული სისტემა — ელ. ბატარეა, მოვლის სპეციფიკა",
        "ავტომობილის ფარები / LED — სწორი ტიპი SsangYong-ის მოდელებისთვის",
        "კლიმატ-კონტროლი vs. ჩვეულებრივი კონდი — განსხვავება, SsangYong",
        "ECU (ძრავის კომპიუტერი) — გადაყენება, დიაგნოსტიკა",
        "ავტომობილის სიგნალი — ხშირი პრობლემები, Wish Motors-ში სერვისი",
    ],
    "warning_signs": [
        "ძრავის ვიბრაცია სიჩქარის ზრდასთან ერთად — კონკრეტული მიზეზი",
        "სამუხრუჭე ჩხვლეტა — დისკი, ხუნდი, ლითონი — რა ჭიავს?",
        "საჭე ვიბრირებს — ბალანსი, ვარცხნა, ბმული: რა ამოწმებ?",
        "შავი კვამლი გამონაბოლქვიდან — ძრავის პრობლემის ნიშნები",
        "თეთრი კვამლი გამონაბოლქვიდან — გაციება თუ ზეთი?",
        "ლურჯი კვამლი გამონაბოლქვიდან — ზეთი იწვის, მიზეზი",
        "ზეთის წვეთები მანქანის ქვეშ — სად გვხვდება, რა ნიშნავს",
        "გამაცივებელი სითხის წვეთები — სად ეძებო, რა საფრთხე",
        "DPF ნათება — ავარია თუ ჩვეულებრივი რეგენერაცია?",
        "Check Engine ნათება — პირველი ნაბიჯები, SsangYong",
        "ბენზინის სუნი სალონში — საწვავის სისტემის ნიშნები",
        "დამწვარი ზეთის სუნი — სად ეძებო, რა ხდება",
        "გადაბმულობის სრიალი — АКПП-ის პირველი ნიშნები",
        "ხმაური მოხვევისას ბოლოდან — ამხილი ჯვარი, ლილვი",
        "ხმაური გზაზე ბოლოდან — ბუჩქი, ამყოლი, რა გამოირჩევა",
        "ABS ნათება — სენსორი თუ სერიოზული პრობლემა?",
        "ავტომობილი ერთ მხარეს იზიდება — ვარცხნა, ბმული, ბუჩქი",
        "სველ გზაზე ბზინვარება (aquaplaning) — საბურავი, ზეწოლა",
    ],
}

_BASE_SYSTEM = """შენ ხარ Wish Motors-ის Facebook-ის კოპირაიტერი.
Wish Motors არის SsangYong-ის სპეციალიზებული ცენტრი ბათუმში (თევდორე მღვდლის #6).

დაწერე ინფორმაციული Facebook პოსტი ზუსტად ამ ერთ თემაზე: {specific_topic}
სხვა თემაზე ნუ გადახვალ — პოსტი მხოლოდ ამ ერთ საკითხს ეხება.

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


def build_text_prompt(category: str, specific_topic: str) -> str:
    return _BASE_SYSTEM.format(specific_topic=specific_topic, example=_EXAMPLE_POST)


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
    """Extract PART_EN and PART_KA lines from generated text."""
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
        line = re.sub(r'\*{1,3}', '', line)
        line = re.sub(r'_{1,2}', '', line)
        line = re.sub(r'^\s*\*+\s+', '', line)
        line = re.sub(r'^\s*-\s+', '', line)
        cleaned.append(line)
    return "\n".join(cleaned).strip()
