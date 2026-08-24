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

# Topic banks to generate unique, realistic headlines and multi-line text
headline_pool = {
    "India & Global": [
        "New Bilateral Trade Pact Signed to Boost Regional Supply Chain Resiliency",
        "Cross-Border Digital Infrastructure Framework Rolls Out Across Key Markets",
        "Global Economic Summit Highlights Shifts in Multi-Currency Settlement Hubs",
        "Maritime Security Protocols Reinforced During Recent Diplomatic Sessions",
        "Strategic Logistics Corridor Expansion Anticipates 30% Reduction in Transit Costs"
    ],
    "Tech & AI": [
        "Autonomous Multi-Agent Systems Revolutionize Enterprise Data Workflows",
        "Semiconductor Fabrication Facility Milestone Reached Ahead of Schedule",
        "Open-Source Foundational Models Gain Major Traction Among Regional Startups",
        "Advanced Cloud Perimeter Defenses Deployed Against Emerging Threat Vectors",
        "Vertical AI Integration Lowers Spreadsheet and ERP Operational Bottlenecks"
    ],
    "Business & Economy": [
        "Metropolitan Retail Sectors Surge on Strong Consumer Demand in Tier-2 Hubs",
        "Clean-Label Direct-to-Consumer Brands Scale Nationwide Distribution Footprint",
        "Central Bank Maintains Steady Interest Rate Outlook Amid Balanced Inflation",
        "Venture Capital Allocations Pivot Toward Deep-Tech and Sustainable Logistics",
        "Automated Corporate Tax Filing Platforms Streamline Compliance Turnaround Times"
    ],
    "Lifestyle & Living": [
        "Artisanal Organic Dairy Formulations Capture Urban Consumer Preferences",
        "Traditional Heritage Foods Re-engineered for Modern Retail Ecosystems",
        "Hyper-Local Creator Marketplaces Empower Home-Based Micro-Entrepreneurs",
        "Sustainable Urban Living Initiatives Transform Residential Property Design",
        "Wellness and Clean-Label Nutrition Trends Drive Record Quarter Growth"
    ],
    "Earth & Environment": [
        "Renewable Energy Grid Integration Reaches Record Capacity Benchmarks",
        "Circular Economy Frameworks Adopted Across Major Industrial Sectors",
        "Water Conservation Tech Innovations Deploy Across Drought-Prone Regions",
        "Green Building Mandates Accelerate Sustainable Urban Infrastructure",
        "Biodiversity Preservation Pacts Secured at International Environmental Forums"
    ],
    "Entertainment": [
        "Regional Cinema Crosses New Milestone with Global Streaming Distribution",
        "Virtual Production Studios Redefine Visual Effects Workflow Efficiencies",
        "Independent Creator Ecosystems Secure Institutional Funding Support",
        "Immersive Audio Formats Transform Modern Digital Entertainment Delivery",
        "Cultural Heritage Arts Festivals Adapt Hybrid Digital-Physical Models"
    ],
    "Sports & Cultural": [
        "Regional Sports Academies Produce Record Yield of International Contenders",
        "Advanced Biometric Analytics Optimize Athlete Training and Injury Prevention",
        "Traditional Indigenous Sports Gain Formal Recognition and Global Leagues",
        "Stadium Infrastructure Upgrades Focus on Net-Zero Carbon Standards",
        "Digital Fan Engagement Platforms Record Exponential Growth in User Metrics"
    ]
}

def generate_large_dataset():
    live_feed = []
    
    for cat in categories:
        pool = headline_pool.get(cat, headline_pool["India & Global"])
        for i in range(1, 55): # 54 unique items per category
            base_title = pool[(i - 1) % len(pool)]
            title_en = f"{base_title} (Report #{i})"
            
            # 5-line summary equivalent text
            summary_en = (
                f"Recent market developments in the {cat.lower()} ecosystem have prompted "
                f"stakeholders to re-evaluate operational frameworks and strategic priorities for item {i}. "
                f"Key industry analysts emphasize that structural adaptations, enhanced compliance standards, "
                f"and technology-driven automation will play a pivotal role in maintaining long-term momentum. "
                f"Observers note immediate impacts across regional supply chains and consumer engagement metrics."
            )
            
            # 30-line deep dive equivalent text
            deep_dive_en = (
                f"Comprehensive Deep Dive & Strategic Assessment for Initiative #{i} ({cat}):\n\n"
                f"1. Executive Overview: This initiative marks a critical turning point for the sector, integrating modern architectural standards with legacy systems.\n"
                f"2. Market Dynamics: Demand patterns show unprecedented shifts towards efficiency, transparency, and localized customization.\n"
                f"3. Technological Integration: Implementation of automated tools and agentic workflows has minimized historical throughput bottlenecks.\n"
                f"4. Financial Implications: Capital expenditure optimization models project significant ROI acceleration over the next fiscal cycle.\n"
                f"5. Regulatory Compliance: Adherence to cross-border frameworks ensures minimal friction during multi-jurisdictional scaling.\n"
                f"6. Stakeholder Feedback: Early adopters report streamlined operational loops, better data visibility, and reduced administrative overhead.\n"
                f"7. Risk Mitigation: Advanced security perimeters and contingency protocols have been established to guard against unexpected macroeconomic volatility.\n"
                f"8. Supply Chain Resilience: Decentralized warehousing and agile routing have successfully shortened delivery windows across urban centers.\n"
                f"9. Consumer Impact: End-users benefit from higher quality consistency, greater product traceability, and responsive service layers.\n"
                f"10. Environmental Considerations: Sustainable practices and green energy metrics are embedded directly into core operational KPIs.\n"
                f"11. Competitive Landscape: Regional disruptors are challenging established incumbents by leveraging agile digital-first delivery loops.\n"
                f"12. Workforce Adaptation: Comprehensive upskilling programs are underway to prepare teams for autonomous workflow environments.\n"
                f"13. Scalability Analysis: Modular frameworks allow seamless horizontal expansion into adjacent tier-2 and tier-3 markets.\n"
                f"14. Investment Outlook: Institutional backing remains robust, driven by clear metrics and measurable efficiency gains.\n"
                f"15. Governance Structure: Transparent reporting mechanisms ensure accountability across all operational tiers.\n"
                f"16. Strategic Partnerships: Collaborative joint ventures are unlocking new distribution channels and joint R&D synergies.\n"
                f"17. Customer Acquisition: Data-driven targeting has lowered acquisition costs while improving lifetime customer value.\n"
                f"18. Infrastructure Readiness: Cloud-native pipelines and low-latency data lakes support real-time decision-making.\n"
                f"19. Policy Alignment: Local legislative changes are being proactively integrated to maintain uninterrupted service continuity.\n"
                f"20. Future Projections: Long-term forecasts anticipate sustained compounding growth and higher market penetration across target segments."
            )

            article = {
                "category": cat,
                "title": {
                    "en": title_en,
                    "hi": f"{title_en} (हिंदी सारांश)",
                    "ta": f"{title_en} (தமிழ் சுருக்கம்)",
                    "te": f"{title_en} (తెలుగు సారాంశం)",
                    "kn": f"{title_en} (ಕನ್ನಡ ಸಾರಾಂಶ)",
                    "ml": f"{title_en} (മലയാളം സംഗ്രഹം)"
                },
                "summary": {
                    "en": summary_en,
                    "hi": f"हालिया बाजार विकास और रणनीतिक प्राथमिकताएं इस क्षेत्र के भीतर परिचालन ढांचों को फिर से आकार दे रही हैं। प्रमुख विश्लेषक तकनीकी स्वचालन और अनुपालन पर जोर देते हैं।",
                    "ta": f"சமீபத்திய சந்தை வளர்ச்சிகள் மற்றும் மூலோபாய முன்னுரிமைகள் இந்தத் துறையில் செயல்பாட்டு கட்டமைப்புகளை மறுவடிவமைக்கின்றன. முக்கிய ஆய்வாளர்கள் தொழில்நுட்ப ஆட்டோமேஷனை வலியுறுத்துகின்றனர்.",
                    "te": f"சமீபத்திய சந்தை வளர்ச்சிகள் மற்றும் மூலோபாய முன்னுரிமைகள் இந்தத் துறையில் செயல்பாட்டு கட்டமைப்புகளை மறுவடிவமைக்கின்றன.",
                    "kn": f"ಇತ್ತೀಚಿನ ಮಾರುಕಟ್ಟೆ ಬೆಳವಣಿಗೆಗಳು ಮತ್ತು ಕಾರ್ಯತಂತ್ರದ ಪ್ರಾಮುಖ್ಯತೆಗಳು ಈ ವಲಯದ ಕಾರ್ಯತಂತ್ರದ ಚೌಕಟ್ಟುಗಳನ್ನು ಮರುರೂಪಿಸುತ್ತಿವೆ.",
                    "ml": f"സമീപകാല വിപണി സംഭവവികാസങ്ങളും തന്ത്രപരമായ മുൻഗണനകളും ഈ മേഖലയിലെ പ്രവർത്തന ഘട്ടങ്ങളെ പുനർനിർമ്മിക്കുന്നു."
                },
                "deep_dive": {
                    "en": deep_dive_en,
                    "hi": f"विस्तृत रणनीतिक विश्लेषण और रिपोर्ट विवरण:\n\n{deep_dive_en}",
                    "ta": f"விரிவான மூலோபாய பகுப்பாய்வு மற்றும் அறிக்கை விவரங்கள்:\n\n{deep_dive_en}",
                    "te": f"விரிவான மூலோபாய பகுப்பாய்வு மற்றும் அறிக்கை விவரங்கள்:\n\n{deep_dive_en}",
                    "kn": f"ಸಮಗ್ರ ಕಾರ್ಯತಂತ್ರದ ವಿಶ್ಲೇಷಣೆ ಮತ್ತು ವರದಿ ವಿವರಗಳು:\n\n{deep_dive_en}",
                    "ml": f"സമഗ്രമായ തന്ത്രപരമായ വിശകലനവും റിപ്പോർട്ട് വിശദാംശങ്ങളും:\n\n{deep_dive_en}"
                },
                "source": random.choice(sources),
                "url": "https://example.com/news-brief",
                "image": random.choice(images)
            }
            live_feed.append(article)

    return {"live_feed": live_feed}

if __name__ == "__main__":
    data = generate_large_dataset()
    with open("articles.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Generated {len(data['live_feed'])} news items with professional headlines and detailed summaries!")
