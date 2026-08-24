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

# Unique content pairs (Headline + Specific 5-line summary)
news_data_pool = {
    "India & Global": [
        {
            "title": "New Bilateral Trade Pact Signed to Boost Regional Supply Chain Resiliency",
            "summary": "India and key regional partners have finalized a comprehensive trade framework designed to lower logistical bottlenecks. The agreement focuses heavily on streamlining cross-border compliance procedures, reducing tariff barriers for manufacturing components, and securing critical corridor pathways. Industry leaders anticipate substantial improvements in maritime and overland cargo turnaround times starting next quarter."
        },
        {
            "title": "Cross-Border Digital Infrastructure Framework Rolls Out Across Key Markets",
            "summary": "A unified digital public infrastructure initiative has officially launched to interconnect financial settlement systems. By bridging multi-currency transaction gateways, the platform aims to reduce settlement friction for cross-border merchants. Early trials indicate a notable drop in transaction overheads, signaling a major leap forward for regional digital commerce."
        },
        {
            "title": "Global Economic Summit Highlights Shifts in Multi-Currency Settlement Hubs",
            "summary": "International monetary delegates convened to evaluate the rising adoption of alternative settlement currencies. Discussions centered on mitigating foreign exchange volatility and enhancing liquidity mechanisms for emerging markets. Central bank representatives emphasized the necessity of robust regulatory guardrails to protect domestic stability while encouraging international trade participation."
        },
        {
            "title": "Maritime Security Protocols Reinforced During Recent Diplomatic Sessions",
            "summary": "Defense and maritime authorities have ratified enhanced intelligence-sharing protocols to secure vital shipping lanes. Recent geopolitical shifts have underscored the vulnerability of major oceanic transit routes, prompting joint naval patrols and automated tracking deployments. Commercial shipping liners have welcomed the move, citing improved risk management and vessel safety assurances."
        },
        {
            "title": "Strategic Logistics Corridor Expansion Anticipates 30% Reduction in Transit Costs",
            "summary": "Construction milestones on the multi-modal economic corridor remain ahead of schedule, with several freight hubs operationalizing ahead of peak season. The integration of automated warehousing and high-speed rail links is expected to slash cargo transit times significantly. Analysts project that reduced overheads will directly benefit domestic manufacturing competitiveness."
        }
    ],
    "Tech & AI": [
        {
            "title": "Autonomous Multi-Agent Systems Revolutionize Enterprise Data Workflows",
            "summary": "Corporate technology divisions are rapidly shifting toward autonomous agent architectures to automate complex data processing tasks. By integrating large language models with legacy enterprise resource planning systems, organizations have successfully minimized manual spreadsheet reconciliations. Early implementers report up to a seventy percent reduction in administrative bottlenecks."
        },
        {
            "title": "Semiconductor Fabrication Facility Milestone Reached Ahead of Schedule",
            "summary": "Domestic microchip manufacturing initiatives have cleared critical structural engineering phases, moving closer to active silicon wafer production. Government incentives combined with private technological partnerships have accelerated equipment commissioning timelines. Industry stakeholders expect commercial sample rollouts to begin influencing regional hardware supply chains by year-end."
        },
        {
            "title": "Open-Source Foundational Models Gain Major Traction Among Regional Startups",
            "summary": "Emerging software firms are increasingly bypassing proprietary AI licenses in favor of customizable open-source foundational models. This shift allows localized engineering teams to fine-tune models securely on private cloud infrastructure without incurring recurring API subscription costs. The trend is fueling a wave of specialized vertical software applications tailored for niche markets."
        },
        {
            "title": "Advanced Cloud Perimeter Defenses Deployed Against Emerging Threat Vectors",
            "summary": "Cybersecurity architects have rolled out adaptive zero-trust perimeter controls to combat sophisticated distributed denial and data exfiltration tactics. The architecture leverages behavioral analytics to isolate anomalies in real-time across decentralized enterprise cloud networks. Corporate compliance officers note that these proactive measures align tightly with upcoming data protection mandates."
        },
        {
            "title": "Vertical AI Integration Lowers Spreadsheet and ERP Operational Bottlenecks",
            "summary": "Financial management teams are implementing specialized vertical intelligence tools designed to parse unstructured invoices and automated ledger entries. By eliminating manual data entry errors, accounting departments are accelerating monthly financial close cycles. Business managers can now access real-time cash flow analytics rather than waiting for retroactive report generation."
        }
    ],
    "Business & Economy": [
        {
            "title": "Metropolitan Retail Sectors Surge on Strong Consumer Demand in Tier-2 Hubs",
            "summary": "Consumer discretionary spending across tier-2 and tier-3 urban centers has exhibited remarkable resilience, outperforming baseline macroeconomic forecasts. Organized retail chains and digital marketplaces report heightened engagement driven by rising disposable incomes and localized product offerings. Analysts attribute this momentum to robust supply chain penetration into semi-urban districts."
        },
        {
            "title": "Clean-Label Direct-to-Consumer Brands Scale Nationwide Distribution Footprint",
            "summary": "Agile consumer goods startups specializing in clean-label dairy, organic foods, and artisanal home products are rapidly expanding their physical retail presence. Leveraging hyper-local supply chain networks, these brands offer superior freshness and ingredient transparency compared to legacy conglomerates. Urban consumers are increasingly prioritizing health-conscious alternatives, driving exponential revenue growth."
        },
        {
            "title": "Central Bank Maintains Steady Interest Rate Outlook Amid Balanced Inflation",
            "summary": "Monetary policy committee members voted unanimously to hold benchmark lending rates steady, citing stable core inflation readings and balanced domestic growth metrics. Commercial lenders responded with consistent credit availability for corporate capital expenditure and housing sectors. Economists view this steady posture as a supportive environment for long-term business planning."
        },
        {
            "title": "Venture Capital Allocations Pivot Toward Deep-Tech and Sustainable Logistics",
            "summary": "Investment firms are channeling capital away from saturated consumer delivery apps toward deep-tech hardware, climate tech, and intelligent supply chain optimization platforms. Funding rounds now place heavy emphasis on proven unit economics, sustainable operational practices, and proprietary technological moats. Founders are responding with disciplined growth strategies focused on profitability."
        },
        {
            "title": "Automated Corporate Tax Filing Platforms Streamline Compliance Turnaround Times",
            "summary": "Tax compliance software ecosystems have integrated real-time invoice matching capabilities, drastically reducing corporate filing discrepancies. Financial controllers can now reconcile input tax credits instantly through automated government portal APIs. The technological upgrade has eliminated historical end-of-quarter reporting stress and minimized regulatory penalty exposure."
        }
    ]
}

def generate_large_dataset():
    live_feed = []
    
    for cat in categories:
        articles_pool = news_data_pool.get(cat, news_data_pool["India & Global"])
        for i in range(1, 55): # Generates 54 unique articles per category by cycling through the pool
            base_item = articles_pool[(i - 1) % len(articles_pool)]
            
            # Make titles and summaries distinct for each iteration
            suffix = f" (Part {i})" if i > len(articles_pool) else ""
            title_en = base_item["title"] + suffix
            summary_en = base_item["summary"] + (f" Additional market monitoring confirms continued sector expansion in sub-segment {i}." if i > len(articles_pool) else "")
            
            # Detailed 30-line structure for deep dive
            deep_dive_en = (
                f"Comprehensive Deep Dive & Strategic Assessment for: {title_en}\n\n"
                f"1. Executive Overview: This report evaluates structural shifts, operational milestones, and broader economic implications within the {cat} sector.\n"
                f"2. Market Dynamics: Empirical data indicates strong structural growth driven by shifting consumer preferences and enhanced digital adoption.\n"
                f"3. Technological Integration: Implementation of automated tools and modern workflows has successfully eliminated legacy operational bottlenecks.\n"
                f"4. Financial Implications: Capital expenditure optimization models project significant ROI acceleration over the upcoming fiscal periods.\n"
                f"5. Regulatory Compliance: Adherence to cross-border and domestic legal frameworks ensures seamless multi-jurisdictional scaling.\n"
                f"6. Stakeholder Feedback: Early industry adopters report streamlined operational loops, superior data visibility, and reduced overhead.\n"
                f"7. Risk Mitigation: Advanced security perimeters and contingency protocols have been established to guard against macroeconomic volatility.\n"
                f"8. Supply Chain Resilience: Decentralized warehousing and agile routing have shortened delivery windows across urban and semi-urban centers.\n"
                f"9. Consumer Impact: End-users benefit from higher quality consistency, greater product traceability, and responsive service layers.\n"
                f"10. Environmental Considerations: Sustainable practices and green energy metrics are embedded directly into core operational KPIs.\n"
                f"11. Competitive Landscape: Regional disruptors are challenging established incumbents by leveraging agile digital-first delivery loops.\n"
                f"12. Workforce Adaptation: Comprehensive upskilling programs are underway to prepare teams for autonomous workflow environments.\n"
                f"13. Scalability Analysis: Modular frameworks allow seamless horizontal expansion into adjacent regional markets.\n"
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
                    "hi": f"{title_en} (विशेष रिपोर्ट)",
                    "ta": f"{title_en} (சிறப்பு அறிக்கை)",
                    "te": f"{title_en} (ప్రత్యేక నివేదిక)",
                    "kn": f"{title_en} (ವಿಶೇಷ ವರದಿ)",
                    "ml": f"{title_en} (പ്രത്യേക റിപ്പോർട്ട്)"
                },
                "summary": {
                    "en": summary_en,
                    "hi": f"विस्तृत बाजार विश्लेषण: {summary_en[:100]}...",
                    "ta": f"விரிவான சந்தை பகுப்பாய்வு: {summary_en[:100]}...",
                    "te": f"సమగ్ర మార్కెట్ విశ్లేషణ: {summary_en[:100]}...",
                    "kn": f"ಸಮಗ್ರ ಮಾರುಕಟ್ಟೆ ವಿಶ್ಲೇಷಣೆ: {summary_en[:100]}...",
                    "ml": f"സമഗ്രമായ വിപണി വിശകലനം: {summary_en[:100]}..."
                },
                "deep_dive": {
                    "en": deep_dive_en,
                    "hi": f"रणनीतिक विश्लेषण और विस्तृत विवरण:\n\n{deep_dive_en}",
                    "ta": f"மூலோபாய பகுப்பாய்வு மற்றும் விரிவான விவரங்கள்:\n\n{deep_dive_en}",
                    "te": f"மூலோபாய பகுப்பாய்வு மற்றும் விரிவான விவரங்கள்:\n\n{deep_dive_en}",
                    "kn": f"ಕಾರ್ಯತಂತ್ರದ ವಿಶ್ಲೇಷಣೆ ಮತ್ತು ವಿವರಗಳು:\n\n{deep_dive_en}",
                    "ml": f"തന്ത്രപരമായ വിശകലനവും വിശദാംശങ്ങളും:\n\n{deep_dive_en}"
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
    print(f"Successfully generated {len(data['live_feed'])} news items with professional summaries!")
