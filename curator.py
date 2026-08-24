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

# Rich data pool with completely unique titles, matching summaries, and 3-paragraph deep dives
news_data_pool = {
    "India & Global": [
        {
            "title": "New Bilateral Trade Pact Signed to Boost Regional Supply Chain Resiliency",
            "summary": "India and key regional partners have finalized a comprehensive trade framework designed to lower logistical bottlenecks, streamline cross-border compliance procedures, and reduce tariff barriers for manufacturing components.",
            "deep_dive": "This strategic agreement marks a significant turning point for regional commerce by establishing direct regulatory bridges between key maritime and overland economic corridors. Industry leaders anticipate substantial improvements in cargo turnaround times, effectively minimizing transit overheads for manufacturers operating across multiple jurisdictions. Furthermore, the framework incorporates provisions for digital customs verification, significantly reducing administrative friction and accelerating clearance cycles at major ports of entry."
        },
        {
            "title": "Cross-Border Digital Infrastructure Framework Rolls Out Across Key Markets",
            "summary": "A unified digital public infrastructure initiative has officially launched to interconnect financial settlement systems, reducing transaction friction for cross-border merchants and boosting regional transparency.",
            "deep_dive": "By bridging multi-currency transaction gateways and real-time payment rails, this deployment allows institutional participants to settle accounts with unprecedented speed and lower intermediary costs. Early trials demonstrate a noticeable drop in foreign exchange conversion overheads, pointing toward a more integrated economic landscape across participating territories. Technical architects have also embedded adaptive security perimeters to protect against emerging threats while ensuring strict compliance with evolving data sovereignty mandates."
        },
        {
            "title": "Global Economic Summit Highlights Shifts in Multi-Currency Settlement Hubs",
            "summary": "International monetary delegates convened to evaluate the rising adoption of alternative settlement currencies, focusing on foreign exchange volatility mitigation and enhanced liquidity mechanisms.",
            "deep_dive": "Central bank representatives underscored the necessity of establishing robust regulatory guardrails to protect domestic stability while actively encouraging international trade diversification. Discussions also centered on how automated treasury management platforms can help financial institutions navigate fluctuating currency reserves more efficiently. Observers note that these evolving monetary alignments are gradually redefining traditional banking partnerships across emerging markets."
        },
        {
            "title": "Maritime Security Protocols Reinforced During Recent Diplomatic Sessions",
            "summary": "Defense and maritime authorities have ratified enhanced intelligence-sharing protocols to secure vital shipping lanes, responding to geopolitical shifts affecting oceanic transit routes.",
            "deep_dive": "The initiative introduces synchronized naval patrols and automated vessel-tracking technologies to safeguard commercial cargo vessels against regional disruptions. Major shipping liners have welcomed these protective measures, highlighting the positive impact on maritime insurance premiums and delivery schedule reliability. Collaborative training exercises between allied nations are scheduled to begin next quarter to ensure seamless operational coordination on the high seas."
        },
        {
            "title": "Strategic Logistics Corridor Expansion Anticipates 30% Reduction in Transit Costs",
            "summary": "Construction milestones on the multi-modal economic corridor remain ahead of schedule, with several automated freight hubs operationalizing ahead of peak shipping season.",
            "deep_dive": "The seamless integration of high-speed rail links and intelligent warehousing facilities is projected to slash cargo transit times across major industrial clusters. Regional manufacturing units stand to benefit directly from lower inventory holding costs and more reliable distribution schedules into metropolitan consumer centers. Analysts view this infrastructure upgrade as a vital catalyst for boosting national manufacturing export competitiveness over the coming decade."
        }
    ],
    "Tech & AI": [
        {
            "title": "Autonomous Multi-Agent Systems Revolutionize Enterprise Data Workflows",
            "summary": "Corporate technology divisions are rapidly shifting toward autonomous agent architectures to automate complex data processing tasks and minimize manual spreadsheet reconciliations.",
            "deep_dive": "By integrating large language models directly with legacy enterprise resource planning systems, organizations have successfully eliminated historical data bottlenecks. Early enterprise implementers report up to a seventy percent reduction in monthly reporting cycles, allowing management teams to reallocate human capital toward strategic financial planning. The architecture relies on secure internal sandboxes that ensure corporate data privacy while executing automated ledger alignments."
        },
        {
            "title": "Semiconductor Fabrication Facility Milestone Reached Ahead of Schedule",
            "summary": "Domestic microchip manufacturing initiatives have cleared critical structural engineering phases, moving closer to active silicon wafer production through public-private partnerships.",
            "deep_dive": "The acceleration of equipment commissioning timelines has been supported by targeted government incentives and collaborative engineering agreements with global technology leaders. Industry stakeholders expect commercial sample rollouts to begin influencing regional hardware supply chains by the end of the fiscal year. This domestic fabrication capacity is expected to insulate local electronics manufacturers from international component shortages and supply volatility."
        },
        {
            "title": "Open-Source Foundational Models Gain Major Traction Among Regional Startups",
            "summary": "Emerging software firms are increasingly bypassing proprietary AI licenses in favor of customizable open-source models that can be fine-tuned securely on private cloud infrastructure.",
            "deep_dive": "This architectural pivot enables localized engineering teams to tailor artificial intelligence capabilities to specific regional languages and industry use cases without recurring API licensing overheads. Startups are leveraging these agile models to build specialized vertical software applications for healthcare, finance, and logistics sectors. The trend is fostering a vibrant ecosystem of independent developers who retain complete ownership over their underlying model weights and data pipelines."
        },
        {
            "title": "Advanced Cloud Perimeter Defenses Deployed Against Emerging Threat Vectors",
            "summary": "Cybersecurity architects have rolled out adaptive zero-trust perimeter controls to combat sophisticated distributed threats and unauthorized data exfiltration tactics across enterprise networks.",
            "deep_dive": "The modern defense architecture leverages real-time behavioral analytics to detect and isolate network anomalies instantaneously across decentralized cloud environments. Corporate compliance officers have noted that these proactive security enhancements align perfectly with upcoming data protection legislation and industry standards. Continuous automated auditing tools ensure that system vulnerabilities are patched long before they can be exploited by malicious actors."
        },
        {
            "title": "Vertical AI Integration Lowers Spreadsheet and ERP Operational Bottlenecks",
            "summary": "Financial management teams are implementing specialized vertical intelligence tools designed to parse unstructured invoices and automate ledger entries with high precision.",
            "deep_dive": "Eliminating manual data entry errors allows accounting departments to achieve near-instantaneous month-end closes and accurate cash flow visibility. Business leaders are no longer constrained by retroactive reporting delays, enabling them to make agile pricing and cost optimization decisions. The software adapts to unique company accounting structures, learning continuously from human feedback loops to improve categorization accuracy over time."
        }
    ],
    "Business & Economy": [
        {
            "title": "Metropolitan Retail Sectors Surge on Strong Consumer Demand in Tier-2 Hubs",
            "summary": "Consumer discretionary spending across tier-2 and tier-3 urban centers has exhibited remarkable resilience, outperforming baseline macroeconomic forecasts through localized offerings.",
            "deep_dive": "Organized retail chains and digital marketplaces report heightened customer engagement driven by rising disposable incomes and tailored regional product selections. Supply chain networks have deepened their penetration into semi-urban districts, ensuring product availability that matches metropolitan standards. Economists emphasize that this consumption breadth provides a sturdy cushion against broader global economic headwinds."
        },
        {
            "title": "Clean-Label Direct-to-Consumer Brands Scale Nationwide Distribution Footprint",
            "summary": "Agile consumer goods startups specializing in clean-label dairy and organic foods are rapidly expanding their physical retail presence by leveraging hyper-local supply chains.",
            "deep_dive": "Urban consumers are increasingly prioritizing health-conscious alternatives, ingredient transparency, and farm-fresh delivery models over mass-produced consumer goods. By establishing decentralized micro-fulfillment centers, these brands maintain strict cold-chain integrity and superior product freshness. Institutional investors have taken notice, fueling aggressive expansion into new geographic regions and product lines."
        },
        {
            "title": "Central Bank Maintains Steady Interest Rate Outlook Amid Balanced Inflation",
            "summary": "Monetary policy committee members voted unanimously to hold benchmark lending rates steady, citing stable core inflation readings and positive domestic growth metrics.",
            "deep_dive": "Commercial lenders have responded with consistent credit availability, supporting capital expenditure across infrastructure, manufacturing, and real estate sectors. Financial planners view this predictable rate environment as highly favorable for long-term corporate budgeting and capital allocation strategies. Foreign institutional investors have also expressed confidence in the macroeconomic stability maintained by prudent monetary governance."
        },
        {
            "title": "Venture Capital Allocations Pivot Toward Deep-Tech and Sustainable Logistics",
            "summary": "Investment firms are channeling capital away from consumer delivery apps toward deep-tech hardware, climate tech, and intelligent supply chain optimization platforms.",
            "deep_dive": "Funding rounds now place rigorous emphasis on sustainable operational practices, unit economics defensibility, and proprietary technological moats rather than aggressive customer acquisition burn. Founders are successfully adapting by demonstrating clear paths to profitability and measurable efficiency gains for enterprise clients. This capital reallocation is strengthening the foundational backbone of the regional technology ecosystem."
        },
        {
            "title": "Automated Corporate Tax Filing Platforms Streamline Compliance Turnaround Times",
            "summary": "Tax compliance software ecosystems have integrated real-time invoice matching capabilities, drastically reducing corporate reporting discrepancies and regulatory risks.",
            "deep_dive": "Financial controllers can now reconcile input tax credits instantly through secure automated government portal integrations, eliminating historical end-of-quarter stress. The technology minimizes human error during data transmission, ensuring complete alignment between internal ledgers and statutory filings. Consequently, corporate legal teams report a dramatic drop in notice resolutions and penalty exposures."
        }
    ]
}

def generate_large_dataset():
    live_feed = []
    
    for cat in categories:
        articles_pool = news_data_pool.get(cat, news_data_pool["India & Global"])
        for i in range(1, 55): # Generates 54 unique articles per category by cycling cleanly
            base_item = articles_pool[(i - 1) % len(articles_pool)]
            
            # Append unique variation suffix only if it loops past the base pool size
            suffix = f" - Perspective {i // len(articles_pool) + 1}" if i > len(articles_pool) else ""
            title_en = base_item["title"] + suffix
            summary_en = base_item["summary"]
            deep_dive_en = base_item["deep_dive"]

            article = {
                "category": cat,
                "title": {
                    "en": title_en,
                    "hi": f"{title_en} (विशेष रिपोर्ट)",
                    "ta": f"{title_en} (சிறப்பு அறிக்கை)",
                    "te": f"{title_en} (ప్రత్యేక నివేదిక)",
                    "kn": f"{title_en} (ವಿಶೇಷ ವರದಿ)",
                    "ml": f"{title_en} (പ്രത്യേക റിപ്പോർട്ട്)"
                },
                "summary": {
                    "en": summary_en,
                    "hi": f"मुख्य समाचार सारांश: {summary_en}",
                    "ta": f"முக்கியச் செய்தி சுருக்கம்: {summary_en}",
                    "te": f"ముఖ్యమైన వార్తల సారాంశం: {summary_en}",
                    "kn": f"ಪ್ರಮುಖ ಸುದ್ದಿ ಸಾರಾಂಶ: {summary_en}",
                    "ml": f"പ്രധാന വാർത്തകളുടെ സംഗ്രഹം: {summary_en}"
                },
                "deep_dive": {
                    "en": deep_dive_en,
                    "hi": f"{deep_dive_en}\n\nবিশ্লেষণ এবং অতিরিক্ত বিবরণ সংযুক্ত করা হয়েছে।",
                    "ta": f"{deep_dive_en}\n\nஆழமான பகுப்பாய்வு மற்றும் கூடுதல் விவரங்கள் இணைக்கப்பட்டுள்ளன.",
                    "te": f"{deep_dive_en}\n\nసమగ్ర విశ్లేషణ మరియు అదనపు వివరాలు అందించబడ్డాయి.",
                    "kn": f"{deep_dive_en}\n\nಸಮಗ್ರ ವಿಶ್ಲೇಷಣೆ ಮತ್ತು ಹೆಚ್ಚುವರಿ ವಿವರಗಳನ್ನು ಒದಗಿಸಲಾಗಿದೆ.",
                    "ml": f"{deep_dive_en}\n\nസമഗ്രമായ വിശകലനവും കൂടുതൽ വിവരങ്ങളും നൽകിയിരിക്കുന്നു."
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
    print(f"Successfully generated {len(data['live_feed'])} news items with clean formatting!")

