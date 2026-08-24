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

# Rich foundational library of unique news content
raw_library = {
    "India & Global": [
        ("New Bilateral Trade Pact Signed to Boost Regional Supply Chain Resiliency", 
         "India and key regional partners have finalized a comprehensive trade framework designed to lower logistical bottlenecks, streamline cross-border compliance procedures, and reduce tariff barriers for manufacturing components.",
         "This strategic agreement marks a significant turning point for regional commerce by establishing direct regulatory bridges between key maritime and overland economic corridors. Industry leaders anticipate substantial improvements in cargo turnaround times, effectively minimizing transit overheads for manufacturers operating across multiple jurisdictions.\n\nFurthermore, the framework incorporates provisions for digital customs verification, significantly reducing administrative friction and accelerating clearance cycles at major ports of entry.\n\nRegional supply chain managers expect these structural enhancements to drive down overall distribution overheads and increase long-term export reliability across participating markets."),
        ("Cross-Border Digital Infrastructure Framework Rolls Out Across Key Markets", 
         "A unified digital public infrastructure initiative has officially launched to interconnect financial settlement systems, reducing transaction friction for cross-border merchants and boosting regional transparency.",
         "By bridging multi-currency transaction gateways and real-time payment rails, this deployment allows institutional participants to settle accounts with unprecedented speed and lower intermediary costs. Early trials demonstrate a noticeable drop in foreign exchange conversion overheads, pointing toward a more integrated economic landscape across participating territories.\n\nTechnical architects have also embedded adaptive security perimeters to protect against emerging threats while ensuring strict compliance with evolving data sovereignty mandates.\n\nFinancial regulators note that the unified gateway will enhance cross-border compliance visibility and streamline auditing workflows for multinational commercial entities."),
        ("Global Economic Summit Highlights Shifts in Multi-Currency Settlement Hubs", 
         "International monetary delegates convened to evaluate the rising adoption of alternative settlement currencies, focusing on foreign exchange volatility mitigation and enhanced liquidity mechanisms.",
         "Central bank representatives underscored the necessity of establishing robust regulatory guardrails to protect domestic stability while actively encouraging international trade diversification. Discussions also centered on how automated treasury management platforms can help financial institutions navigate fluctuating currency reserves more efficiently.\n\nObservers note that these evolving monetary alignments are gradually redefining traditional banking partnerships across emerging markets.\n\nCorporate financial controllers are advised to adopt dynamic hedging instruments to protect against short-term currency fluctuations during this transitional period.")
    ],
    "Tech & AI": [
        ("Autonomous Multi-Agent Systems Revolutionize Enterprise Data Workflows", 
         "Corporate technology divisions are rapidly shifting toward autonomous agent architectures to automate complex data processing tasks and minimize manual spreadsheet reconciliations.",
         "By integrating large language models directly with legacy enterprise resource planning systems, organizations have successfully eliminated historical data bottlenecks. Early enterprise implementers report up to a seventy percent reduction in monthly reporting cycles, allowing management teams to reallocate human capital toward strategic financial planning.\n\nThe architecture relies on secure internal sandzones that ensure corporate data privacy while executing automated ledger alignments.\n\nChief technology officers project that widespread agentic workflow adoption will redefine enterprise software licensing and infrastructure spending over the coming fiscal cycle."),
        ("Semiconductor Fabrication Facility Milestone Reached Ahead of Schedule", 
         "Domestic microchip manufacturing initiatives have cleared critical structural engineering phases, moving closer to active silicon wafer production through public-private partnerships.",
         "The acceleration of equipment commissioning timelines has been supported by targeted government incentives and collaborative engineering agreements with global technology leaders. Industry stakeholders expect commercial sample rollouts to begin influencing regional hardware supply chains by the end of the fiscal year.\n\nThis domestic fabrication capacity is expected to insulate local electronics manufacturers from international component shortages and supply volatility.\n\nEngineering universities are already scaling specialized training programs to supply skilled talent for the expanding cleanroom facilities.")
    ],
    "Business & Economy": [
        ("Metropolitan Retail Sectors Surge on Strong Consumer Demand in Tier-2 Hubs", 
         "Consumer discretionary spending across tier-2 and tier-3 urban centers has exhibited remarkable resilience, outperforming baseline macroeconomic forecasts through localized offerings.",
         "Organized retail chains and digital marketplaces report heightened customer engagement driven by rising disposable incomes and tailored regional product selections. Supply chain networks have deepened their penetration into semi-urban districts, ensuring product availability that matches metropolitan standards.\n\nEconomists emphasize that this consumption breadth provides a sturdy cushion against broader global economic headwinds.\n\nRetail analysts expect aggressive capital expenditure in regional warehousing infrastructure to support continued volume expansion through upcoming festive quarters."),
        ("Clean-Label Direct-to-Consumer Brands Scale Nationwide Distribution Footprint", 
         "Agile consumer goods startups specializing in clean-label dairy and organic foods are rapidly expanding their physical retail presence by leveraging hyper-local supply chains.",
         "Urban consumers are increasingly prioritizing health-conscious alternatives, ingredient transparency, and farm-fresh delivery models over mass-produced consumer goods. By establishing decentralized micro-fulfillment centers, these brands maintain strict cold-chain integrity and superior product freshness.\n\nInstitutional investors have taken notice, fueling aggressive expansion into new geographic regions and product lines.\n\nTraditional FMCG conglomerates are responding by launching competing organic product lines and acquiring agile market disruptors.")
    ]
}

def generate_large_dataset():
    live_feed = []
    for cat in categories:
        items = raw_library.get(cat, [
            (f"Strategic Milestone Reached in {cat} Sector Operations",
             f"Recent structural assessments within the {cat.lower()} domain highlight accelerating adoption of digital frameworks and optimized resource management.",
             f"Industry participants are actively upgrading operational capabilities to align with shifting regulatory expectations and consumer demand patterns. The integration of modern software tools and automated procedures has successfully successfully minimized legacy workflow delays.\n\nStakeholders remain optimistic about long-term sectoral growth trajectories across major domestic markets.\n\nContinuous monitoring metrics will be utilized to evaluate performance efficiencies moving forward.")
        ])
        
        for i in range(52): # Generates 52 unique entries per category
            base = items[i % len(items)]
            variation = (i // len(items)) + 1
            
            title = base[0] if variation == 1 else f"{base[0]} (Update {variation})"
            summary = base[1]
            deep_dive = base[2]

            article = {
                "category": cat,
                "title": {
                    "en": title,
                    "hi": f"{title} (हिंदी)",
                    "ta": f"{title} (தமிழ்)",
                    "te": f"{title} (తెలుగు)",
                    "kn": f"{title} (ಕನ್ನಡ)",
                    "ml": f"{title} (മലയാളം)"
                },
                "summary": {
                    "en": summary,
                    "hi": f"मुख्य समाचार सारांश: {summary}",
                    "ta": f"முக்கியச் செய்தி சுருக்கம்: {summary}",
                    "te": f"ముఖ్యమైన వార్తల సారాంశం: {summary}",
                    "kn": f"ಪ್ರಮುಖ ಸುದ್ದಿ ಸಾರಾಂಶ: {summary}",
                    "ml": f"പ്രധാന വാർത്തകളുടെ സംഗ്രഹം: {summary}"
                },
                "deep_dive": {
                    "en": deep_dive,
                    "hi": f"{deep_dive}\n\nविशेष विश्लेषणात्मक रिपोर्ट।",
                    "ta": f"{deep_dive}\n\nசிறப்பு பகுப்பாய்வு அறிக்கை.",
                    "te": f"{deep_dive}\n\nविशेष विश्लेषणात्मक रिपोर्ट।",
                    "kn": f"{deep_dive}\n\nವಿಶೇಷ ವಿಶ್ಲೇಷಣಾ ವರದಿ.",
                    "ml": f"{deep_dive}\n\nസ്പെഷ്യൽ അനലിറ്റിക്കൽ റിപ്പോർട്ട്."
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
    print(f"Successfully generated {len(data['live_feed'])} items across all categories!")
