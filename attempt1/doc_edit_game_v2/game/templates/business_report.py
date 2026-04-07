"""Business report + corporate filing template."""

import random
from ..content_pools import COMPANY_NAMES, DATES, DOLLAR_AMOUNTS, full_name, pick


def gen_business_report(rng: random.Random, size: str = "medium") -> str:
    company = pick(rng, COMPANY_NAMES)
    author = full_name(rng)
    date = pick(rng, DATES)
    year = rng.randint(2024, 2026)

    sizes = {"small": (3, 5), "medium": (5, 8), "large": (8, 12), "mega": (12, 18)}
    n_range = sizes.get(size, (5, 8))
    n_findings = rng.randint(*n_range)

    findings_pool = [
        f"Revenue increased by {rng.randint(5,35)}% year-over-year, driven primarily by expansion in the {pick(rng, ['enterprise', 'consumer', 'government', 'healthcare'])} segment.",
        f"Operating expenses decreased by {rng.randint(3,15)}% due to efficiency improvements in supply chain management and workforce optimization.",
        f"Customer acquisition cost (CAC) declined from {pick(rng, DOLLAR_AMOUNTS)} to {pick(rng, DOLLAR_AMOUNTS)} per enterprise client, reflecting improved marketing ROI.",
        f"Net promoter score (NPS) increased from {rng.randint(30,50)} to {rng.randint(55,80)}, indicating significant improvement in customer satisfaction.",
        f"Employee retention rate improved to {rng.randint(85,97)}%, exceeding the industry benchmark of {rng.randint(75,85)}%.",
        f"The company's market share in the {pick(rng, ['North American', 'European', 'Asia-Pacific'])} region grew from {rng.randint(5,15)}% to {rng.randint(16,30)}%.",
        f"R&D investment totaled {pick(rng, DOLLAR_AMOUNTS)}, representing {rng.randint(8,20)}% of total revenue, aligned with the company's innovation strategy.",
        f"Gross margin expanded by {rng.randint(100,500)} basis points to {rng.randint(45,75)}%, reflecting pricing optimization and cost reduction initiatives.",
        f"Free cash flow generation was {pick(rng, DOLLAR_AMOUNTS)}, providing sufficient capital for planned acquisitions and shareholder returns.",
        f"The company successfully launched {rng.randint(2,8)} new products during the fiscal year, contributing {rng.randint(10,35)}% of total revenue.",
        f"Debt-to-equity ratio improved from {round(rng.uniform(0.4,1.2),2)} to {round(rng.uniform(0.2,0.6),2)}, strengthening the company's balance sheet.",
        f"International operations now represent {rng.randint(25,55)}% of total revenue, up from {rng.randint(15,25)}% in the prior year.",
    ]
    rng.shuffle(findings_pool)
    findings = findings_pool[:n_findings]

    recs = [
        f"Allocate {pick(rng, DOLLAR_AMOUNTS)} toward digital transformation initiatives in Q{rng.randint(1,4)} {year+1}.",
        f"Expand the sales team by {rng.randint(10,50)} headcount to capitalize on identified growth opportunities.",
        f"Implement enterprise resource planning (ERP) system upgrade to improve operational efficiency by an estimated {rng.randint(15,30)}%.",
        f"Pursue strategic acquisition in the {pick(rng, ['AI/ML', 'cybersecurity', 'cloud infrastructure', 'data analytics'])} space at a budget of up to {pick(rng, DOLLAR_AMOUNTS)}.",
        f"Establish dedicated customer success team to reduce churn rate from {rng.randint(8,15)}% to below {rng.randint(3,7)}%.",
    ]
    rng.shuffle(recs)

    lines = [
        f'<heading level="1" align="center" bold="true">{company}</heading>',
        f'<heading level="2" align="center">Annual Business Review — Fiscal Year {year}</heading>',
        f'<p align="center" spacing-after="6">Prepared by: {author}, Chief Strategy Officer</p>',
        f'<p align="center" spacing-after="18">Date: {date}</p>',
        f'<p align="center" spacing-after="12" border-bottom="single"><italic>CONFIDENTIAL — FOR INTERNAL USE ONLY</italic></p>',

        f'<heading level="2" bold="true">Executive Summary</heading>',
        f'<p align="justify" indent-first="36" spacing-after="12">This report presents the annual business review for {company} for fiscal year {year}. The company demonstrated strong performance across key metrics, with revenue growth exceeding targets and operational efficiency improvements driving margin expansion. The following sections detail financial performance, market position, operational highlights, and strategic recommendations for the coming year.</p>',

        f'<heading level="2" bold="true">Financial Performance</heading>',
    ]

    # Financial table
    lines.append(f'<table cols="3" border="single">')
    lines.append(f'<row><cell bold="true">Metric</cell><cell bold="true" align="center">FY{year}</cell><cell bold="true" align="center">FY{year-1}</cell></row>')
    for metric in ["Total Revenue", "Operating Income", "Net Income", "EBITDA", "Free Cash Flow"]:
        val1 = pick(rng, DOLLAR_AMOUNTS)
        lines.append(f'<row><cell>{metric}</cell><cell align="center">{val1}</cell><cell align="center">{pick(rng, DOLLAR_AMOUNTS)}</cell></row>')
    lines.append(f'</table>')

    lines.append(f'<heading level="2" bold="true">Key Findings</heading>')
    for i, finding in enumerate(findings):
        lines.append(f'<p align="justify" indent-first="36" spacing-after="12">{i+1}. {finding}</p>')

    lines.append(f'<heading level="2" bold="true">Strategic Recommendations</heading>')
    for i, rec in enumerate(recs[:min(3, len(recs))]):
        lines.append(f'<p align="justify" indent-first="36" spacing-after="12">{i+1}. {rec}</p>')

    lines.extend([
        f'<heading level="2" bold="true">Conclusion</heading>',
        f'<p align="justify" indent-first="36" spacing-after="12">{company} is well-positioned for continued growth in fiscal year {year+1}. By executing on the strategic recommendations outlined above and maintaining focus on operational excellence, the company can achieve its ambitious targets while building long-term shareholder value.</p>',
        f'<p align="left" spacing-after="24">Respectfully submitted,</p>',
        f'<p><bold>{author}</bold></p>',
        f'<p>Chief Strategy Officer, {company}</p>',
    ])

    return "\n".join(lines)
