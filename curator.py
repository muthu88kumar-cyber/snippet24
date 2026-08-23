import json
import os

VALID_CATEGORIES = [
    "India & Global",
    "Tech & AI",
    "Business & Economy",
    "Earth & Environment",
    "Lifestyle & Living",
    "Sports & Cultural"
]

def classify_article(title, summary):
    text = (title + " " + summary).lower()
    if any(k in text for k in ["tech", "ai", "artificial intelligence", "software", "cloud", "algorithm"]):
        return "Tech & AI"
    elif any(k in text for k in ["business", "economy", "market", "stocks", "inflation", "investment", "logistics"]):
        return "Business & Economy"
    elif any(k in text for k in ["environment", "climate", "lake", "water", "earth", "sustainable", "green"]):
        return "Earth & Environment"
    elif any(k in text for k in ["lifestyle", "living", "health", "food", "travel", "culture"]):
        return "Lifestyle & Living"
    elif any(k in text for k in ["sports", "cricket", "football", "olympics", "cultural", "festival", "art"]):
        return "Sports & Cultural"
    else:
        return "India & Global"

# Example function hook to generate articles.json during your build workflow
def generate_feed_json(sample_articles, output_path="articles.json"):
    feed_data = {"live_feed": {}}
    
    for i, art in enumerate(sample_articles, start=1):
        cat = classify_article(art.get("title", ""), art.get("summary", ""))
        feed_data["live_feed"][f"article_{i}"] = {
            "category": cat,
            "meta": f"{cat} • Live Update",
            "title": {"en": art.get("title", "")},
            "summary": {"en": art.get("summary", "")},
            "deep_dive": {"en": art.get("deep_dive", "")}
        }
        
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(feed_data, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    print("Curator script template loaded successfully.")
