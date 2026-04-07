"""Indian income tax assessment order / notice template — from real tax proceedings."""

import random
from ..content_pools import DATES, DOLLAR_AMOUNTS, full_name, pick, TAX_SECTIONS, TAX_TERMS


ASSESSMENT_PARAGRAPHS = [
    "The assessee filed his return of income for the Assessment Year {ay} on {date} declaring total income of Rs. {amount}. The return was processed u/s 143(1) of the Income Tax Act, 1961.",
    "Information was received from the Directorate of Income Tax (Systems) through the Insight-NMS portal indicating that the assessee had entered into high-value financial transactions during the Previous Year {py} which were not reflected in the return of income.",
    "As per SFT (Statement of Financial Transaction) data, the assessee had cash deposits aggregating to Rs. {amount} in savings bank account no. {account} maintained with {bank} during the relevant previous year.",
    "As per information available with the Department through TDS/TCS statements, the assessee received income of Rs. {amount} which has not been offered for taxation in the return of income filed for AY {ay}.",
    "A notice u/s 148A(b) was issued to the assessee on {date} along with the information which suggests that income chargeable to tax has escaped assessment. The assessee was given an opportunity to furnish his reply/explanation.",
    "The assessee has not filed any reply to the show cause notice despite being given adequate opportunity. In view of the non-compliance by the assessee, it is a fit case for issuance of notice u/s 148 of the Act.",
    "After careful examination of the information available on record and the reply furnished by the assessee, the Assessing Officer is satisfied that the income chargeable to tax amounting to Rs. {amount} has escaped assessment within the meaning of Section 147 of the Income Tax Act.",
    "A notice u/s 142(1) was issued to the assessee on {date} seeking details of bank accounts, source of cash deposits, and details of income from all sources during the previous year relevant to the assessment year under consideration.",
    "Despite opportunities given to the assessee through multiple notices, the assessee has failed to comply with the statutory requirements. Therefore, the assessment is completed to the best of judgment u/s 144 read with section 147 of the Act.",
    "The total income of the assessee is assessed at Rs. {amount} and the tax payable on the assessed income works out to Rs. {tax}. A notice of demand u/s 156 of the Act is being issued separately.",
    "Penalty proceedings u/s 271(1)(c) of the Income Tax Act are being initiated separately for concealment of income / furnishing inaccurate particulars of income.",
    "In view of the above discussion, the addition of Rs. {amount} is hereby confirmed as unexplained cash credits u/s 68 of the Income Tax Act, 1961.",
]

BANK_NAMES = [
    "State Bank of India", "Punjab National Bank", "Bank of Baroda",
    "HDFC Bank Ltd.", "ICICI Bank Ltd.", "Axis Bank Ltd.",
    "Union Bank of India", "Canara Bank", "Indian Overseas Bank",
]


def gen_tax_assessment(rng: random.Random, size: str = "medium") -> str:
    assessee = full_name(rng)
    ao_name = full_name(rng)
    pan = f"{''.join(rng.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=5))}{rng.randint(1000,9999)}{''.join(rng.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=1))}"
    start_year = rng.randint(2015, 2024)
    ay = f"{start_year}-{(start_year + 1) % 100:02d}"
    py = f"{start_year - 1}-{start_year % 100:02d}"
    ward = f"Ward {rng.randint(1,15)}({rng.randint(1,4)})"
    bank = pick(rng, BANK_NAMES)
    account = str(rng.randint(10000000000, 99999999999))

    sizes = {"small": (4, 6), "medium": (6, 10), "large": (10, 15), "mega": (15, 20)}
    n_paras = rng.randint(*sizes.get(size, (6, 10)))

    rs_amounts = [f"{rng.randint(1,99)},{rng.randint(10,99)},{rng.randint(100,999)}", f"{rng.randint(1,9)},{rng.randint(10,99)},{rng.randint(100,999)}", f"{rng.randint(10,99)},{rng.randint(100,999)}"]

    lines = [
        f'<heading level="1" align="center" bold="true">INCOME TAX DEPARTMENT</heading>',
        f'<heading level="2" align="center" bold="true">GOVERNMENT OF INDIA</heading>',
        f'<p align="center" spacing-after="6">Office of the Income Tax Officer, {ward}</p>',
        f'<p align="center" spacing-after="18">Assessment Year: {ay}</p>',
        f'<p align="left" spacing-after="6">Name of Assessee: <bold>{assessee}</bold></p>',
        f'<p align="left" spacing-after="6">PAN: {pan}</p>',
        f'<p align="left" spacing-after="6">Status: Individual</p>',
        f'<p align="left" spacing-after="18">Date of Order: {pick(rng, DATES)}</p>',
        f'<heading level="2" bold="true" underline="single">ORDER {pick(rng, TAX_SECTIONS)} OF THE INCOME TAX ACT, 1961</heading>',
    ]

    rng.shuffle(ASSESSMENT_PARAGRAPHS)
    for i, para in enumerate(ASSESSMENT_PARAGRAPHS[:n_paras]):
        filled = para.replace("{ay}", ay).replace("{py}", py).replace("{date}", pick(rng, DATES))
        filled = filled.replace("{amount}", pick(rng, rs_amounts))
        filled = filled.replace("{tax}", pick(rng, rs_amounts))
        filled = filled.replace("{account}", account).replace("{bank}", bank)
        lines.append(f'<p align="justify" indent-first="36" spacing-after="12" line-spacing="1.5">{i+1}. {filled}</p>')

    lines.extend([
        f'<heading level="2" bold="true">CONCLUSION AND ORDER</heading>',
        f'<p align="justify" indent-first="36" spacing-after="12" line-spacing="1.5">In view of the above discussion and the material available on record, the total income of the assessee for the Assessment Year {ay} is hereby assessed as under:</p>',
        f'<p align="justify" indent-left="72" spacing-after="6">Income as returned: Rs. {pick(rng, rs_amounts)}</p>',
        f'<p align="justify" indent-left="72" spacing-after="6">Add: Unexplained cash credits u/s 68: Rs. {pick(rng, rs_amounts)}</p>',
        f'<p align="justify" indent-left="72" spacing-after="6">Add: Unexplained investment u/s 69: Rs. {pick(rng, rs_amounts)}</p>',
        f'<p align="justify" indent-left="72" spacing-after="18" bold="true">Total Assessed Income: Rs. {pick(rng, rs_amounts)}</p>',
        f'<p align="justify" spacing-after="12">Issue notice of demand u/s 156 of the Income Tax Act, 1961.</p>',
        f'<p align="justify" spacing-after="12">Penalty proceedings u/s 271(1)(c) are initiated separately.</p>',
        f'<p align="left" spacing-after="24">Dated: {pick(rng, DATES)}</p>',
        f'<p align="left" spacing-after="6"><bold>{ao_name}</bold></p>',
        f'<p align="left">Income Tax Officer, {ward}</p>',
    ])

    return "\n".join(lines)
