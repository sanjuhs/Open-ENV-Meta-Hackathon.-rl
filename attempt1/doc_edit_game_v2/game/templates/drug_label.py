"""FDA drug label / package insert template."""

import random
from ..content_pools import ADVERSE_REACTIONS, DRUG_INDICATIONS, PHARMA_COMPANIES, drug_pair, full_name, pick


def gen_drug_label(rng: random.Random, size: str = "medium") -> str:
    brand, generic = drug_pair(rng)
    company = pick(rng, PHARMA_COMPANIES)
    indication = pick(rng, DRUG_INDICATIONS)
    dose_mg = rng.choice([5, 10, 25, 50, 100, 200, 500])

    sizes = {"small": 4, "medium": 7, "large": 10, "mega": 14}
    n_adverse = sizes.get(size, 7)
    adverse = rng.sample(ADVERSE_REACTIONS, k=min(n_adverse, len(ADVERSE_REACTIONS)))

    lines = [
        f'<heading level="1" align="center" bold="true">{brand.upper()}</heading>',
        f'<p align="center" spacing-after="6"><italic>({generic})</italic></p>',
        f'<p align="center" spacing-after="6">Tablets for Oral Administration</p>',
        f'<p align="center" spacing-after="18">{dose_mg} mg</p>',
        f'<p align="center" spacing-after="24" border-bottom="single"><bold>HIGHLIGHTS OF PRESCRIBING INFORMATION</bold></p>',
        f'<p align="justify" spacing-after="12">These highlights do not include all the information needed to use <bold>{brand}</bold> safely and effectively. See full prescribing information for <bold>{brand}</bold>.</p>',
        f'<p align="justify" spacing-after="12"><bold>{brand.upper()} ({generic}) tablets, for oral use</bold></p>',
        f'<p align="justify" spacing-after="12">Initial U.S. Approval: {rng.randint(2018, 2025)}</p>',

        # Boxed warning
        f'<p align="justify" spacing-after="12" border-top="double" border-bottom="double" border-left="double" border-right="double"><bold>WARNING: RISK OF SERIOUS CARDIOVASCULAR EVENTS</bold></p>',
        f'<p align="justify" spacing-after="12" indent-left="36" border-left="double"><italic>See full prescribing information for complete boxed warning.</italic></p>',
        f'<p align="justify" spacing-after="18" indent-left="36" border-left="double" border-bottom="double">{brand} may increase the risk of serious cardiovascular thrombotic events, including myocardial infarction and stroke, which can be fatal. This risk may occur early in treatment and may increase with duration of use. {brand} is contraindicated in the setting of coronary artery bypass graft surgery.</p>',

        # Indications
        f'<heading level="2" bold="true">1 INDICATIONS AND USAGE</heading>',
        f'<p align="justify" indent-first="36" spacing-after="12">{brand} is indicated for the {indication}.</p>',
        f'<p align="justify" indent-first="36" spacing-after="12"><bold>Limitations of Use:</bold> {brand} has not been studied in patients with severe hepatic impairment. Use in this population is not recommended.</p>',

        # Dosage
        f'<heading level="2" bold="true">2 DOSAGE AND ADMINISTRATION</heading>',
        f'<heading level="3" bold="true">2.1 Recommended Dosage</heading>',
        f'<p align="justify" indent-first="36" spacing-after="12">The recommended starting dose of {brand} is {dose_mg} mg administered orally once daily, with or without food. Based on individual tolerability, the dose may be increased to {dose_mg * 2} mg once daily after {rng.choice([2, 4])} weeks.</p>',
        f'<heading level="3" bold="true">2.2 Dosage in Renal Impairment</heading>',
        f'<p align="justify" indent-first="36" spacing-after="12">No dosage adjustment is required in patients with mild to moderate renal impairment (eGFR 30-89 mL/min). In patients with severe renal impairment (eGFR &lt; 30 mL/min), reduce the dose to {dose_mg // 2} mg once daily.</p>',

        # Warnings
        f'<heading level="2" bold="true">5 WARNINGS AND PRECAUTIONS</heading>',
        f'<heading level="3" bold="true">5.1 Cardiovascular Risk</heading>',
        f'<p align="justify" indent-first="36" spacing-after="12"><highlight color="yellow">Nonsteroidal anti-inflammatory drugs (NSAIDs) cause an increased risk of serious cardiovascular thrombotic events, including myocardial infarction and stroke, which can be fatal.</highlight> Patients with known cardiovascular disease or risk factors may be at greater risk.</p>',
        f'<heading level="3" bold="true">5.2 Hepatotoxicity</heading>',
        f'<p align="justify" indent-first="36" spacing-after="12">Elevations of ALT or AST (three or more times the upper limit of normal [ULN]) have been reported in patients treated with {brand}. Measure transaminases (ALT and AST) before initiating treatment and as clinically indicated.</p>',

        # Adverse reactions
        f'<heading level="2" bold="true">6 ADVERSE REACTIONS</heading>',
        f'<heading level="3" bold="true">6.1 Clinical Trials Experience</heading>',
        f'<p align="justify" indent-first="36" spacing-after="12">Because clinical trials are conducted under widely varying conditions, adverse reaction rates observed in clinical trials cannot be directly compared to rates in other clinical trials and may not reflect rates observed in practice.</p>',
        f'<p align="justify" indent-first="36" spacing-after="12">The following adverse reactions were reported in ≥{rng.randint(2,10)}% of patients treated with {brand} {dose_mg} mg in placebo-controlled clinical trials (N={rng.randint(500,2000)}):</p>',
    ]

    for reaction in adverse:
        pct = rng.randint(2, 25)
        lines.append(f'<p align="justify" indent-left="72" spacing-after="6">• {reaction.capitalize()} ({pct}%)</p>')

    lines.extend([
        f'<heading level="2" bold="true">16 HOW SUPPLIED/STORAGE AND HANDLING</heading>',
        f'<p align="justify" indent-first="36" spacing-after="12">{brand} ({generic}) tablets, {dose_mg} mg, are {pick(rng, ["white", "yellow", "pink", "blue"])}, {pick(rng, ["round", "oval", "capsule-shaped"])}, film-coated tablets debossed with "{brand[0]}{dose_mg}" on one side.</p>',
        f'<p align="justify" indent-first="36" spacing-after="12">Store at 20°C to 25°C (68°F to 77°F); excursions permitted to 15°C to 30°C (59°F to 86°F). Protect from moisture.</p>',
        f'<heading level="2" bold="true">17 PATIENT COUNSELING INFORMATION</heading>',
        f'<p align="justify" indent-first="36" spacing-after="12">Advise patients to read the FDA-approved patient labeling (Medication Guide). Inform patients of the potential cardiovascular and hepatic risks and advise them to seek medical attention if symptoms occur.</p>',
        f'<p align="justify" spacing-after="24">Manufactured by: <bold>{company}</bold></p>',
        f'<p align="justify">Revised: {rng.randint(1,12)}/{rng.randint(2024,2026)}</p>',
    ])

    return "\n".join(lines)
