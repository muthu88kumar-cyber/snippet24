# Map incoming RSS tags or keywords into your exact 6 primary active categories
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
