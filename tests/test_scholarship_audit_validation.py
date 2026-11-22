import os
import unittest
import json
from datetime import datetime, date
from starlette.testclient import TestClient

os.environ["ENVIRONMENT"] = "test"

from web.app import app
from services.automation_service import AutomationService, is_deadline_expired
from services.advisor_service import AdvisorService
from services.scholarship_engine import ScholarshipEngine
from services.search_service import SearchService, CURATED_VERIFIED_SCHOLARSHIPS
from services.db import enforce_scholarship_deadlines, get_all_scholarships


class TestScholarshipAuditValidation(unittest.TestCase):
    """
    Test suite verifying scholarship audit requirements:
    1. Identification of scholarships with expired deadlines (relative to 2026-11-22).
    2. Proper marking of expired opportunities as inactive and expired status.
    3. Verification that expired opportunities are not presented as active verified scholarships.
    4. Validation preventing expired records from appearing in active search results.
    5. Content preservation (ensuring non-status/date attributes remain unchanged).
    """

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.automation = AutomationService()
        cls.advisor = AdvisorService()
        cls.engine = ScholarshipEngine()
        cls.search_svc = SearchService()
        cls.today = date.today()

    def test_01_expired_scholarships_identified_and_marked_in_storage(self):
        """Verifies Pearson and Chevening are identified and marked inactive/expired in data/live_scholarships.json."""
        with open("data/live_scholarships.json", "r", encoding="utf-8") as f:
            items = json.load(f)

        pearson = next(s for s in items if s["id"] == "pearson")
        chevening = next(s for s in items if s["id"] == "chevening")

        # Pearson expired on 2026-11-06 (16 days before 2026-11-22)
        self.assertFalse(pearson["is_active"], "Pearson scholarship must be marked inactive")
        self.assertEqual(pearson["status"], "منتهية (Expired)", "Pearson status must be 'منتهية (Expired)'")
        self.assertEqual(pearson["statusClass"], "sp-badge-danger", "Pearson badge class must be danger")
        self.assertEqual(pearson["deadlineDays"], "انتهى موعد التقديم", "Pearson deadlineDays must indicate expiration")

        # Chevening expired on 2026-11-20 (2 days before 2026-11-22)
        self.assertFalse(chevening["is_active"], "Chevening scholarship must be marked inactive")
        self.assertEqual(chevening["status"], "منتهية (Expired)", "Chevening status must be 'منتهية (Expired)'")
        self.assertEqual(chevening["statusClass"], "sp-badge-danger", "Chevening badge class must be danger")
        self.assertEqual(chevening["deadlineDays"], "انتهى موعد التقديم", "Chevening deadlineDays must indicate expiration")

        # Verify active opportunities remain active and unexpired
        active_items = [s for s in items if s["id"] not in ("pearson", "chevening")]
        self.assertEqual(len(active_items), 19, "There should be 19 active opportunities")
        for s in active_items:
            self.assertTrue(s["is_active"], f"Opportunity {s['id']} should be active")
            dl_date = datetime.strptime(s["deadline"], "%Y-%m-%d").date()
            self.assertGreaterEqual(dl_date, self.today, f"Active opportunity {s['id']} deadline must be in future")

    def test_02_scholarship_content_preserved_without_alteration(self):
        """Verifies scholarship content (coverage, requirements, universities, majors, links) was NOT altered."""
        with open("data/live_scholarships.json", "r", encoding="utf-8") as f:
            items = json.load(f)

        pearson = next(s for s in items if s["id"] == "pearson")
        self.assertEqual(pearson["name"], "Lester B. Pearson International Scholarship")
        self.assertEqual(pearson["university"], "جامعة تورنتو (University of Toronto)")
        self.assertEqual(pearson["country"], "كندا (Canada)")
        self.assertEqual(pearson["link"], "https://future.utoronto.ca/pearson/about/#apply")
        self.assertEqual(pearson["min_gpa_percentage"], 85.0)
        self.assertIn("Computer Science", pearson["target_majors"])
        self.assertIn("الرسوم الدراسية + السكن الجامعي", pearson["coverage"])

        chevening = next(s for s in items if s["id"] == "chevening")
        self.assertEqual(chevening["name"], "Chevening UK Government Scholarship")
        self.assertEqual(chevening["country"], "بريطانيا (UK)")
        self.assertEqual(chevening["link"], "https://www.chevening.org/apply/")
        self.assertEqual(chevening["min_gpa_percentage"], 80.0)
        self.assertIn("Public Policy", chevening["target_majors"])

    def test_03_active_search_api_filters_out_expired_scholarships(self):
        """Verifies /api/scholarships/live excludes expired opportunities from active search results by default."""
        resp = self.client.get("/api/scholarships/live")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["count"], 19, "Active count should be 19")

        ids = [s["id"] for s in data["scholarships"]]
        self.assertNotIn("pearson", ids, "Expired Pearson must not appear in active search results")
        self.assertNotIn("chevening", ids, "Expired Chevening must not appear in active search results")

        # Verify all returned scholarships are valid and active
        for opp in data["scholarships"]:
            self.assertTrue(opp.get("is_active", True), f"Opp {opp['id']} in active results must be active")
            self.assertFalse(is_deadline_expired(opp.get("deadline")), f"Opp {opp['id']} in active results must not be expired")

    def test_04_api_allows_including_expired_when_explicitly_requested(self):
        """Verifies /api/scholarships/live?include_expired=true returns all 21 records with accurate expired statuses."""
        resp = self.client.get("/api/scholarships/live?include_expired=true")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["count"], 21, "Total count including expired should be 21")

        by_id = {s["id"]: s for s in data["scholarships"]}
        self.assertIn("pearson", by_id)
        self.assertIn("chevening", by_id)
        self.assertFalse(by_id["pearson"]["is_active"])
        self.assertEqual(by_id["pearson"]["status"], "منتهية (Expired)")
        self.assertFalse(by_id["chevening"]["is_active"])
        self.assertEqual(by_id["chevening"]["status"], "منتهية (Expired)")

    def test_05_advisor_python_search_and_rank_excludes_expired_opportunities(self):
        """Verifies advisor python_search_and_rank does not recommend expired scholarships."""
        results = self.advisor.python_search_and_rank("Toronto Canada Computer Science", limit=10, active_only=True)
        res_ids = [s.get("id") for s in results]
        self.assertNotIn("pearson", res_ids, "Pearson should not appear in search & rank recommendations")
        self.assertNotIn("chevening", res_ids, "Chevening should not appear in search & rank recommendations")

    def test_06_advisor_deadline_analytics_tracks_expired_appropriately(self):
        """Verifies deadline analytics classifies expired scholarships and counts active properly."""
        analytics = self.advisor.get_deadline_analytics()
        self.assertTrue(analytics["success"])
        self.assertEqual(analytics["total_active"], 19, "Active count must be exactly 19")
        self.assertEqual(analytics["total_expired"], 2, "Expired count must be exactly 2")

        expired_names = [item["name"] for item in analytics.get("expired_opportunities", [])]
        self.assertTrue(any("Pearson" in n for n in expired_names), "Pearson must be in expired list")
        self.assertTrue(any("Chevening" in n for n in expired_names), "Chevening must be in expired list")

        # Expired items must NOT be in closing_this_week or closing_in_30_days
        week_names = [item["name"] for item in analytics.get("closing_this_week", [])]
        month_names = [item["name"] for item in analytics.get("closing_in_30_days", [])]
        self.assertFalse(any("Pearson" in n for n in week_names + month_names))
        self.assertFalse(any("Chevening" in n for n in week_names + month_names))

    def test_07_scholarship_engine_fallbacks_filter_expired_scholarships(self):
        """Verifies scholarship engine fallback directories return only active opportunities."""
        ug_fallbacks = self.engine._get_fallback_scholarships("undergraduate", "Palestine", active_only=True)
        ug_names = [s["name"] for s in ug_fallbacks]
        self.assertFalse(any("Pearson" in n for n in ug_names), "Pearson should be filtered out from active fallback list")

        grad_fallbacks = self.engine._get_fallback_scholarships("masters", "Palestine", active_only=True)
        grad_names = [s["name"] for s in grad_fallbacks]
        self.assertFalse(any("Chevening" in n for n in grad_names), "Chevening should be filtered out from active fallback list")

    def test_08_search_service_curated_verified_excludes_expired_from_results(self):
        """Verifies curated search candidates flag expired items and exclude them from injection."""
        active_curated = [c for c in CURATED_VERIFIED_SCHOLARSHIPS if not c.get("is_expired", False)]
        active_titles = [c["title"] for c in active_curated]
        self.assertFalse(any("Pearson" in t for t in active_titles), "Expired Pearson should not be active curated")
        self.assertFalse(any("UBC" in t for t in active_titles), "Expired UBC should not be active curated")
        self.assertFalse(any("Tomorrow's Leaders" in t for t in active_titles), "Expired Tomorrow's Leaders should not be active curated")

    def test_09_db_enforce_scholarship_deadlines_and_get_all_scholarships(self):
        """Verifies db layer deadline enforcement and get_all_scholarships filtering."""
        enforce_count = enforce_scholarship_deadlines()
        self.assertIsInstance(enforce_count, int)

        active_schs = get_all_scholarships(only_active=True)
        active_ids = {s.get("id") for s in active_schs}
        self.assertEqual(len(active_schs), 19)
        self.assertNotIn("pearson", active_ids)
        self.assertNotIn("chevening", active_ids)

        all_schs = get_all_scholarships(only_active=False)
        self.assertEqual(len(all_schs), 21)


if __name__ == "__main__":
    unittest.main()
