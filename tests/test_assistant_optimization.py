import os
import asyncio
import hashlib
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from web.app import app
from services.advisor_service import (
    AdvisorService,
    compute_query_similarity,
    normalize_query_intent,
    compress_conversation_memory,
    synthesize_grounded_catalog_response,
    VERIFIED_SCHOLARSHIPS_CATALOG,
    _advisor_response_cache
)

client = TestClient(app)
advisor = AdvisorService()


def test_normalize_query_intent():
    """Verifies intent detection for common scholarship inquiries."""
    intent1, _ = normalize_query_intent("متى موعد انتهاء منحة بيرسون؟")
    assert intent1 == "canonical_deadline"

    intent2, _ = normalize_query_intent("What is the application deadline?")
    assert intent2 == "canonical_deadline"

    intent3, _ = normalize_query_intent("When does this scholarship close?")
    assert intent3 == "canonical_deadline"

    intent4, _ = normalize_query_intent("ما هي الشروط والمستندات المطلوبة للتقديم؟")
    assert intent4 == "canonical_requirements"

    intent5, _ = normalize_query_intent("كم الراتب الشهري وبدل السكن والتمويل؟")
    assert intent5 == "canonical_funding"

    intent6, _ = normalize_query_intent("رابط التقديم المعتمد والبوابة الرسمية")
    assert intent6 == "canonical_apply_link"

    intent7, _ = normalize_query_intent("منح تقترب مواعيد إغلاقها")
    assert intent7 == "canonical_closing_soon"

    intent8, _ = normalize_query_intent("منح ممولة بالكامل 100%")
    assert intent8 == "canonical_fully_funded"

    intent9, _ = normalize_query_intent("ابحث لي عن منح تناسب ملفي")
    assert intent9 == "canonical_recommendation"


def test_semantic_similarity_duplicate_detection():
    """Verifies that equivalent questions with different wording have high similarity (>= 0.70)."""
    # Test English deadline duplicate questions
    sim_en = compute_query_similarity("What is the deadline?", "When does this scholarship close?")
    assert sim_en >= 0.70, f"Expected similarity >= 0.70, got {sim_en}"

    # Test Arabic deadline duplicate questions
    sim_ar = compute_query_similarity("ما هو الموعد النهائي للمنحة؟", "متى ينتهي التقديم على المنحة؟")
    assert sim_ar >= 0.70, f"Expected similarity >= 0.70, got {sim_ar}"

    # Test funding duplicate questions
    sim_fund = compute_query_similarity("ما هي تفاصيل الراتب والسكن؟", "كم التمويل والمخصص الشهري للمنحة؟")
    assert sim_fund >= 0.70, f"Expected similarity >= 0.70, got {sim_fund}"

    # Test unrelated questions have low similarity
    sim_unrelated = compute_query_similarity("ما هو موعد إغلاق منحة بيرسون؟", "كيف أكتب رسالة دافع احترافية؟")
    assert sim_unrelated < 0.40, f"Expected similarity < 0.40, got {sim_unrelated}"


def test_zero_token_direct_grounded_catalog_lookup():
    """Verifies factual scholarship questions are resolved directly with 0 LLM tokens."""
    pearson = next(s for s in VERIFIED_SCHOLARSHIPS_CATALOG if s["id"] == "pearson")
    dummy_prof = {
        "full_name": "أحمد الفلسطيني",
        "degree": "Undergraduate",
        "majors": ["Computer Science"],
        "gpa": "92%",
        "country": "Palestine"
    }

    # 1. Deadline lookup
    res_deadline = synthesize_grounded_catalog_response("canonical_deadline", pearson, dummy_prof, VERIFIED_SCHOLARSHIPS_CATALOG)
    assert res_deadline is not None
    advice_d, chips_d = res_deadline
    assert "2026-11-06" in advice_d
    assert "University of Toronto" in advice_d
    assert len(chips_d) > 0

    # 2. Funding lookup
    res_funding = synthesize_grounded_catalog_response("canonical_funding", pearson, dummy_prof, VERIFIED_SCHOLARSHIPS_CATALOG)
    assert res_funding is not None
    advice_f, chips_f = res_funding
    assert "100%" in advice_f
    assert "رسوم" in advice_f

    # 3. Apply Link lookup
    res_link = synthesize_grounded_catalog_response("canonical_apply_link", pearson, dummy_prof, VERIFIED_SCHOLARSHIPS_CATALOG)
    assert res_link is not None
    advice_l, _ = res_link
    assert "https://future.utoronto.ca/pearson/" in advice_l

    # 4. Closing soon lookup
    res_soon = synthesize_grounded_catalog_response("canonical_closing_soon", None, dummy_prof, VERIFIED_SCHOLARSHIPS_CATALOG)
    assert res_soon is not None
    advice_s, _ = res_soon
    assert "تقترب مواعيد إغلاقها" in advice_s

    # 5. Fully funded lookup
    res_full = synthesize_grounded_catalog_response("canonical_fully_funded", None, dummy_prof, VERIFIED_SCHOLARSHIPS_CATALOG)
    assert res_full is not None
    advice_ff, _ = res_full
    assert "Fully Funded" in advice_ff or "100%" in advice_ff


def test_context_compression():
    """Verifies that multi-turn chat history is compressed into compact memory."""
    profile = {
        "full_name": "سارة علي",
        "degree": "Master's Degree",
        "majors": ["Artificial Intelligence"],
        "gpa": "89%",
        "country": "Palestine"
    }
    history = [
        {"role": "user", "text": "مرحباً، هل منحة المجر مناسبة لمعدلي؟"},
        {"role": "assistant", "text": "نعم منحة Stipendium Hungaricum ممتازة ومعدلك 89% يمنحك أفضلية تنافسية قوية جداً."},
        {"role": "user", "text": "ما هي الوثائق المطلوبة؟"},
        {"role": "assistant", "text": "تحتاج شهادة البكالوريوس، كشف العلامات، وشهادة كفاءة لغة إنجليزية."}
    ]
    compressed = compress_conversation_memory(history, profile)
    assert "سارة علي" in compressed
    assert "Artificial Intelligence" in compressed
    assert "89%" in compressed
    # Ensure it is ultra-compact (under 400 characters, ~80 tokens)
    assert len(compressed) < 400


def test_consult_advisor_endpoint_zero_token_direct():
    """Verifies the /api/advisor/chat endpoint returns zero-token direct catalog facts instantly."""
    payload = {
        "query": "ما هو الموعد النهائي لمنحة بيرسون؟",
        "scholarship_id": "pearson",
        "email": "test_student@example.com",
        "profile": {
            "full_name": "طارق محمود",
            "degree": "Undergraduate",
            "majors": ["Software Engineering"],
            "gpa": "90%",
            "country": "Palestine"
        }
    }
    resp = client.post("/api/advisor/chat", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["cached"] is True
    assert data["zero_token_direct"] is True
    assert data["model"] == "scholarpilot-grounded-catalog-engine"
    assert "2026-11-06" in data["advice"]
    assert len(data["follow_ups"]) > 0


def test_consult_advisor_semantic_duplicate_cache():
    """Reuses a scoped cache entry for its owner but never for another student."""
    email_a = "student-a@example.com"
    email_b = "student-b@example.com"
    scope_a = hashlib.sha256(email_a.encode("utf-8")).hexdigest()
    query = "Could you suggest a thoughtful application narrative structure?"
    normalized_query = normalize_query_intent(query)[1]
    cache_key = f"{scope_a}::pearson::{normalized_query}"
    _advisor_response_cache[cache_key] = {
        "timestamp": 9999999999,
        "user_scope": scope_a,
        "original_query": query,
        "normalized_q": normalized_query,
        "scholarship_id": "pearson",
        "intent": "general_consultation",
        "advice": "Personalized advice for student A.",
        "follow_ups": ["Review my checklist"]
    }

    original_client = advisor.client
    advisor.client = None
    try:
        same_user = asyncio.run(advisor.consult_ai_advisor(
            student_query=query,
            email=email_a,
            scholarship_id="pearson"
        ))
        other_user = asyncio.run(advisor.consult_ai_advisor(
            student_query=query,
            email=email_b,
            scholarship_id="pearson"
        ))
    finally:
        advisor.client = original_client
        _advisor_response_cache.pop(cache_key, None)

    assert same_user["cached"] is True
    assert same_user["duplicate_detected"] is True
    assert same_user["advice"] == "Personalized advice for student A."
    assert other_user["cached"] is False
    assert "Personalized advice for student A." not in other_user["advice"]


if __name__ == "__main__":
    test_normalize_query_intent()
    print("✅ test_normalize_query_intent passed")
    test_semantic_similarity_duplicate_detection()
    print("✅ test_semantic_similarity_duplicate_detection passed")
    test_zero_token_direct_grounded_catalog_lookup()
    print("✅ test_zero_token_direct_grounded_catalog_lookup passed")
    test_context_compression()
    print("✅ test_context_compression passed")
    test_consult_advisor_endpoint_zero_token_direct()
    print("✅ test_consult_advisor_endpoint_zero_token_direct passed")
    test_consult_advisor_semantic_duplicate_cache()
    print("✅ test_consult_advisor_semantic_duplicate_cache passed")
    print("🎉 ALL ASSISTANT OPTIMIZATION TESTS PASSED PERFECTLY!")
