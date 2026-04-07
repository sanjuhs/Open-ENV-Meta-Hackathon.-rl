"""Legal contract template generator — service agreements, NDAs, licensing deals."""

import random
from ..content_pools import (
    COMPANY_NAMES, DATES, DOLLAR_AMOUNTS, LEGAL_SECTIONS, STATES,
    full_name, pick, fill_template,
)

CLAUSE_TEMPLATES = [
    '{party} shall deliver all materials within {days} business days of execution.',
    'Payment of {amount} shall be made in {installments} equal installments commencing on the Effective Date.',
    'Either party may terminate this Agreement with {days} days prior written notice to the other party.',
    'All intellectual property created during the term shall remain the sole property of {party}.',
    '{party} agrees to maintain strict confidentiality of all proprietary information disclosed hereunder.',
    'This Agreement shall be governed by and construed in accordance with the laws of the State of {state}.',
    'Any disputes arising under this Agreement shall be resolved through binding arbitration in {state}.',
    '{party} shall indemnify, defend, and hold harmless the other party against all claims, damages, and expenses.',
    'Force majeure events, including but not limited to acts of God, shall excuse performance for the duration thereof.',
    'Neither party may assign this Agreement without the prior written consent of the other party.',
    '{party} represents and warrants that it has full authority to enter into this Agreement.',
    'The total liability of either party under this Agreement shall not exceed {amount}.',
    '{party} shall maintain insurance coverage of not less than {amount} during the term.',
    'All notices under this Agreement shall be in writing and delivered to the addresses set forth herein.',
    'This Agreement constitutes the entire agreement between the parties and supersedes all prior negotiations.',
]


def gen_legal_contract(rng: random.Random, size: str = "medium") -> str:
    party_a = pick(rng, COMPANY_NAMES)
    party_b = pick(rng, COMPANY_NAMES)
    while party_b == party_a:
        party_b = pick(rng, COMPANY_NAMES)
    date = pick(rng, DATES)
    amount = pick(rng, DOLLAR_AMOUNTS)
    signatory_a = full_name(rng)
    signatory_b = full_name(rng)

    sizes = {"small": (3, 5), "medium": (5, 8), "large": (8, 12), "mega": (12, 15)}
    clause_range = sizes.get(size, (5, 8))
    n_clauses = rng.randint(*clause_range)
    clauses = rng.sample(CLAUSE_TEMPLATES, k=min(n_clauses, len(CLAUSE_TEMPLATES)))

    sections_used = rng.sample(LEGAL_SECTIONS, k=min(n_clauses + 4, len(LEGAL_SECTIONS)))

    lines = [
        f'<heading level="1" align="center" bold="true">SERVICE AGREEMENT</heading>',
        f'<p align="center" spacing-after="24">Effective Date: {date}</p>',
        f'<p align="justify" spacing-after="12">This Service Agreement (the "<bold>Agreement</bold>") is entered into as of {date} by and between <bold>{party_a}</bold>, a corporation organized under the laws of the State of {pick(rng, STATES)} ("<underline>Provider</underline>"), and <bold>{party_b}</bold>, a corporation organized under the laws of the State of {pick(rng, STATES)} ("<underline>Client</underline>").</p>',
        f'<heading level="2" bold="true">RECITALS</heading>',
        f'<p align="justify" indent-first="36" spacing-after="12">WHEREAS, Provider possesses specialized expertise and resources in professional consulting and technology services;</p>',
        f'<p align="justify" indent-first="36" spacing-after="12">WHEREAS, Client desires to engage Provider to render certain professional services on the terms and conditions set forth herein;</p>',
        f'<p align="justify" indent-first="36" spacing-after="12">NOW, THEREFORE, in consideration of the mutual covenants and agreements herein contained, and for other good and valuable consideration, the receipt and sufficiency of which are hereby acknowledged, the parties agree as follows:</p>',
    ]

    for i, clause in enumerate(clauses):
        section_name = sections_used[i] if i < len(sections_used) else f"SECTION {i+1}"
        lines.append(f'<heading level="2" bold="true">{section_name}</heading>')
        filled = fill_template(rng, clause)
        lines.append(f'<p align="justify" indent-first="36" spacing-after="12">{i+1}.1 {filled}</p>')
        if rng.random() < 0.6:
            extra = fill_template(rng, pick(rng, CLAUSE_TEMPLATES))
            lines.append(f'<p align="justify" indent-first="36" spacing-after="12">{i+1}.2 {extra}</p>')

    lines.extend([
        f'<heading level="2" bold="true">EXECUTION</heading>',
        f'<p align="justify" spacing-after="24">IN WITNESS WHEREOF, the parties have executed this Agreement as of the date first written above.</p>',
        f'<p spacing-after="6"><bold>{party_a}</bold></p>',
        f'<p spacing-after="6">By: _________________________ Name: {signatory_a} Title: Chief Executive Officer</p>',
        f'<p spacing-after="6">Date: _________________________</p>',
        f'<p spacing-after="6"><bold>{party_b}</bold></p>',
        f'<p spacing-after="6">By: _________________________ Name: {signatory_b} Title: Managing Director</p>',
        f'<p spacing-after="6">Date: _________________________</p>',
    ])

    return "\n".join(lines)
