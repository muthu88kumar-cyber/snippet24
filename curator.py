import json
import random

categories = [
    "India & Global", 
    "Tech & AI", 
    "Business & Economy", 
    "Lifestyle & Living", 
    "Earth & Environment", 
    "Entertainment", 
    "Sports & Cultural"
]

sources = ["Mint", "YourStory", "The Economic Times", "The Hindu", "Business Standard", "Financial Express"]
images = [
    "https://picsum.photos/seed/news_eco/800/500",
    "https://picsum.photos/seed/news_tech/800/500",
    "https://picsum.photos/seed/news_biz/800/500",
    "https://picsum.photos/seed/news_global/800/500",
    "https://picsum.photos/seed/news_ai/800/500"
]

# Base template pools to dynamically scale up to 50+ items per category
def generate_large_dataset():
    live_feed = []
    id_counter = 1

    for cat in categories:
        for i in range(1, 55): # Generates 54 unique articles per category
            title_en = f"Strategic Update {i}: Key Developments in {cat} Sector"
            summary_en = f"Analysis report examining recent structural milestones, policy changes, and stakeholder impacts across the {cat.lower()} domain for item {i}."
            deep_dive_en = f"A comprehensive deep dive into initiative {i} within {cat}. Evaluates operational adjustments, regional market uptake, scalability factors, and future projections."

            article = {
                "category": cat,
                "title": {
                    "en": title_en,
                    "hi": f"{cat} क्षेत्र में प्रमुख विकास - अपडेट {i}",
                    "ta": f"{cat} துறையில் முக்கிய முன்னேற்றங்கள் - புதுப்பிப்பு {i}",
                    "te": f"{cat} రంగంలో కీలక పరిణామాలు - అప్‌డేట్ {i}",
                    "kn": f"{cat} ವಲಯದಲ್ಲಿ ಪ್ರಮುಖ ಬೆಳವಣಿಗೆಗಳು - ಅಪ್‌ಡೇಟ್ {i}",
                    "ml": f"{cat} മേഖലയിലെ പ്രധാന സംഭവവികാസങ്ങൾ - അപ്ഡേറ്റ് {i}"
                },
                "summary": {
                    "en": summary_en,
                    "hi": f"विश्लेषण रिपोर्ट हाल के मील के पत्थर और नीतिगत बदलावों की जांच कर रही है।",
                    "ta": f"சமீபத்திய மைல்கற்கள் மற்றும் கொள்கை மாற்றங்களை ஆராயும் பகுப்பாய்வு அறிக்கை.",
                    "te": f"சமீபத்திய மைல்கற்கள் மற்றும் கொள்கை மாற்றங்களை ஆராயும் பகுப்பாய்வு அறிக்கை.",
                    "kn": f"ಇತ್ತೀಚಿನ ಮೈಲಿಗಲ್ಲುಗಳು ಮತ್ತು ನೀತಿ ಬದಲಾವಣೆಗಳನ್ನು ಪರಿಶೀಲಿಸುವ ವಿಶ್ಲೇಷಣಾ ವರದಿ.",
                    "ml": f"സമീപകാല നാഴികക്കല്ലുകളും നയപരമായ മാറ്റങ്ങളും പരിശോധിക്കുന്ന വിശകലന റിപ്പോർട്ട്."
                },
                "deep_dive": {
                    "en": deep_dive_en,
                    "hi": f"रणनीतिक बदलावों और बाजार के रुझानों का व्यापक विश्लेषण।",
                    "ta": f"மூலோபாய மாற்றங்கள் மற்றும் சந்தை போக்குகளின் விரிவான பகுப்பாய்வு.",
                    "te": f"மூலோபாய மாற்றங்கள் மற்றும் சந்தை போக்குகளின் விரிவான பகுப்பாய்வு.",
                    "kn": f"ಕಾರ್ಯತಂತ್ರದ ಬದಲಾವಣೆಗಳು ಮತ್ತು ಮಾರುಕಟ್ಟೆ ಪ್ರವೃತ್ತಿಗಳ ಸಮಗ್ರ ವಿಶ್ಲೇಷಣೆ.",
                    "ml": f"തന്ത്രപരമായ മാറ്റങ്ങളുടെയും വിപണി പ്രവണതകളുടെയും സമഗ്രമായ വിശകലനം."
                },
                "source": random.choice(sources),
                "url": "https://example.com/news-brief",
                "image": random.choice(images)
            }
            live_feed.append(article)
            id_counter += 1

    return {"live_feed": live_feed}

if __name__ == "__main__":
    data = generate_large_dataset()
    with open("articles.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Successfully generated {len(data['live_feed'])} total articles across all categories in articles.json!")

