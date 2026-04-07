"""Clinical Study Report template — trial results with tables and findings."""

import random
from ..content_pools import PHARMA_COMPANIES, drug_pair, full_name, pick


def gen_clinical_study_report(rng: random.Random, size: str = "medium") -> str:
    brand, generic = drug_pair(rng)
    company = pick(rng, PHARMA_COMPANIES)
    pi = full_name(rng)
    protocol = f"PROTO-{rng.randint(1000,9999)}-{rng.randint(100,999)}"
    n_subjects = rng.randint(100, 2000)
    completion_rate = rng.randint(75, 98)

    sizes = {"small": 3, "medium": 5, "large": 8, "mega": 12}
    n_sites = sizes.get(size, 5)

    lines = [
        f'<heading level="1" align="center" bold="true">CLINICAL STUDY REPORT</heading>',
        f'<p align="center" spacing-after="6"><bold>A Randomized, Double-Blind, Placebo-Controlled Study of {brand} ({generic})</bold></p>',
        f'<p align="center" spacing-after="6">Protocol Number: {protocol}</p>',
        f'<p align="center" spacing-after="6">Sponsor: {company}</p>',
        f'<p align="center" spacing-after="18">Report Date: {rng.randint(1,12)}/{rng.randint(2024,2026)}</p>',

        f'<heading level="2" bold="true">1. SYNOPSIS</heading>',
        f'<p align="justify" spacing-after="12">Name of Sponsor: <bold>{company}</bold></p>',
        f'<p align="justify" spacing-after="12">Name of Investigational Product: <bold>{brand} ({generic})</bold></p>',
        f'<p align="justify" spacing-after="12">Protocol Number: {protocol}</p>',
        f'<p align="justify" spacing-after="12">Principal Investigator: {pi}, M.D., Ph.D.</p>',
        f'<p align="justify" spacing-after="12">Study Centers: {n_sites} sites across {rng.randint(3,12)} countries</p>',
        f'<p align="justify" spacing-after="12">Total Subjects Enrolled: {n_subjects}</p>',
        f'<p align="justify" spacing-after="12">Study Completion Rate: {completion_rate}%</p>',

        f'<heading level="2" bold="true">2. STUDY DESIGN</heading>',
        f'<p align="justify" indent-first="36" spacing-after="12">This was a Phase {rng.choice(["II", "III"])} randomized, double-blind, placebo-controlled, parallel-group study designed to evaluate the efficacy and safety of {brand} ({generic}) in adult patients. Subjects were randomized in a {rng.choice(["1:1", "2:1", "1:1:1"])} ratio to receive {brand} or placebo for a treatment period of {rng.choice([12, 24, 36, 52])} weeks.</p>',
        f'<heading level="3" bold="true">2.1 Inclusion Criteria</heading>',
        f'<p align="justify" indent-first="36" spacing-after="12">Male and female patients aged {rng.randint(18,21)}-{rng.randint(65,80)} years with a confirmed diagnosis meeting the study protocol requirements. Patients must have had stable symptoms for at least {rng.choice([4, 8, 12])} weeks prior to screening.</p>',
        f'<heading level="3" bold="true">2.2 Exclusion Criteria</heading>',
        f'<p align="justify" indent-first="36" spacing-after="12">Patients with severe hepatic impairment (Child-Pugh Class C), uncontrolled cardiovascular disease, known hypersensitivity to {generic} or any excipient, or participation in another clinical trial within {rng.choice([30, 60, 90])} days of screening.</p>',

        f'<heading level="2" bold="true">3. EFFICACY RESULTS</heading>',
        f'<heading level="3" bold="true">3.1 Primary Endpoint</heading>',
    ]

    p_value = round(rng.uniform(0.001, 0.049), 3)
    effect = round(rng.uniform(15, 45), 1)
    lines.append(f'<p align="justify" indent-first="36" spacing-after="12">The primary efficacy endpoint was met. Treatment with {brand} resulted in a statistically significant {effect}% improvement from baseline compared to placebo (p={p_value}, 95% CI [{round(effect-8,1)}, {round(effect+8,1)}]).</p>')

    # Results table
    lines.append(f'<table cols="4" border="single">')
    lines.append(f'<row><cell bold="true" align="center">Parameter</cell><cell bold="true" align="center">{brand} (N={n_subjects//2})</cell><cell bold="true" align="center">Placebo (N={n_subjects//2})</cell><cell bold="true" align="center">p-value</cell></row>')
    for param in ["Primary endpoint", "Secondary endpoint 1", "Secondary endpoint 2"]:
        val1 = round(rng.uniform(20, 60), 1)
        val2 = round(rng.uniform(5, 30), 1)
        p = round(rng.uniform(0.001, 0.05), 3)
        lines.append(f'<row><cell>{param}</cell><cell align="center">{val1}%</cell><cell align="center">{val2}%</cell><cell align="center">{p}</cell></row>')
    lines.append(f'</table>')

    lines.extend([
        f'<heading level="2" bold="true">4. SAFETY RESULTS</heading>',
        f'<p align="justify" indent-first="36" spacing-after="12">A total of {rng.randint(40,80)}% of subjects in the {brand} group and {rng.randint(30,60)}% in the placebo group reported at least one adverse event. The most common adverse events (≥5%) were headache, nausea, and fatigue. Serious adverse events were reported in {rng.randint(2,8)}% of {brand}-treated subjects versus {rng.randint(1,5)}% in the placebo group.</p>',
        f'<p align="justify" indent-first="36" spacing-after="12"><highlight color="yellow">No deaths were attributed to study treatment. One subject in the {brand} group experienced a serious cardiac event that was assessed as possibly related to treatment.</highlight></p>',

        f'<heading level="2" bold="true">5. CONCLUSIONS</heading>',
        f'<p align="justify" indent-first="36" spacing-after="12">{brand} ({generic}) demonstrated statistically significant and clinically meaningful efficacy in the study population. The safety profile was consistent with the known pharmacological properties of the compound. Based on these results, {brand} represents a viable treatment option warranting further regulatory evaluation.</p>',

        f'<p align="justify" spacing-after="24">Report prepared by: {full_name(rng)}, Ph.D., Biostatistics</p>',
        f'<p align="justify">Approved by: {pi}, M.D., Ph.D., Principal Investigator</p>',
    ])

    return "\n".join(lines)
