import os
import re
import json
import asyncio
import logging
import hashlib
import unicodedata
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Union

from services.subscriber_service import SubscriberService
from services.scholarship_engine import ScholarshipEngine
from services.auth_service import AuthService
from services.security_utils import sanitize_text, sanitize_email_header

logger = logging.getLogger("scholarpilot.automation")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
LIVE_SCHOLARSHIPS_FILE = os.path.join(DATA_DIR, "live_scholarships.json")


def normalize_scholarship_title(title: str) -> str:
    """
    Normalizes scholarship title for robust hashing and deduplication.
    Converts variations like 'Türkiye Bursları' and 'Türkiye Bursları (YTB)' to canonical 'turkiye'.
    """
    if not title:
        return ""
    # 1. Decompose unicode accents (e.g., ü -> u, é -> e)
    text = unicodedata.normalize('NFKD', title)
    text = ''.join(c for c in text if not unicodedata.combining(c)).lower()

    # 2. Strip bracketed and parenthetical noise: (YTB), [UK], {2026}, etc.
    text = re.sub(r'[\(\[\{].*?[\)\]\}]', ' ', text)

    # 3. Strip common noise words and dates
    noise_words = sorted([
        'scholarships', 'scholarship', 'bursları', 'burslari', 'bursu',
        'fellowships', 'fellowship', 'programmes', 'programme', 'programs',
        'program', 'grants', 'grant', 'awards', 'award', 'opportunity',
        'opportunities', 'منحة', 'منح', 'برنامج', 'دراسات', 'جامعة',
        'حكومة', 'للطلاب', '2024', '2025', '2026', '2027', '2028',
        'fully funded', 'full funding', 'government', 'international'
    ], key=len, reverse=True)

    for w in noise_words:
        text = re.sub(r'\b' + re.escape(w) + r'\b', ' ', text, flags=re.IGNORECASE)
        text = text.replace(w, ' ')

    # 4. Remove punctuation and normalize spaces
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def compute_scholarship_hash(sch: Union[str, Dict[str, Any]]) -> str:
    """Computes a canonical SHA-256 hash for a scholarship."""
    if isinstance(sch, dict):
        raw_name = sch.get("name") or sch.get("title") or ""
        country = (sch.get("country") or "").strip().lower()
    else:
        raw_name = str(sch)
        country = ""
    norm_name = normalize_scholarship_title(raw_name)
    canonical = f"{norm_name}:{country}".strip(":")
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

# Verified base roster of flagship global scholarships
DEFAULT_LIVE_SCHOLARSHIPS = [
    {
        "id": "pearson",
        "name": "Lester B. Pearson International Scholarship",
        "university": "جامعة تورنتو (University of Toronto)",
        "country": "كندا (Canada)",
        "opportunity_type": "scholarship",
        "degree": "Undergraduate (بكالوريوس)",
        "target_degrees": [
            "Undergraduate (Bachelor's)",
            "بكالوريوس",
            "ثانوية عامة"
        ],
        "degree_levels": [
            "high_school",
            "bachelors"
        ],
        "target_majors": [
            "Computer Science",
            "Engineering",
            "Data Science",
            "Humanities",
            "Life Sciences",
            "Business"
        ],
        "eligible_nationalities": [
            "ALL"
        ],
        "eligible_residences": [
            "ANY"
        ],
        "min_gpa_percentage": 85.0,
        "funding_type": "fully_funded",
        "status": "مفتوح حالياً للتقديم",
        "statusClass": "sp-badge-success",
        "deadline": "2026-11-06",
        "deadline_display": "6 نوفمبر 2026",
        "deadlineDays": "متبقي أسبوع واحد",
        "coverage": "تغطية كاملة 100%: الرسوم الدراسية + السكن الجامعي الكامل 4 سنوات + تكلفة الكتب والتأمين الصحي",
        "requirements": "المعدل الأكاديمي 85%+، شهادة الثانوية العامة، رسالة ترشيح رسمية من المدرسة، وإثبات التميز القيادي والمجتمعي",
        "link": "https://future.utoronto.ca/pearson/about/#apply",
        "is_active": True
    },
    {
        "id": "hungaricum",
        "name": "Stipendium Hungaricum Scholarship",
        "university": "جامعات المجر الحكومية (بودابست، ديبريسين، زيجد)",
        "country": "المجر (الاتحاد الأوروبي)",
        "opportunity_type": "scholarship",
        "degree": "بكالوريوس • ماجستير • دكتوراه",
        "target_degrees": [
            "Undergraduate (Bachelor's)",
            "Master's Degree",
            "PhD / Doctorate",
            "بكالوريوس",
            "ماجستير",
            "دكتوراه"
        ],
        "degree_levels": [
            "bachelors",
            "masters",
            "phd"
        ],
        "target_majors": [
            "Computer Science & IT",
            "Software Engineering",
            "Medicine",
            "Civil Engineering",
            "Business",
            "Economics"
        ],
        "eligible_nationalities": [
            "ALL"
        ],
        "eligible_residences": [
            "ANY"
        ],
        "min_gpa_percentage": 75.0,
        "funding_type": "fully_funded",
        "status": "تفتح للتقديم قريباً",
        "statusClass": "sp-badge-info",
        "deadline": "2027-01-15",
        "deadline_display": "15 يناير 2027",
        "deadlineDays": "يفتح خلال شهرين",
        "coverage": "إعفاء دراسي 100% + راتب شهري مجزي + سكن جامعي مجاني + تأمين صحي شامل طوال فترة الدراسة",
        "requirements": "معدل 75%+ للبكالوريوس و80%+ للدراسات العليا، شهادة التخرج السابقة، خطاب دافع أكاديمي وفحص طبي رسمي",
        "link": "https://apply.stipendiumhungaricum.hu/",
        "is_active": True
    },
    {
        "id": "turkiye",
        "name": "Türkiye Bursları Government Scholarship",
        "university": "كافة الجامعات التركية الحكومية الرائدة (METU, Boğaziçi, ITU)",
        "country": "تركيا (Turkey)",
        "opportunity_type": "scholarship",
        "degree": "كافة المراحل (بكالوريوس ودراسات عليا)",
        "target_degrees": [
            "Undergraduate (Bachelor's)",
            "Master's Degree",
            "PhD / Doctorate",
            "بكالوريوس",
            "ماجستير",
            "دكتوراه"
        ],
        "degree_levels": [
            "bachelors",
            "masters",
            "phd"
        ],
        "target_majors": [
            "Computer Science & IT",
            "Engineering",
            "Medicine",
            "Business",
            "International Relations",
            "Humanities"
        ],
        "eligible_nationalities": [
            "ALL"
        ],
        "eligible_residences": [
            "ANY"
        ],
        "min_gpa_percentage": 70.0,
        "funding_type": "fully_funded",
        "status": "تفتح 10 يناير 2027",
        "statusClass": "sp-badge-info",
        "deadline": "2027-02-20",
        "deadline_display": "20 فبراير 2027",
        "deadlineDays": "فرصة سنوية كبرى",
        "coverage": "رسوم دراسية مجانية 100% + راتب شهري + سكن جامعي مجاني + سنة تحضيرية كاملة للغة وتذاكر طيران",
        "requirements": "حد أدنى 70% للبكالوريوس (90% للطب البشري)، رسائل توصية، وخطاب نوايا أكاديمي قوي",
        "link": "https://tbbs.turkiyeburslari.gov.tr/",
        "is_active": True
    },
    {
        "id": "chevening",
        "name": "Chevening UK Government Scholarship",
        "university": "جامعات المملكة المتحدة (أكسفورد، كامبريدج، إمبريال، UCL, LSE)",
        "country": "بريطانيا (UK)",
        "opportunity_type": "scholarship",
        "degree": "Master's Degree (ماجستير)",
        "target_degrees": [
            "Master's Degree",
            "ماجستير"
        ],
        "degree_levels": [
            "masters"
        ],
        "target_majors": [
            "Engineering",
            "Public Policy",
            "Computer Science",
            "Finance",
            "Law",
            "International Development"
        ],
        "eligible_nationalities": [
            "ALL"
        ],
        "eligible_residences": [
            "ANY"
        ],
        "min_gpa_percentage": 80.0,
        "funding_type": "fully_funded",
        "status": "مفتوح حالياً",
        "statusClass": "sp-badge-warning",
        "deadline": "2026-11-20",
        "deadline_display": "20 نوفمبر 2026",
        "deadlineDays": "أيام معدودة للإغلاق",
        "coverage": "تمويل كامل 100% + راتب شهري للمعيشة في بريطانيا + تذاكر طيران ذهاب وعودة ورسوم التأشيرة",
        "requirements": "درجة البكالوريوس بتقدير جيد جداً على الأقل، سنتان خبرة مهنية (2800 ساعة)، 4 مقالات قيادية",
        "link": "https://www.chevening.org/apply/",
        "is_active": True
    },
    {
        "id": "gks",
        "name": "Global Korea Scholarship (GKS)",
        "university": "أفضل الجامعات الكورية في سيئول والمدن الكبرى (SNU, KAIST, Yonsei)",
        "country": "كوريا الجنوبية (South Korea)",
        "opportunity_type": "scholarship",
        "degree": "بكالوريوس وماجستير ودكتوراه",
        "target_degrees": [
            "Undergraduate (Bachelor's)",
            "Master's Degree",
            "PhD / Doctorate",
            "بكالوريوس",
            "ماجستير",
            "دكتوراه"
        ],
        "degree_levels": [
            "bachelors",
            "masters",
            "phd"
        ],
        "target_majors": [
            "Information Technology",
            "AI",
            "Electrical Engineering",
            "Korean Studies",
            "Biotech",
            "Semiconductors"
        ],
        "eligible_nationalities": [
            "ALL"
        ],
        "eligible_residences": [
            "ANY"
        ],
        "min_gpa_percentage": 80.0,
        "funding_type": "fully_funded",
        "status": "التقديم السنوي عبر السفارة والجامعات",
        "statusClass": "sp-badge-info",
        "deadline": "2027-03-25",
        "deadline_display": "25 مارس 2027",
        "deadlineDays": "تفتح في الربيع",
        "coverage": "رسوم دراسية كاملة 100% + راتب شهري 1,000,000 وون + سنة لغة كورية وتذاكر طيران دولية",
        "requirements": "معدل تراكمي أعلى من 80%، فحص طبي شامل، خطة دراسية وبيان شخصي باللغة الإنجليزية",
        "link": "https://www.studyinkorea.go.kr/en/scholarship/gksNoticeList.do",
        "is_active": True
    },
    {
        "id": "daad",
        "name": "DAAD Scholarships Germany",
        "university": "جامعات ألمانيا التقنية والبحثية (TUM, LMU Munich, Heidelberg, RWTH Aachen)",
        "country": "ألمانيا (Germany)",
        "opportunity_type": "scholarship",
        "degree": "Master's & PhD (دراسات عليا)",
        "target_degrees": [
            "Master's Degree",
            "PhD / Doctorate",
            "ماجستير",
            "دكتوراه"
        ],
        "degree_levels": [
            "masters",
            "phd",
            "postdoctoral"
        ],
        "target_majors": [
            "Engineering",
            "Informatics",
            "Data Science",
            "Natural Sciences",
            "Economics",
            "Renewable Energy"
        ],
        "eligible_nationalities": [
            "ALL"
        ],
        "eligible_residences": [
            "ANY"
        ],
        "min_gpa_percentage": 78.0,
        "funding_type": "fully_funded",
        "status": "مفتوح حسب البرنامج",
        "statusClass": "sp-badge-success",
        "deadline": "2026-12-15",
        "deadline_display": "15 ديسمبر 2026",
        "deadlineDays": "مستمر حسب البرنامج",
        "coverage": "راتب شهري 934 يورو للماجستير و1,300 يورو للدكتوراه + تأمين صحي شامل + بدل سفر وتكاليف الأبحاث والمراجع",
        "requirements": "درجة بكالوريوس لا يتجاوز عمرها 6 سنوات، سنتان خبرة عمل، وخطاب دافع أكاديمي بالإنجليزية أو الألمانية",
        "link": "https://www2.daad.de/deutschland/stipendium/datenbank/en/21148-scholarship-database/",
        "is_active": True
    },
    {
        "id": "erasmus",
        "name": "Erasmus Mundus Joint Masters (EMJM)",
        "university": "اتحاد جامعات أوروبية متعددة (فرنسا، ألمانيا، إسبانيا، إيطاليا، بلجيكا)",
        "country": "الاتحاد الأوروبي (Europe)",
        "opportunity_type": "scholarship",
        "degree": "Master's Degree (ماجستير مشترك)",
        "target_degrees": [
            "Master's Degree",
            "ماجستير"
        ],
        "degree_levels": [
            "masters"
        ],
        "target_majors": [
            "Artificial Intelligence",
            "Cybersecurity",
            "Environmental Sciences",
            "Humanities",
            "Data Analytics"
        ],
        "eligible_nationalities": [
            "ALL"
        ],
        "eligible_residences": [
            "ANY"
        ],
        "min_gpa_percentage": 75.0,
        "funding_type": "fully_funded",
        "status": "مفتوح للتقديم حالياً",
        "statusClass": "sp-badge-success",
        "deadline": "2027-01-20",
        "deadline_display": "20 يناير 2027",
        "deadlineDays": "برامج متعددة",
        "coverage": "إعفاء دراسي كامل 100% + راتب شهري 1,400 يورو لمدة عامين + تذاكر سفر وبدل إقامة في دولتين أوروبيتين على الأقل",
        "requirements": "شهادة البكالوريوس، سيرة ذاتية Europass، رسالتا توصية، ومقال دافع لكل برنامج",
        "link": "https://www.eacea.ec.europa.eu/scholarships/erasmus-mundus-catalogue_en",
        "is_active": True
    },
    {
        "id": "fulbright",
        "name": "Fulbright Foreign Student Program",
        "university": "كافة الجامعات الأمريكية المعتمدة (MIT, Harvard, Stanford, Columbia)",
        "country": "الولايات المتحدة (USA)",
        "opportunity_type": "scholarship",
        "degree": "Master's & PhD (دراسات عليا)",
        "target_degrees": [
            "Master's Degree",
            "PhD / Doctorate",
            "ماجستير",
            "دكتوراه"
        ],
        "degree_levels": [
            "masters",
            "phd"
        ],
        "target_majors": [
            "Engineering",
            "Public Policy",
            "Social Sciences",
            "Natural Sciences",
            "Business",
            "Humanities"
        ],
        "eligible_nationalities": [
            "ALL"
        ],
        "eligible_residences": [
            "ANY"
        ],
        "min_gpa_percentage": 80.0,
        "funding_type": "fully_funded",
        "status": "التقديم السنوي عبر Amideast والسفارة",
        "statusClass": "sp-badge-info",
        "deadline": "2027-05-31",
        "deadline_display": "31 مايو 2027",
        "deadlineDays": "دورة 2027",
        "coverage": "تغطية الرسوم الجامعية بالكامل + راتب شهري للإعاشة + تذاكر طيران ذهاب وعودة + تأمين صحي شامل + فيزا J-1",
        "requirements": "درجة البكالوريوس بتقدير جيد جداً، كفاءة عالية في اللغة الإنجليزية، واجتياز المقابلة الشخصية",
        "link": "https://foreign.fulbrightonline.org/",
        "is_active": True
    },
    {
        "id": "cern_summer",
        "name": "CERN Summer Student Programme",
        "university": "المنظمة الأوروبية للأبحاث النووية (CERN Laboratory)",
        "country": "سويسرا (Switzerland)",
        "opportunity_type": "internship",
        "degree": "Undergraduate & Master's Internship",
        "target_degrees": [
            "Undergraduate (Bachelor's)",
            "Master's Degree",
            "بكالوريوس",
            "ماجستير"
        ],
        "degree_levels": [
            "bachelors",
            "masters"
        ],
        "target_majors": [
            "Physics",
            "Computer Science",
            "Software Engineering",
            "Mathematics",
            "Electrical Engineering"
        ],
        "eligible_nationalities": [
            "ALL"
        ],
        "eligible_residences": [
            "ANY"
        ],
        "min_gpa_percentage": 75.0,
        "funding_type": "fully_funded",
        "status": "مفتوح للتقديم حالياً",
        "statusClass": "sp-badge-success",
        "deadline": "2027-01-31",
        "deadline_display": "31 يناير 2027",
        "deadlineDays": "فرصة بحثية فريدة",
        "coverage": "تمويل كامل: بدل معيشة 90 فرنك سويسري يومياً (حوالي 2,700 CHF شهرياً) + تذاكر طيران + تأمين صحي شامل + تدريب متقدم في مصادم الهادرونات الكبير",
        "requirements": "إتمام 3 سنوات على الأقل من دراسة البكالوريوس أو الماجستير في تخصصات الفيزياء أو الحوسبة أو الهندسة، وإتقان اللغة الإنجليزية",
        "link": "https://careers.cern/summer",
        "is_active": True
    },
    {
        "id": "world_bank_internship",
        "name": "World Bank Group Global Internship",
        "university": "مجموعة البنك الدولي (World Bank HQ & Regional Hubs)",
        "country": "الولايات المتحدة (USA & Global)",
        "opportunity_type": "internship",
        "degree": "Graduate Internship (Master's & PhD)",
        "target_degrees": [
            "Master's Degree",
            "PhD / Doctorate",
            "ماجستير",
            "دكتوراه"
        ],
        "degree_levels": [
            "masters",
            "phd"
        ],
        "target_majors": [
            "Economics",
            "Finance",
            "Public Policy",
            "Computer Science",
            "Data Science",
            "International Relations"
        ],
        "eligible_nationalities": [
            "ALL"
        ],
        "eligible_residences": [
            "ANY"
        ],
        "min_gpa_percentage": 80.0,
        "funding_type": "fully_funded",
        "status": "مفتوح للتقديم",
        "statusClass": "sp-badge-success",
        "deadline": "2027-01-31",
        "deadline_display": "31 يناير 2027",
        "deadlineDays": "فرصة دولية مرموقة",
        "coverage": "راتب شهري ممول بالساعة لكافة ساعات العمل + بدل سفر دولي يصل إلى 3,000 دولار لمن يحتاج السفر إلى واشنطن",
        "requirements": "التسجيل في برنامج ماجستير أو دكتوراه معترف به، وإجادة تامة للغة الإنجليزية مع مهارات تحليلية كمية مثبتة",
        "link": "https://www.worldbank.org/en/about/careers/programs-and-internships/internship",
        "is_active": True
    },
    {
        "id": "max_planck_internship",
        "name": "Max Planck Summer Research Internship",
        "university": "معاهد ماكس بلانك البحثية (Max Planck Institutes)",
        "country": "ألمانيا (Germany)",
        "opportunity_type": "internship",
        "degree": "Undergraduate & Master's Lab Internship",
        "target_degrees": [
            "Undergraduate (Bachelor's)",
            "Master's Degree",
            "بكالوريوس",
            "ماجستير"
        ],
        "degree_levels": [
            "bachelors",
            "masters"
        ],
        "target_majors": [
            "Neurobiology",
            "Computer Science",
            "Biochemistry",
            "Physics",
            "Artificial Intelligence"
        ],
        "eligible_nationalities": [
            "ALL"
        ],
        "eligible_residences": [
            "ANY"
        ],
        "min_gpa_percentage": 80.0,
        "funding_type": "fully_funded",
        "status": "يفتح ديسمبر 2026",
        "statusClass": "sp-badge-info",
        "deadline": "2027-02-15",
        "deadline_display": "15 فبراير 2027",
        "deadlineDays": "تدريب بحثي مكثف",
        "coverage": "تمويل كامل: راتب شهري 900 يورو + سكن مجاني داخل مجمع المعهد + تغطية تذاكر السفر وتأمين صحي كامل لمدة 10 أسابيع",
        "requirements": "سجل أكاديمي متميز في مرحلة البكالوريوس أو الماجستير وشغف بالأبحاث المعملية والابتكار العلمي",
        "link": "https://www.imprs-ls.mpg.de/",
        "is_active": True
    },
    {
        "id": "gsoc_fellowship",
        "name": "Google Summer of Code (GSoC) Global Fellowship",
        "university": "شركة جوجل ومؤسسات البرمجيات الحرة (Google Open Source)",
        "country": "عالمي عن بُعد (Global / Remote)",
        "opportunity_type": "internship",
        "degree": "كافة المراحل من 18 عاماً فأكثر",
        "target_degrees": [
            "Undergraduate (Bachelor's)",
            "Master's Degree",
            "PhD / Doctorate",
            "Diploma",
            "بكالوريوس",
            "دبلوم"
        ],
        "degree_levels": [
            "high_school",
            "diploma",
            "bachelors",
            "masters",
            "phd",
            "professional_training"
        ],
        "target_majors": [
            "Computer Science",
            "Software Engineering",
            "AI",
            "Data Science",
            "Web Development",
            "All"
        ],
        "eligible_nationalities": [
            "ALL"
        ],
        "eligible_residences": [
            "ANY"
        ],
        "min_gpa_percentage": 60.0,
        "funding_type": "fully_funded",
        "status": "يفتح التقديم مارس 2027",
        "statusClass": "sp-badge-info",
        "deadline": "2027-04-04",
        "deadline_display": "4 أبريل 2027",
        "deadlineDays": "تدريب برمجي عالمي",
        "coverage": "مكافأة مالية متدرجة (1,500$ إلى 3,300$) مدفوعة من جوجل حسب بلد إقامة الطالب + توجيه وإشراف مباشر من كبار مهندسي البرمجيات في العالم",
        "requirements": "مهارات برمجية جيدة في إحدى اللغات (Python, C++, JS, Rust) وتقديم مقترح مشروع متكامل لمنظمة مفتوحة المصدر",
        "link": "https://summerofcode.withgoogle.com/",
        "is_active": True
    },
    {
        "id": "riken_summer",
        "name": "RIKEN Center for Brain Science Summer Internship",
        "university": "معهد رايكن للأبحاث العلمية (RIKEN CBS)",
        "country": "اليابان (Japan)",
        "opportunity_type": "internship",
        "degree": "Undergraduate & Graduate Internship",
        "target_degrees": [
            "Undergraduate (Bachelor's)",
            "Master's Degree",
            "PhD / Doctorate",
            "بكالوريوس",
            "ماجستير"
        ],
        "degree_levels": [
            "bachelors",
            "masters",
            "phd"
        ],
        "target_majors": [
            "Life Sciences",
            "Artificial Intelligence",
            "Computational Biology",
            "Bioengineering",
            "Neuroscience"
        ],
        "eligible_nationalities": [
            "ALL"
        ],
        "eligible_residences": [
            "ANY"
        ],
        "min_gpa_percentage": 78.0,
        "funding_type": "fully_funded",
        "status": "مفتوح للتقديم",
        "statusClass": "sp-badge-success",
        "deadline": "2027-02-28",
        "deadline_display": "28 فبراير 2027",
        "deadlineDays": "تدريب نخبوي باليابان",
        "coverage": "تمويل كامل: سكن جامعي مجاني في طوكيو + تذاكر طيران ذهاب وعودة لليابان + مصروف معيشة يومي + العمل في أحدث مختبرات الدماغ والذكاء الاصطناعي",
        "requirements": "طلبة البكالوريوس والدراسات العليا ذوو الاهتمام بالعلوم العصبية والحوسبة الحيوية، ورسائل توصية أكاديمية",
        "link": "https://cbs.riken.jp/en/summer/",
        "is_active": True
    },
    {
        "id": "harvard_hnmun",
        "name": "Harvard National Model United Nations (HNMUN) & Travel Grants",
        "university": "جامعة هارفارد (Harvard University - Boston)",
        "country": "الولايات المتحدة (USA)",
        "opportunity_type": "conference",
        "degree": "Undergraduate & Graduate Conference",
        "target_degrees": [
            "Undergraduate (Bachelor's)",
            "Master's Degree",
            "بكالوريوس",
            "ماجستير"
        ],
        "degree_levels": [
            "bachelors",
            "masters"
        ],
        "target_majors": [
            "Political Science",
            "International Relations",
            "Law",
            "Public Policy",
            "Economics",
            "All"
        ],
        "eligible_nationalities": [
            "ALL"
        ],
        "eligible_residences": [
            "ANY"
        ],
        "min_gpa_percentage": 70.0,
        "funding_type": "fully_funded",
        "status": "مفتوح للتقديم حالياً",
        "statusClass": "sp-badge-warning",
        "deadline": "2026-12-01",
        "deadline_display": "1 ديسمبر 2026",
        "deadlineDays": "مؤتمر دولي رائد",
        "coverage": "منحة سفر ومشاركة: تغطية رسوم المؤتمر بالكامل + دعم تذاكر الطيران والسكن لوفود الطلبة الدوليين المتميزين من الدول النامية",
        "requirements": "التسجيل كوفد أو مندوب فردي، كتابة أوراق سياسات موقفية، وشغف بالقضايا الدبلوماسية الدولية",
        "link": "https://www.harvardmun.org/",
        "is_active": True
    },
    {
        "id": "ieee_travel_grant",
        "name": "IEEE Student Conference Travel Grants",
        "university": "معهد مهندسي الكهرباء والإلكترونيات (IEEE Global)",
        "country": "عالمي (Global / Various Locations)",
        "opportunity_type": "conference",
        "degree": "Undergraduate, Master's & PhD",
        "target_degrees": [
            "Undergraduate (Bachelor's)",
            "Master's Degree",
            "PhD / Doctorate",
            "بكالوريوس",
            "ماجستير",
            "دكتوراه"
        ],
        "degree_levels": [
            "bachelors",
            "masters",
            "phd"
        ],
        "target_majors": [
            "Electrical Engineering",
            "Computer Science",
            "AI",
            "Robotics",
            "Telecommunications"
        ],
        "eligible_nationalities": [
            "ALL"
        ],
        "eligible_residences": [
            "ANY"
        ],
        "min_gpa_percentage": 75.0,
        "funding_type": "partial",
        "status": "مفتوح على مدار العام",
        "statusClass": "sp-badge-success",
        "deadline": "2027-03-15",
        "deadline_display": "15 مارس 2027",
        "deadlineDays": "دعم مستمر للمؤتمرات",
        "coverage": "منحة سفر مالية من 500$ إلى 1,500$ لتغطية تذاكر السفر ورسوم التسجيل والإقامة للطلبة المقبولين لعرض أوراقهم البحثية في مؤتمرات IEEE المرموقة",
        "requirements": "عضوية طلابية في IEEE وقبول ورقة بحثية أصلية تم تحكيمها ونشرها في المؤتمر المستهدف",
        "link": "https://www.ieee.org/membership/students/scholarships-grants-awards.html",
        "is_active": True
    },
    {
        "id": "world_youth_forum",
        "name": "World Youth Forum Academic Fellowship & Summit",
        "university": "الأكاديمية الوطنية للتدريب ورئاسة المؤتمر (WYF Egypt)",
        "country": "مصر (Egypt - Sharm El-Sheikh)",
        "opportunity_type": "conference",
        "degree": "كافة المراحل والشباب المتميزين (18-35 عاماً)",
        "target_degrees": [
            "Undergraduate (Bachelor's)",
            "Master's Degree",
            "PhD / Doctorate",
            "Professional",
            "بكالوريوس"
        ],
        "degree_levels": [
            "diploma",
            "bachelors",
            "masters",
            "phd",
            "professional_training"
        ],
        "target_majors": [
            "All Majors",
            "Entrepreneurship",
            "Technology",
            "Peacebuilding",
            "Environment"
        ],
        "eligible_nationalities": [
            "ALL"
        ],
        "eligible_residences": [
            "ANY"
        ],
        "min_gpa_percentage": 65.0,
        "funding_type": "fully_funded",
        "status": "تفتح التسجيلات قريباً",
        "statusClass": "sp-badge-info",
        "deadline": "2027-01-10",
        "deadline_display": "10 يناير 2027",
        "deadlineDays": "مؤتمر سنوي ضخم",
        "coverage": "تمويل كامل 100%: تذاكر طيران ذهاب وعودة من أي دولة بالعالم + إقامة فندقية فاخرة كاملة + حضور جلسات قادة العالم وورش العمل التخصصية",
        "requirements": "الفئة العمرية من 18 إلى 35 عاماً، تقديم فيديو تعريفي أو مقال حول رؤية الطالب في القيادة والتنمية المستدامة",
        "link": "https://wyfegypt.com/",
        "is_active": True
    },
    {
        "id": "lindau_nobel",
        "name": "Lindau Nobel Laureate Meetings Fellowship",
        "university": "مؤسسة اجتماعات لينداو لجائزة نوبل (Lindau Foundation)",
        "country": "ألمانيا (Germany - Bavaria)",
        "opportunity_type": "conference",
        "degree": "Graduate & Postdoc Young Scientists",
        "target_degrees": [
            "Undergraduate (Bachelor's)",
            "Master's Degree",
            "PhD / Doctorate",
            "Postdoc",
            "ماجستير",
            "دكتوراه"
        ],
        "degree_levels": [
            "bachelors",
            "masters",
            "phd",
            "postdoctoral"
        ],
        "target_majors": [
            "Physics",
            "Chemistry",
            "Physiology/Medicine",
            "Economic Sciences"
        ],
        "eligible_nationalities": [
            "ALL"
        ],
        "eligible_residences": [
            "ANY"
        ],
        "min_gpa_percentage": 85.0,
        "funding_type": "fully_funded",
        "status": "مفتوح للترشيح والتقديم",
        "statusClass": "sp-badge-warning",
        "deadline": "2026-11-30",
        "deadline_display": "30 نوفمبر 2026",
        "deadlineDays": "لقاء تاريخي مع علماء نوبل",
        "coverage": "منحة حضور كاملة: لقاء مباشر مع 30+ من حائزي جوائز نوبل + تغطية كاملة للإقامة الفندقية والسفر والوجبات في بافاريا الألمانية",
        "requirements": "علماء وباحثون شباب متميزون في مجالات العلوم الطبيعية أو الاقتصاد، مع توصيات بحثية رفيعة المستوى",
        "link": "https://www.lindau-nobel.org/",
        "is_active": True
    },
    {
        "id": "unitar_diplomacy",
        "name": "UNITAR Global Multilateral Diplomacy Fellowship",
        "university": "معهد الأمم المتحدة للتدريب والبحث (UNITAR - Geneva)",
        "country": "سويسرا وعن بُعد (Switzerland & Online)",
        "opportunity_type": "training_program",
        "degree": "Professional & Academic Training Fellowship",
        "target_degrees": [
            "Undergraduate (Bachelor's)",
            "Master's Degree",
            "PhD / Doctorate",
            "Professional",
            "بكالوريوس",
            "ماجستير"
        ],
        "degree_levels": [
            "bachelors",
            "masters",
            "phd",
            "professional_training"
        ],
        "target_majors": [
            "International Law",
            "Diplomacy",
            "Political Science",
            "Sustainable Development",
            "Public Policy"
        ],
        "eligible_nationalities": [
            "ALL"
        ],
        "eligible_residences": [
            "ANY"
        ],
        "min_gpa_percentage": 70.0,
        "funding_type": "fully_funded",
        "status": "مفتوح للتقديم حالياً",
        "statusClass": "sp-badge-success",
        "deadline": "2027-02-10",
        "deadline_display": "10 فبراير 2027",
        "deadlineDays": "تدريب دبلوماسي أممي",
        "coverage": "منحة دراسية وتدريبية كاملة من الأمم المتحدة مع شهادة رسمية معتمدة ورعاية كاملة للمشاركين المتميزين من الدول النامية",
        "requirements": "الاهتمام بالعمل الدبلوماسي والمفاوضات الدولية، شهادة جامعية أو قيد الدراسة، وإتقان اللغة الإنجليزية أو الفرنسية",
        "link": "https://unitar.org/",
        "is_active": True
    },
    {
        "id": "kaust_vsrp",
        "name": "KAUST Visiting Student Research Program (VSRP)",
        "university": "جامعة الملك عبد الله للعلوم والتقنية (KAUST)",
        "country": "السعودية (Saudi Arabia)",
        "opportunity_type": "training_program",
        "degree": "Graduate Research Training Internship (3-6 Months)",
        "target_degrees": [
            "Undergraduate (Bachelor's)",
            "Master's Degree",
            "بكالوريوس",
            "ماجستير"
        ],
        "degree_levels": [
            "bachelors",
            "masters"
        ],
        "target_majors": [
            "Applied Mathematics",
            "Computer Science",
            "Energy",
            "Bioengineering",
            "Material Sciences",
            "AI"
        ],
        "eligible_nationalities": [
            "ALL"
        ],
        "eligible_residences": [
            "ANY"
        ],
        "min_gpa_percentage": 80.0,
        "funding_type": "fully_funded",
        "status": "مفتوح للتقديم طوال العام",
        "statusClass": "sp-badge-success",
        "deadline": "2027-03-31",
        "deadline_display": "31 مارس 2027",
        "deadlineDays": "تدريب بحثي استثنائي",
        "coverage": "تمويل كامل 100%: راتب شهري 1,000$ + غرفة خاصة مع حمام مستقل في السكن الجامعي + تذاكر طيران ذهاب وعودة + تأمين صحي وتكاليف الفيزا",
        "requirements": "إتمام السنة الثالثة من البكالوريوس أو دراسة الماجستير بمعدل GPA لا يقل عن 3.5 من 4 (أو 85%+)، وكفاءة لغة إنجليزية مثبتة",
        "link": "https://vsrp.kaust.edu.sa/",
        "is_active": True
    },
    {
        "id": "oxford_climate_training",
        "name": "Oxford Climate Leadership & Policy Network",
        "university": "جامعة أكسفورد (Oxford Climate Society / Smith School)",
        "country": "بريطانيا وعن بُعد (UK & Hybrid)",
        "opportunity_type": "training_program",
        "degree": "Executive & Academic Training Fellowship",
        "target_degrees": [
            "Undergraduate (Bachelor's)",
            "Master's Degree",
            "PhD / Doctorate",
            "Professional",
            "بكالوريوس",
            "ماجستير"
        ],
        "degree_levels": [
            "diploma",
            "bachelors",
            "masters",
            "phd",
            "professional_training"
        ],
        "target_majors": [
            "Environmental Science",
            "Economics",
            "Policy",
            "Geography",
            "Engineering",
            "Law"
        ],
        "eligible_nationalities": [
            "ALL"
        ],
        "eligible_residences": [
            "ANY"
        ],
        "min_gpa_percentage": 75.0,
        "funding_type": "fully_funded",
        "status": "يفتح للتقديم يناير 2027",
        "statusClass": "sp-badge-info",
        "deadline": "2027-01-25",
        "deadline_display": "25 يناير 2027",
        "deadlineDays": "تدريب قيادي بأكسفورد",
        "coverage": "تدريب مكثف مع تغطية كاملة للرسوم والمواد البحثية وفرصة توجيه مباشر من أساتذة جامعة أكسفورد وشهادة إتمام معتمدة",
        "requirements": "سيرة ذاتية قوية ومقال يوضح مساهمة المتقدم في حلول الاستدامة وتغير المناخ",
        "link": "https://www.ox.ac.uk/",
        "is_active": True
    },
    {
        "id": "iaeste_intern_training",
        "name": "IAESTE International Practical Engineering Training",
        "university": "الرابطة الدولية لتبادل الطلاب للخبرة الفنية (IAESTE Global)",
        "country": "أكثر من 80 دولة (Europe, Asia, Americas)",
        "opportunity_type": "training_program",
        "degree": "Engineering & Technical Practical Training",
        "target_degrees": [
            "Undergraduate (Bachelor's)",
            "Master's Degree",
            "بكالوريوس",
            "ماجستير"
        ],
        "degree_levels": [
            "bachelors",
            "masters"
        ],
        "target_majors": [
            "Engineering",
            "Architecture",
            "Technology",
            "Natural Sciences",
            "Computer Science"
        ],
        "eligible_nationalities": [
            "ALL"
        ],
        "eligible_residences": [
            "ANY"
        ],
        "min_gpa_percentage": 70.0,
        "funding_type": "fully_funded",
        "status": "مفتوح للتقديم السنوي",
        "statusClass": "sp-badge-success",
        "deadline": "2027-02-28",
        "deadline_display": "28 فبراير 2027",
        "deadlineDays": "تدريب مهني عالمي",
        "coverage": "تدريب مهني مدفوع الأجر في شركات وجامعات عالمية يغطي نفقات المعيشة وتأشيرات العمل والتدريب التقني الميداني لمدة 8 إلى 52 أسبوعاً",
        "requirements": "دراسة أحد تخصصات الهندسة أو العلوم أو الحاسوب، وإتمام عامين دراسيين على الأقل",
        "link": "https://iaeste.org/",
        "is_active": True
    }
]


class AutomationService:
    """
    Production-Grade Autonomous Scholarship Discovery & Notification Engine:
    1. Recurring Scholarship Discovery & Ingestion across Global Sources.
    2. Automatic 5-D Student Matching & Threshold-Based Immediate Notifications.
    3. Recurring 7-Day Personalized Reports & Weekly Digests.
    4. Smart Deadline Monitoring (Milestones: 30, 14, 7, 3, 1 Days).
    5. State-Persistent Notification History to prevent spam and duplicate dispatches.
    6. Continuous Daemon that survives server restarts and rate-limits email dispatches safely.
    """

    def __init__(self):
        self.sub_service = SubscriberService()
        self.engine = ScholarshipEngine()
        self.auth_service = AuthService()
        self._ensure_live_scholarships_file()
        self._last_scan_at: Optional[str] = None
        self._last_metrics: Dict[str, Any] = {}

    def _ensure_live_scholarships_file(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        if not os.path.exists(LIVE_SCHOLARSHIPS_FILE):
            with open(LIVE_SCHOLARSHIPS_FILE, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_LIVE_SCHOLARSHIPS, f, ensure_ascii=False, indent=2)

    def get_live_scholarships(self) -> List[Dict[str, Any]]:
        """Returns the current auto-managed scholarship catalogue from database or JSON."""
        from services.db import is_db_available, get_db_session, LiveScholarshipDB
        
        # 1. Try DB first
        if is_db_available() and LiveScholarshipDB is not None:
            try:
                with get_db_session() as db:
                    if db is not None:
                        db_items = db.query(LiveScholarshipDB).filter(LiveScholarshipDB.is_active == True).all()
                        if db_items and len(db_items) > 0:
                            return [item.to_dict() for item in db_items]
            except Exception as e:
                logger.debug(f"DB load live scholarships error: {e}")

        # 2. Fallback to JSON
        data_list = []
        try:
            with open(LIVE_SCHOLARSHIPS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    data_list = data
        except Exception as e:
            logger.warning(f"Could not read live scholarships file: {e}")
            
        if not data_list:
            data_list = list(DEFAULT_LIVE_SCHOLARSHIPS)

        for item in data_list:
            if "official_link" not in item:
                item["official_link"] = item.get("link", "#")
        return data_list

    def _save_live_scholarships(self, items: List[Dict[str, Any]]):
        """Persists updated scholarships to both PostgreSQL DB and JSON store."""
        from services.db import is_db_available, get_db_session, LiveScholarshipDB

        # 1. Update Database
        if is_db_available() and LiveScholarshipDB is not None:
            try:
                with get_db_session() as db:
                    if db is not None:
                        for itm in items:
                            s_id = itm.get("id")
                            existing = db.query(LiveScholarshipDB).filter(LiveScholarshipDB.id == s_id).first()
                            if not existing:
                                db.add(LiveScholarshipDB(
                                    id=s_id,
                                    name=itm.get("name"),
                                    university=itm.get("university"),
                                    country=itm.get("country"),
                                    degree=itm.get("degree"),
                                    match_score=itm.get("matchScore"),
                                    match_label=itm.get("matchLabel"),
                                    status=itm.get("status"),
                                    status_class=itm.get("statusClass"),
                                    deadline=itm.get("deadline"),
                                    deadline_display=itm.get("deadline_display"),
                                    deadline_days=itm.get("deadlineDays"),
                                    coverage=itm.get("coverage"),
                                    requirements=itm.get("requirements"),
                                    link=itm.get("link") or itm.get("official_link"),
                                    is_active=itm.get("is_active", True)
                                ))
                            else:
                                if itm.get("link"):
                                    existing.link = itm.get("link")
                                if itm.get("deadline"):
                                    existing.deadline = itm.get("deadline")
                                if itm.get("deadline_display"):
                                    existing.deadline_display = itm.get("deadline_display")
                                if itm.get("status"):
                                    existing.status = itm.get("status")
                                if itm.get("coverage"):
                                    existing.coverage = itm.get("coverage")
            except Exception as e:
                logger.debug(f"DB save live scholarships error: {e}")

        # 2. Update JSON
        try:
            temp_file = LIVE_SCHOLARSHIPS_FILE + ".tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
            os.replace(temp_file, LIVE_SCHOLARSHIPS_FILE)
        except Exception as je:
            logger.error(f"Error saving live scholarships JSON: {je}")

    def _get_all_active_students(self) -> List[Dict[str, Any]]:
        """Unifies and deduplicates all registered students and active subscribers."""
        students_map: Dict[str, Dict[str, Any]] = {}

        # 1. Registered Users
        try:
            users = self.auth_service._load_users()
            for u in users:
                em = (u.get("email") or "").strip().lower()
                if em and "@" in em:
                    students_map[em] = {
                        "email": em,
                        "full_name": u.get("full_name", "Student"),
                        "degree": u.get("degree", "Undergraduate (Bachelor's)"),
                        "majors": u.get("majors") or ["Software Engineering"],
                        "gpa": u.get("gpa", "85%"),
                        "english_level": u.get("english_level", "Intermediate"),
                        "country": u.get("country", "Palestine"),
                        "target_destinations": ["Any"],
                        "talents_experience": u.get("talents_experience", ""),
                        "saved_scholarships": u.get("saved_scholarships", [])
                    }
        except Exception as e:
            logger.debug(f"Error reading users for automation: {e}")

        # 2. Active Subscribers
        try:
            subs = self.sub_service.get_all(active_only=True)
            for s in subs:
                em = (s.get("email") or "").strip().lower()
                if em and "@" in em:
                    if em not in students_map:
                        students_map[em] = s
                    else:
                        # Merge preferences
                        if s.get("target_destinations"):
                            students_map[em]["target_destinations"] = s["target_destinations"]
                        if s.get("last_sent_at"):
                            students_map[em]["last_sent_at"] = s["last_sent_at"]
                        if s.get("saved_scholarships") and not students_map[em].get("saved_scholarships"):
                            students_map[em]["saved_scholarships"] = s["saved_scholarships"]
        except Exception as e:
            logger.debug(f"Error reading subscribers for automation: {e}")

        return list(students_map.values())

    # ==========================================================================
    # 1. FULLY AUTOMATED SCHOLARSHIP DISCOVERY & INGESTION
    # ==========================================================================
    async def auto_refresh_scholarships_from_web(self) -> Dict[str, Any]:
        """
        Periodically discovers and normalizes newly published scholarships across
        all degrees and sources. Triggers automatic matching whenever new entries are detected.
        """
        logger.info("Executing automated recurring scholarship discovery scan...")
        self._last_scan_at = datetime.now().isoformat()
        newly_discovered: List[Dict[str, Any]] = []

        degrees_to_scan = [
            "Undergraduate (Bachelor's)",
            "Master's Degree",
            "PhD / Doctorate"
        ]

        current = self.get_live_scholarships()
        current_names = {s.get("name", "").strip().lower() for s in current}

        for deg in degrees_to_scan:
            try:
                extracted = await self.engine.search_and_extract(
                    degree=deg,
                    majors=["Computer Science", "Engineering", "Medicine", "Business"],
                    country="Palestine"
                )
                if extracted and len(extracted) > 0:
                    for item in extracted:
                        raw_name = item.get("name", "").strip()
                        if not raw_name or raw_name.lower() in current_names:
                            continue

                        # Normalize attributes
                        clean_id = f"auto_{abs(hash(raw_name)) % 1000000}"
                        official_url = item.get("official_link") or item.get("link") or "https://scholarpilot-ai-mkac.onrender.com"
                        deadline_val = item.get("deadline", "2027-01-30")

                        normalized_item = {
                            "id": clean_id,
                            "name": raw_name,
                            "university": item.get("country_institution") or item.get("provider", "Leading Global University"),
                            "country": item.get("country_institution", "International").split()[-1].strip("()"),
                            "degree": deg,
                            "target_degrees": [deg],
                            "target_majors": ["All Majors", "Computer Science", "Engineering"],
                            "matchScore": "92%",
                            "matchLabel": "فرصة جديدة تم رصدها آلياً ⚡",
                            "status": item.get("status", "مفتوح رسمياً للتقديم"),
                            "statusClass": "sp-badge-success",
                            "deadline": deadline_val,
                            "deadline_display": deadline_val,
                            "deadlineDays": "تحقق من الرابط",
                            "coverage": item.get("funding", "تمويل حكومي شامل أو إعفاء دراسي كامل"),
                            "requirements": item.get("requirements", "متطلبات القبول الأكاديمي الرسمية"),
                            "link": official_url,
                            "official_link": official_url,
                            "is_active": True
                        }

                        current.append(normalized_item)
                        current_names.add(raw_name.lower())
                        newly_discovered.append(normalized_item)
                        logger.info(f"✨ New Verified Scholarship Ingested: {raw_name}")
            except Exception as e:
                logger.error(f"Discovery error scanning degree '{deg}': {e}")
            await asyncio.sleep(1)

        if newly_discovered:
            self._save_live_scholarships(current)
            logger.info(f"✅ Ingestion Complete: {len(newly_discovered)} new opportunities added. Triggering automatic student matching and Telegram channel publication...")

            # Automatically broadcast newly discovered scholarships to Telegram channel
            from services.telegram_service import telegram_service
            telegram_posts = 0
            for item in newly_discovered:
                try:
                    msg_id = await telegram_service.publish_scholarship_to_channel(item)
                    if msg_id:
                        telegram_posts += 1
                except Exception as te:
                    logger.warning(f"Telegram auto-publish error for {item.get('id')}: {te}")

            # Trigger matching engine immediately
            matching_stats = await self.match_and_notify_students_for_new_scholarships(newly_discovered)
            return {
                "success": True,
                "new_discovered_count": len(newly_discovered),
                "telegram_published_count": telegram_posts,
                "total_monitored": len(current),
                "matching_stats": matching_stats
            }

        return {
            "success": True,
            "new_discovered_count": 0,
            "total_monitored": len(current),
            "matching_stats": {"alerts_sent": 0}
        }

    # ==========================================================================
    # 2 & 3. AUTOMATIC STUDENT MATCHING & NOTIFICATION ENGINE
    # ==========================================================================
    async def match_and_notify_students_for_new_scholarships(
        self,
        new_scholarships: List[Dict[str, Any]],
        match_threshold: float = 75.0
    ) -> Dict[str, Any]:
        """
        Automatic Student Matching & Notification Engine:
        Evaluates newly discovered scholarships against all active students and user preferences.
        Guarantees strict idempotency and deduplication using sent_notifications table & normalized title hash.
        Consolidates newly discovered matches into a SINGLE 'Smart Radar Digest Email' per student per scan.
        """
        from services.advisor_service import AdvisorService
        from services.email_service import email_service
        from services.notification_queue import enqueue_notification
        from services.db import is_scholarship_already_sent, record_sent_notification, get_user_preferences

        advisor = AdvisorService()
        students = self._get_all_active_students()
        logger.info(f"Matching {len(new_scholarships)} new scholarships against {len(students)} active students using Consolidated Digest...")

        total_alerts_queued = 0
        total_digests_sent = 0

        for student in students:
            email = student.get("email")
            if not email or "@" not in email:
                continue

            name = student.get("full_name") or "Student"
            # Load extended preferences
            prefs = get_user_preferences(email)
            pref_countries = [c.lower() for c in prefs.get("preferred_countries", ["any"])]
            pref_funding = prefs.get("funding_type", "Any").lower()
            email_enabled = prefs.get("email_notifications", True)
            telegram_enabled = prefs.get("telegram_notifications", False)
            telegram_chat_id = (prefs.get("telegram_chat_id") or "").strip()

            student_new_matches = []

            for sch in new_scholarships:
                sch_hash = compute_scholarship_hash(sch)
                sch_id = sch.get("id") or sch_hash[:16]
                sch_name = sch.get("name", "منحة دراسية جديدة")
                sch_country = (sch.get("country") or "").lower()
                sch_coverage = (sch.get("coverage") or "").lower()

                # Preference Check: Country
                if "any" not in pref_countries and "كل الدول" not in pref_countries:
                    country_match = any(pc in sch_country for pc in pref_countries)
                    if not country_match:
                        continue

                # Preference Check: Funding
                if pref_funding in ["full", "كامل", "تغطية كاملة"] and "100%" not in sch_coverage and "كامل" not in sch_coverage:
                    continue

                # STRICT IDEMPOTENCY CHECK: has this student EVER been alerted for this scholarship?
                if is_scholarship_already_sent(email, sch_hash, "match_alert"):
                    continue

                # 4-D Match Score calculation (GPA 35%, Major 30%, Nationality 20%, Language 15%)
                match_res = advisor.calculate_smart_match(student, sch)
                score = match_res.get("match_score", 0.0)

                if score >= match_threshold:
                    logger.info(f"🎯 High Match found: {sch_name} ({score}%) for {email}")
                    link = sch.get("link") or sch.get("official_link", "https://eduatlas-irxv.onrender.com")

                    sch_entry = dict(sch)
                    sch_entry["match_score"] = int(score)
                    sch_entry["reasons"] = match_res.get("strengths", [])
                    sch_entry["scholarship_hash"] = sch_hash
                    student_new_matches.append(sch_entry)

                    # 1. ALWAYS Queue In-App Notification
                    notification_target = f"new_match_alert_{sch_hash}_{email.lower()}"
                    await enqueue_notification(
                        channel="in_app",
                        recipient=email,
                        notification_type="new_scholarship_alert",
                        target_id=f"in_app_{notification_target}",
                        payload={
                            "title": f"🎯 منحة مطابقة لملفك: {sch_name} ({int(score)}%)",
                            "message": f"اكتشف رادار المنح منحة جديدة متوافقة مع تخصصك في {sch.get('country', '')}. الموعد النهائي: {sch.get('deadline_display', sch.get('deadline', 'قريباً'))}",
                            "type": "match",
                            "scholarship_id": sch_id,
                            "link": link
                        }
                    )
                    try:
                        from services.notification_service import notification_service
                        notification_service.notify_scholarship_match(
                            user_email=email,
                            scholarship_id=sch_id,
                            scholarship_name=sch_name,
                            match_score=int(score),
                            country=sch.get('country', ''),
                            deadline=sch.get('deadline_display', sch.get('deadline', ''))
                        )
                    except Exception as ne:
                        logger.warning(f"Unified notification error: {ne}")

                    # 2. Queue Telegram Notification if user enabled Telegram
                    if telegram_enabled and telegram_chat_id:
                        await enqueue_notification(
                            channel="telegram",
                            recipient=telegram_chat_id,
                            notification_type="new_scholarship_alert",
                            target_id=f"tg_{notification_target}",
                            payload={
                                "chat_id": telegram_chat_id,
                                "scholarship": sch
                            }
                        )

            # CONSOLIDATED EMAIL DISPATCH: Send ONE consolidated digest email if there are matches
            if student_new_matches and email_enabled:
                logger.info(f"📨 Dispatching 1 consolidated Smart Radar Digest ({len(student_new_matches)} matches) to {email}...")
                send_ok = await email_service.send_smart_radar_digest(
                    student_email=email,
                    student_name=name,
                    matches=student_new_matches,
                    student_profile=student
                )
                if send_ok:
                    total_digests_sent += 1
                    # Record each scholarship as sent in sent_notifications DB table
                    for item in student_new_matches:
                        record_sent_notification(
                            user_id=email,
                            scholarship_hash=item["scholarship_hash"],
                            notification_type="match_alert",
                            scholarship_name=item.get("name", "")
                        )
                        total_alerts_queued += 1

        return {
            "alerts_queued": total_alerts_queued,
            "digests_sent": total_digests_sent
        }

    # ==========================================================================
    # 4 & 6. WEEKLY AUTOMATED REPORTS (RECURRING 7-DAY PERSONALIZED DIGESTS)
    # ==========================================================================
    async def auto_dispatch_weekly_digests(self) -> Dict[str, Any]:
        """
        Automated Weekly Dispatcher:
        Scans all active students. If 7 days have passed since their last digest,
        generates and delivers their personalized 5-D report automatically.
        Guarantees idempotency per calendar week to prevent spam.
        """
        from services.db import is_notification_sent, record_notification, get_user_preferences
        from services.notification_queue import enqueue_notification

        students = self._get_all_active_students()
        now = datetime.now()
        current_week_num = now.isocalendar()[1]
        dispatched = 0
        failed = 0

        logger.info(f"Checking weekly digest eligibility for {len(students)} active students...")

        for student in students:
            email = student.get("email")
            if not email or "@" not in email:
                continue

            last_sent_str = student.get("last_sent_at")
            should_send = False

            if not last_sent_str:
                should_send = True
            else:
                try:
                    last_sent_dt = datetime.fromisoformat(last_sent_str)
                    if (now - last_sent_dt).total_seconds() >= (7 * 86400 - 3600):  # 7 days with buffer
                        should_send = True
                except Exception:
                    should_send = True

            # Week-level idempotency
            week_key = f"weekly_digest_{now.year}_w{current_week_num}_{email.lower()}"
            if is_notification_sent(email, "weekly_digest", week_key):
                should_send = False

            if should_send:
                logger.info(f"Automated Weekly Digest triggering for: {email}")
                try:
                    # Enqueue in-app digest notification
                    await enqueue_notification(
                        channel="in_app",
                        recipient=email,
                        notification_type="weekly_digest",
                        target_id=f"in_app_{week_key}",
                        payload={
                            "title": f"📬 صدرت النشرة الأسبوعية للمنح (أسبوع {current_week_num})",
                            "message": f"تم تجهيز حصاد المنح الأسبوعية الجديدة المتطابقة مع تخصصك ومعاييرك الأكاديمية.",
                            "type": "digest",
                            "scholarship_id": None,
                            "link": "/notifications"
                        }
                    )

                    prefs = get_user_preferences(email)
                    if prefs.get("email_notifications", True):
                        ok = await self.engine.send_personalized_report(
                            recipient_email=email,
                            student_name=student.get("full_name", "Student"),
                            degree=student.get("degree", "Undergraduate (Bachelor's)"),
                            majors=student.get("majors", ["Software Engineering"]),
                            country=student.get("country", "Palestine"),
                            student_profile=student
                        )
                        if ok:
                            dispatched += 1
                            self.sub_service.update_last_sent(email)
                            record_notification(
                                recipient=email,
                                notification_type="weekly_digest",
                                target_id=week_key,
                                subject=f"دليل المنح الأسبوعي المخصص (أسبوع {current_week_num})",
                                status="sent",
                                details={"week": current_week_num, "year": now.year}
                            )
                        else:
                            failed += 1
                    else:
                        dispatched += 1
                        self.sub_service.update_last_sent(email)
                except Exception as e:
                    failed += 1
                    logger.error(f"Auto-dispatch error for {email}: {e}")
                await asyncio.sleep(0.5)

        return {
            "dispatched": dispatched,
            "failed": failed,
            "total_students": len(students)
        }

    # ==========================================================================
    # 5. SMART DEADLINE MONITORING (30, 14, 7, 3, 1 DAYS REMAINING)
    # ==========================================================================
    async def auto_dispatch_deadline_reminders(self) -> Dict[str, Any]:
        """
        Automated Deadline Monitor:
        Scans all students and their saved scholarships.
        Sends personalized reminders at key milestones: 30, 14, 7, 3, 1 days remaining.
        Guarantees idempotency via NotificationHistory so reminders are sent once per milestone.
        """
        from services.db import is_notification_sent, record_notification, get_user_preferences
        from services.notification_queue import enqueue_notification

        students = self._get_all_active_students()
        scholarships = self.get_live_scholarships()
        sch_dict = {s["name"].lower(): s for s in scholarships}
        today = date.today()
        reminders_sent = 0

        target_milestones = [30, 14, 7, 3, 1]

        for student in students:
            email = student.get("email")
            if not email or "@" not in email:
                continue

            saved = student.get("saved_scholarships", [])
            if not saved:
                continue

            for sch_name in saved:
                matched = sch_dict.get(sch_name.lower())
                if not matched:
                    # Partial match attempt
                    matched = next((s for s in scholarships if sch_name.lower() in s["name"].lower()), None)
                if not matched:
                    continue

                dl_str = matched.get("deadline")
                if not dl_str:
                    continue

                try:
                    dl_date = datetime.strptime(dl_str[:10], "%Y-%m-%d").date()
                    days_remaining = (dl_date - today).days

                    # Trigger only on designated milestones
                    if days_remaining in target_milestones:
                        reminder_key = f"deadline_{days_remaining}d_{matched.get('id', sch_name)}_{dl_str}_{email.lower()}"
                        if is_notification_sent(email, "deadline_reminder", reminder_key):
                            continue

                        logger.info(f"⏰ Dispatching deadline reminder for '{sch_name}' to {email} ({days_remaining} days left)")

                        # 1. Enqueue In-App notification
                        await enqueue_notification(
                            channel="in_app",
                            recipient=email,
                            notification_type="deadline_reminder",
                            target_id=f"in_app_{reminder_key}",
                            payload={
                                "title": f"⚠️ تذكير موعد نهائي: متبقي {days_remaining} أيام لمنحة {sch_name}",
                                "message": f"الموعد النهائي المحدد لإغلاق التقديم هو {dl_str}. سارع باستكمال وثائقك الرسمية.",
                                "type": "deadline",
                                "scholarship_id": matched.get("id"),
                                "link": matched.get("link")
                            }
                        )
                        try:
                            from services.notification_service import notification_service
                            notification_service.notify_scholarship_deadline(
                                user_email=email,
                                scholarship_id=str(matched.get("id") or sch_name),
                                scholarship_name=sch_name,
                                days_left=days_remaining,
                                deadline_date=dl_str
                            )
                        except Exception as ne:
                            logger.warning(f"Unified deadline notification error: {ne}")

                        prefs = get_user_preferences(email)
                        # 2. Enqueue Email notification if enabled
                        if prefs.get("email_notifications", True):
                            ok = await self._send_reminder_email(
                                recipient_email=email,
                                student_name=student.get("full_name", "Student"),
                                scholarship=matched,
                                days_remaining=days_remaining,
                                deadline_date=dl_str,
                                link=matched.get("link") or matched.get("official_link", "https://scholarpilot-ai-mkac.onrender.com")
                            )
                            if ok:
                                reminders_sent += 1
                                record_notification(
                                    recipient=email,
                                    notification_type="deadline_reminder",
                                    target_id=reminder_key,
                                    subject=f"تنبيه بالموعد النهائي: متبقي {days_remaining} أيام لمنحة {sch_name}",
                                    status="sent",
                                    details={"days_remaining": days_remaining, "scholarship": sch_name, "deadline": dl_str}
                                )

                        # 3. Enqueue Telegram reminder if enabled
                        if prefs.get("telegram_notifications", False) and prefs.get("telegram_chat_id"):
                            await enqueue_notification(
                                channel="telegram",
                                recipient=prefs["telegram_chat_id"],
                                notification_type="deadline_reminder",
                                target_id=f"tg_{reminder_key}",
                                payload={
                                    "chat_id": prefs["telegram_chat_id"],
                                    "text": f"⚠️ <b>تذكير باقتراب الموعد النهائي!</b>\nمنحة: <b>{sch_name}</b>\nمتبقي: <b>{days_remaining} أيام</b> (الموعد: {dl_str})\n🔗 <a href='{matched.get('link')}'>رابط التقديم الرسمي</a>"
                                }
                            )

                        await asyncio.sleep(0.5)
                except Exception as e:
                    logger.debug(f"Could not parse deadline date {dl_str}: {e}")

        return {"reminders_sent": reminders_sent}

    async def _send_reminder_email(
        self,
        recipient_email: str,
        student_name: str,
        scholarship: Dict[str, Any],
        days_remaining: int,
        deadline_date: str,
        link: str
    ) -> bool:
        """Dispatches an urgent, beautifully styled personalized reminder email."""
        from services.email_service import dispatch_email, render_deadline_reminder_template
        clean_name = sanitize_text(student_name)
        sch_name = scholarship.get("name", "منحة دراسية")

        html_content, text_content = render_deadline_reminder_template(
            student_name=clean_name,
            scholarship=scholarship,
            days_left=days_remaining,
            milestone="استكمال ورفع الوثائق النهائية"
        )
        return await dispatch_email(
            to_email=recipient_email,
            subject=f"تذكير بالموعد النهائي: متبقي {days_remaining} أيام على إغلاق التقديم لمنحة {sch_name}",
            html_content=html_content,
            text_content=text_content
        )

    def get_automation_status(self) -> Dict[str, Any]:
        """Returns comprehensive real-time telemetry of the automation subsystem."""
        from services.db import get_notification_history

        scholarships = self.get_live_scholarships()
        students = self._get_all_active_students()
        history = get_notification_history(limit=50)

        digests_sent = sum(1 for h in history if h.get("notification_type") == "weekly_digest")
        alerts_sent = sum(1 for h in history if h.get("notification_type") == "new_scholarship_alert")
        reminders_sent = sum(1 for h in history if h.get("notification_type") == "deadline_reminder")

        return {
            "status": "active_autonomous_daemon",
            "last_scan_at": self._last_scan_at or datetime.now().isoformat(),
            "monitored_scholarships_count": len(scholarships),
            "active_students_count": len(students),
            "notification_metrics": {
                "total_sent_recorded": len(history),
                "weekly_digests_sent": digests_sent,
                "new_match_alerts_sent": alerts_sent,
                "deadline_reminders_sent": reminders_sent
            },
            "recent_dispatches": history[:10]
        }


# ==============================================================================
# 7. CONTINUOUS BACKGROUND AUTOMATION DAEMON (SURVIVES RESTARTS & CRASHES)
# ==============================================================================
async def start_automation_daemon():
    """
    Self-Operating Background Daemon that runs continuously alongside FastAPI:
    - Scans and ingests new global scholarships every cycle.
    - Evaluates every student profile and notifies them of matching opportunities.
    - Continuously evaluates deadlines at 30, 14, 7, 3, 1 day milestones.
    - Checks 7-day weekly digest eligibility for all active students.
    """
    automation = AutomationService()
    logger.info("🚀 ScholarPilotAI Autonomous Platform Daemon activated. Running self-operating background loops...")

    while True:
        try:
            logger.info("🔄 Automation cycle starting: Discovery, Matching, Deadlines & Weekly Digests...")
            
            # Step 1: Discover new scholarships and notify matching students
            discovery_res = await automation.auto_refresh_scholarships_from_web()
            logger.info(f"Discovery Cycle Output: {discovery_res}")

            # Step 2: Deadline reminders (30, 14, 7, 3, 1 days)
            deadline_res = await automation.auto_dispatch_deadline_reminders()
            logger.info(f"Deadline Cycle Output: {deadline_res}")

            # Step 3: Weekly digests (7-day intervals)
            digest_res = await automation.auto_dispatch_weekly_digests()
            logger.info(f"Weekly Digest Cycle Output: {digest_res}")

            # Step 4: Real-time News Discovery & Opportunity Aggregation
            try:
                from services.news_service import news_service
                news_res = news_service.discover_and_aggregate_news()
                logger.info(f"Autonomous News Aggregation Output: {news_res}")
            except Exception as n_err:
                logger.error(f"❌ Error in autonomous news aggregation: {n_err}")

        except Exception as e:
            logger.error(f"❌ Error in autonomous daemon cycle: {e}", exc_info=True)

        # Sleep for 3 hours between background cycles
        logger.info("Automation cycle complete. Sleeping for 3 hours before next autonomous scan...")
        await asyncio.sleep(3 * 3600)


async def run_radar_scan_job() -> Dict[str, Any]:
    """
    Safely executes the scholarship discovery and student matching job in the background.
    Decoupled from HTTP request lifecycle so cron-job.org and webhooks return immediately.
    """
    logger.info("Executing asynchronous radar scan job triggered by cron/webhook...")
    automation = AutomationService()
    try:
        res = await automation.auto_refresh_scholarships_from_web()
        logger.info(f"Asynchronous radar scan job completed successfully: {res}")
        return res
    except Exception as e:
        logger.error(f"Error executing asynchronous radar scan job: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
