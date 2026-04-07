"""Case brief / legal memorandum template."""

import random
from ..content_pools import CASE_CITATIONS, COURT_NAMES, STATES, full_name, pick


def gen_case_brief(rng: random.Random, size: str = "medium") -> str:
    author = full_name(rng)
    plaintiff = full_name(rng)
    defendant = full_name(rng)
    court = pick(rng, COURT_NAMES)
    date = f"{pick(rng, ['January','February','March','April','May','June'])} {rng.randint(1,28)}, {rng.randint(2024,2026)}"

    sizes = {"small": 3, "medium": 5, "large": 8, "mega": 12}
    n_sections = sizes.get(size, 5)

    arguments = [
        f"The defendant's actions constitute a clear breach of the contractual obligations set forth in Section {rng.randint(2,8)} of the Agreement dated {date}. As established in {pick(rng, CASE_CITATIONS)}, a party that fails to perform its material obligations is liable for consequential damages.",
        f"Under the doctrine of promissory estoppel, the plaintiff reasonably relied on the defendant's representations to its detriment. The court in {pick(rng, CASE_CITATIONS)} held that such reliance, when foreseeable, gives rise to an enforceable obligation.",
        f"The statute of limitations does not bar the plaintiff's claims. The discovery rule tolls the limitation period until the plaintiff knew or should have known of the injury. See {pick(rng, CASE_CITATIONS)}.",
        f"The defendant's motion for summary judgment should be denied because genuine issues of material fact remain in dispute. As the Supreme Court held in {pick(rng, CASE_CITATIONS)}, all reasonable inferences must be drawn in favor of the non-moving party.",
        f"The evidence demonstrates that the defendant acted with willful and wanton disregard for the plaintiff's rights, warranting an award of punitive damages under {pick(rng, STATES)} law.",
        f"The plaintiff has established all elements of a prima facie case for negligence: duty, breach, causation, and damages. The defendant owed a duty of care under {pick(rng, CASE_CITATIONS)}.",
        f"The arbitration clause in the parties' agreement is enforceable under the Federal Arbitration Act. The court in {pick(rng, CASE_CITATIONS)} reaffirmed the strong federal policy favoring arbitration.",
        f"The court should grant injunctive relief because the plaintiff has demonstrated: (1) likelihood of success on the merits; (2) irreparable harm absent injunction; (3) balance of hardships favoring plaintiff; and (4) public interest considerations.",
    ]
    rng.shuffle(arguments)

    lines = [
        f'<heading level="1" align="center" bold="true">LEGAL MEMORANDUM</heading>',
        f'<p align="center" spacing-after="6"><bold>{plaintiff} v. {defendant}</bold></p>',
        f'<p align="center" spacing-after="18">{court}</p>',
        f'<p align="left" spacing-after="6">Prepared by: {author}</p>',
        f'<p align="left" spacing-after="18">Date: {date}</p>',
        f'<heading level="2" bold="true">I. STATEMENT OF FACTS</heading>',
        f'<p align="justify" indent-first="36" spacing-after="12" line-spacing="2.0">This matter arises from a commercial dispute between {plaintiff} ("<bold>Plaintiff</bold>") and {defendant} ("<bold>Defendant</bold>"). On or about {date}, the parties entered into a written agreement pursuant to which Defendant agreed to provide certain services in exchange for compensation. Plaintiff alleges that Defendant materially breached the agreement by failing to perform its obligations in a timely and competent manner.</p>',
        f'<heading level="2" bold="true">II. ISSUES PRESENTED</heading>',
        f'<p align="justify" indent-first="36" spacing-after="12" line-spacing="2.0">1. Whether the Defendant\'s failure to deliver services by the contractual deadline constitutes a material breach.</p>',
        f'<p align="justify" indent-first="36" spacing-after="12" line-spacing="2.0">2. Whether the Plaintiff is entitled to consequential damages arising from the breach.</p>',
        f'<p align="justify" indent-first="36" spacing-after="12" line-spacing="2.0">3. Whether the arbitration clause in the agreement is enforceable.</p>',
        f'<heading level="2" bold="true">III. ANALYSIS</heading>',
    ]

    for i, arg in enumerate(arguments[:n_sections]):
        sub = chr(65 + i)  # A, B, C...
        heading_text = pick(rng, [
            "Breach of Contract", "Promissory Estoppel", "Statute of Limitations",
            "Summary Judgment Standard", "Punitive Damages", "Negligence",
            "Arbitration", "Injunctive Relief",
        ])
        lines.append(f'<heading level="3" italic="true">{sub}. {heading_text}</heading>')
        lines.append(f'<p align="justify" indent-first="36" spacing-after="12" line-spacing="2.0">{arg}</p>')

    lines.extend([
        f'<heading level="2" bold="true">IV. CONCLUSION</heading>',
        f'<p align="justify" indent-first="36" spacing-after="12" line-spacing="2.0">For the foregoing reasons, it is respectfully submitted that the Plaintiff\'s claims are meritorious and that the Court should grant the relief requested herein. The evidence establishes that the Defendant breached its contractual obligations and that the Plaintiff suffered damages as a direct and proximate result thereof.</p>',
        f'<p align="left" spacing-after="6">Respectfully submitted,</p>',
        f'<p align="left" spacing-after="6"><bold>{author}</bold></p>',
        f'<p align="left">Attorney for {plaintiff}</p>',
    ])

    return "\n".join(lines)
