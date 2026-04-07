"""Affidavit template — sworn statements with court formatting."""

import random
from ..content_pools import COURT_NAMES, DATES, STATES, full_name, pick


def gen_affidavit(rng: random.Random, size: str = "medium") -> str:
    affiant = full_name(rng)
    court = pick(rng, COURT_NAMES)
    case_no = f"{rng.randint(20,26)}-cv-{rng.randint(1000,9999)}"
    plaintiff = full_name(rng)
    defendant = full_name(rng)
    date = pick(rng, DATES)
    state = pick(rng, STATES)

    sizes = {"small": (4, 8), "medium": (8, 15), "large": (15, 25), "mega": (25, 40)}
    n_paras = rng.randint(*sizes.get(size, (8, 15)))

    statements = [
        f"I am over the age of eighteen years and competent to testify to the matters stated herein.",
        f"I am currently employed as {pick(rng, ['Senior Vice President', 'General Counsel', 'Chief Financial Officer', 'Director of Operations'])} at {pick(rng, ['Acme Corporation', 'GlobalTech Solutions', 'Summit Industries', 'Vertex Partners'])}.",
        f"I have personal knowledge of the facts stated in this affidavit and, if called upon to testify, could and would competently testify thereto.",
        f"On or about {pick(rng, DATES)}, I was present at a meeting where the terms of the agreement were discussed.",
        f"At no time during the negotiations did the opposing party disclose the material information referenced in paragraph {rng.randint(2,5)} above.",
        f"The documents attached hereto as Exhibit A are true and correct copies of the original documents in my possession.",
        f"I have reviewed the financial records for the period ending {pick(rng, DATES)} and can confirm the amounts are accurate.",
        f"The statements made by the defendant on {pick(rng, DATES)} were inconsistent with the written representations provided earlier.",
        f"I personally observed the condition of the premises on {pick(rng, DATES)} and can attest to the damages described herein.",
        f"The total damages incurred as a result of the defendant's breach amount to approximately {pick(rng, ['$50,000', '$250,000', '$1,000,000', '$5,000,000'])}.",
        f"Based on my professional experience of {rng.randint(5,25)} years in this field, the practices described constitute a material violation of industry standards.",
        f"I am authorized to make this affidavit on behalf of the organization and have been duly empowered to do so by resolution of the Board of Directors.",
    ]

    rng.shuffle(statements)
    used = statements[:n_paras]

    lines = [
        f'<heading level="1" align="center" bold="true">IN THE {court.upper()}</heading>',
        f'<p align="center" spacing-after="6">{plaintiff}, Plaintiff,</p>',
        f'<p align="center" spacing-after="6">v.</p>',
        f'<p align="center" spacing-after="6">{defendant}, Defendant.</p>',
        f'<p align="center" spacing-after="18">Case No. {case_no}</p>',
        f'<heading level="2" align="center" bold="true" underline="single">AFFIDAVIT OF {affiant.upper()}</heading>',
        f'<p align="justify" line-spacing="2.0" spacing-after="12">STATE OF {state.upper()}</p>',
        f'<p align="justify" line-spacing="2.0" spacing-after="12">COUNTY OF {pick(rng, ["Kings", "New York", "Los Angeles", "Cook", "Harris", "Maricopa"])}</p>',
        f'<p align="justify" line-spacing="2.0" indent-first="36" spacing-after="12">I, <bold>{affiant}</bold>, being duly sworn, depose and state as follows:</p>',
    ]

    for i, stmt in enumerate(used):
        lines.append(f'<p align="justify" line-spacing="2.0" indent-first="36" spacing-after="12">{i+1}. {stmt}</p>')

    lines.extend([
        f'<p align="justify" line-spacing="2.0" indent-first="36" spacing-after="24">I declare under penalty of perjury that the foregoing is true and correct to the best of my knowledge, information, and belief.</p>',
        f'<p spacing-after="6">Executed on {date}.</p>',
        f'<p spacing-after="36">_________________________</p>',
        f'<p spacing-after="6"><bold>{affiant}</bold></p>',
        f'<p spacing-after="24">Sworn to and subscribed before me this _____ day of _________, 2026.</p>',
        f'<p spacing-after="6">_________________________</p>',
        f'<p>Notary Public, State of {state}</p>',
        f'<p>My commission expires: _________________________</p>',
    ])

    return "\n".join(lines)
