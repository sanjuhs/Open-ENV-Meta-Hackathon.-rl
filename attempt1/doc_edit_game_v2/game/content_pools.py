"""Content pools for procedural document generation — legal + pharma + business domains."""

import random as _random

FIRST_NAMES = [
    "James", "Sarah", "Michael", "Emily", "David", "Jennifer", "Robert", "Maria",
    "William", "Elizabeth", "Richard", "Patricia", "Thomas", "Linda", "Charles",
    "Barbara", "Daniel", "Susan", "Matthew", "Jessica", "Anthony", "Karen",
    "Andrew", "Nancy", "Christopher", "Lisa", "Joseph", "Margaret", "Steven", "Dorothy",
    "Priya", "Raj", "Anita", "Vikram", "Neha", "Arjun", "Sanjay", "Meera",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson",
    "Sharma", "Patel", "Gupta", "Kumar", "Verma", "Singh",
]

COMPANY_NAMES = [
    "Acme Corporation", "GlobalTech Solutions", "Summit Industries", "Vertex Partners",
    "Pinnacle Holdings", "Atlas Dynamics", "Meridian Group", "Cascade Systems",
    "Horizon Enterprises", "Sterling Consulting", "Nexus Financial", "Vanguard Legal",
    "Pacific Ventures", "Continental Services", "Apex Analytics",
]

PHARMA_COMPANIES = [
    "Novapharm Inc.", "BioGenesis Therapeutics", "MedVista Laboratories",
    "Zenith Pharmaceuticals", "CureWell Biotech", "PharmaCore Solutions",
    "Helix Life Sciences", "Pristine Biologics", "OmniCure Research",
    "Vitalink Pharmaceuticals",
    "Novo Nordisk A/S", "AbbVie Inc.", "Pfizer Inc.", "Merck & Co.",
    "Eli Lilly and Company", "Johnson & Johnson", "AstraZeneca PLC",
]

DRUG_NAMES = [
    ("Xanitrol", "xanitrol hydrochloride"), ("Veloprin", "veloprin succinate"),
    ("Cortizane", "cortizane acetate"), ("Luminex", "luminex maleate"),
    ("Paxovent", "paxovent citrate"), ("Renostat", "renostat potassium"),
    ("Cardivex", "cardivex tartrate"), ("Neuroflex", "neuroflex sodium"),
    ("Dermacil", "dermacil propionate"), ("Hemofix", "hemofix sulfate"),
    ("Ozempex", "semaglutide"), ("Adalibra", "adalimumab"),
    ("Trulicex", "dulaglutide"), ("Jardivex", "empagliflozin"),
    ("Keytriva", "pembrolizumab"), ("Eliquisar", "apixaban"),
]

DRUG_INDICATIONS = [
    "treatment of moderate to severe hypertension in adult patients",
    "management of Type 2 diabetes mellitus as adjunct to diet and exercise",
    "reduction of major cardiovascular events in patients with established coronary artery disease",
    "treatment of major depressive disorder in adults",
    "management of chronic obstructive pulmonary disease (COPD)",
    "treatment of rheumatoid arthritis in adults who have had inadequate response to DMARDs",
    "prophylaxis of deep vein thrombosis in patients undergoing orthopedic surgery",
    "improvement of glycemic control in adults with Type 2 diabetes mellitus",
    "reduction of the risk of major adverse cardiovascular events in adults with Type 2 diabetes mellitus and established cardiovascular disease",
    "reducing signs and symptoms of moderately to severely active rheumatoid arthritis in adult patients",
    "treatment of adult patients with moderately to severely active Crohn's disease who have had an inadequate response to conventional therapy",
    "treatment of adult patients with moderately to severely active ulcerative colitis",
    "treatment of chronic weight management in adults with an initial body mass index (BMI) of 30 kg/m2 or greater",
]

ADVERSE_REACTIONS = [
    "headache", "nausea", "dizziness", "fatigue", "diarrhea", "insomnia",
    "dry mouth", "constipation", "elevated liver enzymes", "peripheral edema",
    "hypotension", "tachycardia", "rash", "pruritus", "arthralgia",
    "upper respiratory tract infection", "urinary tract infection",
    "pancreatitis", "diabetic retinopathy complications", "hypoglycemia",
    "acute kidney injury", "injection site reactions", "sinusitis",
    "abdominal pain", "vomiting", "decreased appetite", "dyspepsia",
    "acute gallbladder disease", "hypersensitivity reactions",
    "serious infections including tuberculosis", "invasive fungal infections",
    "hepatitis B virus reactivation", "demyelinating disease",
    "cytopenias", "heart failure worsening", "lupus-like syndrome",
]

# FDA boxed warning templates (from real Ozempic/Humira labels)
BOXED_WARNINGS = [
    "In rodents, {generic} causes dose-dependent and treatment-duration-dependent thyroid C-cell tumors at clinically relevant exposures. It is unknown whether {brand} causes thyroid C-cell tumors, including medullary thyroid carcinoma (MTC), in humans.",
    "{brand} is contraindicated in patients with a personal or family history of medullary thyroid carcinoma (MTC) or in patients with Multiple Endocrine Neoplasia syndrome type 2 (MEN 2).",
    "Increased risk of serious infections leading to hospitalization or death, including tuberculosis (TB), bacterial sepsis, invasive fungal infections (such as histoplasmosis), and infections due to other opportunistic pathogens.",
    "Lymphoma and other malignancies, some fatal, have been reported in patients treated with TNF blockers including {brand}.",
    "{brand} may increase the risk of serious cardiovascular thrombotic events, including myocardial infarction and stroke, which can be fatal. This risk may occur early in treatment and may increase with duration of use.",
]

# Indian tax/legal terminology (from real Harikrishna Durgi tax case)
TAX_SECTIONS = [
    "u/s 148A(b)", "u/s 148A(d)", "u/s 148", "u/s 142(1)", "u/s 144",
    "u/s 144B", "u/s 147", "u/s 143(3)", "u/s 156", "u/s 271(1)(c)",
]

TAX_TERMS = [
    "Assessment Year", "Previous Year", "assessee", "reassessment",
    "show cause notice", "faceless assessment", "best judgment assessment",
    "SFT/TDS/TCS high-value transactions", "non-compliance",
    "Income Tax Department", "Central Board of Direct Taxes",
    "DIT(S) Insight-NMS", "escaped income", "notice of demand",
]

# Corporate/annual report terminology (from real Reliance annual report)
CORPORATE_METRICS = [
    "Revenue from Operations", "EBITDA", "Profit After Tax", "Earnings Per Share",
    "Return on Capital Employed", "Net Debt to Equity Ratio", "Free Cash Flow",
    "Capital Expenditure", "Gross Margin", "Operating Margin",
    "Digital Services Revenue", "Retail Revenue", "Oil to Chemicals Revenue",
]

CORPORATE_SEGMENTS = [
    "Digital Services", "Retail", "Oil to Chemicals", "Oil and Gas",
    "Media and Entertainment", "Financial Services", "New Energy",
]

LEGAL_SECTIONS = [
    "DEFINITIONS", "SCOPE OF SERVICES", "TERM AND TERMINATION", "COMPENSATION",
    "CONFIDENTIALITY", "INTELLECTUAL PROPERTY", "REPRESENTATIONS AND WARRANTIES",
    "INDEMNIFICATION", "LIMITATION OF LIABILITY", "DISPUTE RESOLUTION",
    "GOVERNING LAW", "FORCE MAJEURE", "ASSIGNMENT", "NOTICES", "ENTIRE AGREEMENT",
    "AMENDMENTS", "SEVERABILITY", "WAIVER", "COUNTERPARTS",
]

COURT_NAMES = [
    "United States District Court for the Southern District of New York",
    "United States District Court for the Northern District of California",
    "Supreme Court of the State of Delaware",
    "United States District Court for the District of Columbia",
    "High Court of Delhi", "Supreme Court of India",
    "United States Bankruptcy Court for the District of Delaware",
]

CASE_CITATIONS = [
    "Smith v. Jones, 456 F.3d 789 (2d Cir. 2006)",
    "Global Corp. v. National Industries, 789 F. Supp. 2d 123 (S.D.N.Y. 2011)",
    "In re Pacific Holdings, 234 B.R. 567 (Bankr. D. Del. 2008)",
    "Anderson v. Technology Partners LLC, 567 U.S. 234 (2012)",
    "Johnson & Johnson v. Generic Pharma Inc., 890 F.3d 456 (Fed. Cir. 2018)",
    "Securities Exchange Commission v. Alpha Fund LP, 345 F. Supp. 3d 678 (D.D.C. 2019)",
]

STATES = [
    "California", "New York", "Texas", "Delaware", "Massachusetts",
    "Illinois", "Florida", "Washington", "Colorado", "Georgia",
]

DOLLAR_AMOUNTS = [
    "$50,000", "$100,000", "$250,000", "$500,000", "$750,000",
    "$1,000,000", "$1,500,000", "$2,000,000", "$5,000,000", "$10,000,000",
]

DATES = [
    "January 15, 2026", "February 28, 2026", "March 1, 2026", "April 7, 2026",
    "May 20, 2025", "June 30, 2025", "July 15, 2025", "August 1, 2025",
    "September 10, 2024", "October 22, 2024", "November 5, 2024", "December 31, 2024",
]

MISSPELLINGS = {
    "receive": "recieve", "management": "managment", "definitely": "definately",
    "separate": "seperate", "occurrence": "occurence", "accommodate": "accomodate",
    "necessary": "neccessary", "environment": "enviroment", "government": "goverment",
    "professional": "proffesional", "recommend": "reccomend", "maintenance": "maintainance",
    "independent": "independant", "committee": "commitee", "assessment": "assesment",
    "achievement": "achievment", "development": "developement", "immediately": "immediatly",
    "experience": "experiance", "performance": "preformance", "agreement": "agremeent",
    "department": "departmnet", "implementation": "implemenation", "comprehensive": "comperhensive",
    "communication": "comunication", "approximately": "approximatly", "significant": "signifcant",
    "responsibility": "responsibilty", "opportunity": "oppertunity", "requirements": "requirments",
    "acquisition": "aquisition", "beneficial": "benefical", "competitive": "competative",
    "consistency": "consistancy", "corporation": "corparation", "efficiency": "effeciency",
    "guarantee": "gaurantee", "infrastructure": "infastructure", "preliminary": "prelimanary",
    "recognition": "reconition", "regulatory": "regulatary", "specifically": "specificaly",
    "sufficient": "sufficent", "technical": "techincal", "transformation": "tranformation",
    "compliance": "complience", "quarterly": "quartely", "delivery": "delivrey",
    "schedule": "scedule", "revenue": "revnue", "analysis": "anaylsis",
    "pharmaceutical": "pharamceutical", "therapeutic": "thereputic", "efficacy": "efficasy",
    "adverse": "advsere", "clinical": "clinicla", "indication": "indicaiton",
    "plaintiff": "plantiff", "defendant": "defendent", "jurisdiction": "jurisdiciton",
    "indemnification": "indemnifcation", "arbitration": "arbitartion", "amendment": "ammendment",
    "affidavit": "affadavit", "interrogatory": "interogatory", "deposition": "depostion",
    "confidentiality": "confidentialty", "proprietary": "propreitary", "intellectual": "intelectual",
    "semaglutide": "semagultide", "adalimumab": "adalimimab", "subcutaneous": "subcutaneos",
    "contraindicated": "contraindicatd", "pancreatitis": "pancretitis", "retinopathy": "retinopthy",
    "hypoglycemia": "hypoglycmia", "cardiovascular": "cardivascular", "tuberculosis": "tuburculosis",
    "malignancy": "maligancy", "immunogenicity": "immunogenicty", "pharmacokinetics": "pharmacokenetics",
    "reassessment": "reassesment", "adjudication": "adjudicaiton", "contravention": "contravenion",
    "intimation": "intimiation", "undertaking": "undertaknig", "remuneration": "remunaration",
    "consolidated": "consolodated", "sustainability": "sustainabilty", "infrastructure": "infastructure",
    "manufacturing": "manufacuring", "shareholders": "sharehoders", "depreciation": "depriciation",
}

ALTERNATE_NAMES = {
    "James": "Robert", "Sarah": "Jennifer", "Michael": "William", "Emily": "Patricia",
    "David": "Thomas", "Jennifer": "Sarah", "Robert": "James", "Maria": "Linda",
    "Priya": "Neha", "Raj": "Arjun", "Sanjay": "Vikram",
}

ALTERNATE_COMPANIES = {
    "Acme Corporation": "Beta Industries", "GlobalTech Solutions": "LocalTech Services",
    "Summit Industries": "Valley Enterprises", "Vertex Partners": "Edge Associates",
    "Novapharm Inc.": "OldPharm Ltd.", "BioGenesis Therapeutics": "BioLegacy Research",
}

JUNK_CHARS = [
    "\u200b",  # zero-width space
    "\u00a0",  # non-breaking space
    "\u00ad",  # soft hyphen
    "\ufeff",  # BOM
    "\u200c",  # zero-width non-joiner
    "\u200d",  # zero-width joiner
    "\u2028",  # line separator
    "\u2029",  # paragraph separator
]

HIGHLIGHT_COLORS = ["yellow", "green", "red", "blue", "cyan", "magenta"]
ALIGNMENT_VALUES = ["left", "center", "right", "justify"]
UNDERLINE_STYLES = ["single", "double", "wavy"]
SPACING_VALUES = ["6", "12", "18", "24", "36"]
LINE_SPACING_VALUES = ["1.0", "1.15", "1.5", "2.0"]


def pick(rng: _random.Random, pool: list):
    return rng.choice(pool)

def full_name(rng: _random.Random) -> str:
    return f"{pick(rng, FIRST_NAMES)} {pick(rng, LAST_NAMES)}"

def drug_pair(rng: _random.Random) -> tuple:
    return pick(rng, DRUG_NAMES)

def fill_template(rng: _random.Random, template: str) -> str:
    replacements = {
        "party": pick(rng, ["the Vendor", "the Client", "the Contractor", "the Licensee"]),
        "days": str(rng.choice([5, 10, 15, 20, 30, 45, 60, 90])),
        "amount": pick(rng, DOLLAR_AMOUNTS),
        "installments": str(rng.choice([2, 3, 4, 6, 12])),
        "state": pick(rng, STATES),
        "percent": str(rng.randint(5, 45)),
        "date": pick(rng, DATES),
        "count": str(rng.randint(3, 25)),
        "ms": str(rng.randint(15, 350)),
        "year": str(rng.randint(2020, 2026)),
    }
    result = template
    for key, value in replacements.items():
        result = result.replace("{" + key + "}", value)
    return result
