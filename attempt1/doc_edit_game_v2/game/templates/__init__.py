from .legal_contract import gen_legal_contract
from .affidavit import gen_affidavit
from .case_brief import gen_case_brief
from .drug_label import gen_drug_label
from .clinical_study_report import gen_clinical_study_report
from .business_report import gen_business_report
from .tax_assessment import gen_tax_assessment

TEMPLATES = {
    "legal_contract": gen_legal_contract,
    "affidavit": gen_affidavit,
    "case_brief": gen_case_brief,
    "drug_label": gen_drug_label,
    "clinical_study_report": gen_clinical_study_report,
    "business_report": gen_business_report,
    "tax_assessment": gen_tax_assessment,
}
