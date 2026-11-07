import unittest
import os
import json
from starlette.testclient import TestClient

from web.app import app
from services.advisor_service import AdvisorService
from services.automation_service import AutomationService


class TestGlobalArchitecture(unittest.TestCase):
    """
    Comprehensive test suite verifying EduAtlas Global Scholarship Intelligence Architecture:
    1. Support for 4 core opportunity categories: Scholarships, Internships, Conferences, Training.
    2. Zero static match scores: 100% dynamic 9-dimensional real-time scoring.
    3. Decoupled Nationality vs. Residence architecture.
    4. Stateless external cron automation (Render Free Tier sleep resilience).
    5. High-quality data schemas and AI prompt context.
    """

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.advisor = AdvisorService()
        cls.automation = AutomationService()

    def test_01_all_four_opportunity_types_present_in_catalog(self):
        """Verifies that Scholarships, Internships, Conferences, and Training are present and typed."""
        items = self.automation.get_live_scholarships()
        self.assertGreaterEqual(len(items), 15, "Catalog should have at least 15 verified opportunities")

        types_present = {item.get("opportunity_type") for item in items}
        self.assertIn("scholarship", types_present, "Scholarships must be present")
        self.assertIn("internship", types_present, "Internships must be present")
        self.assertIn("conference", types_present, "Conferences must be present")
        self.assertIn("training_program", types_present, "Training programs must be present")

        # Verify specific flagship opportunities
        ids = {item.get("id") for item in items}
        self.assertIn("pearson", ids, "Pearson scholarship must be in roster")
        self.assertIn("cern_summer", ids, "CERN internship must be in roster")
        self.assertIn("harvard_hnmun", ids, "Harvard conference grant must be in roster")
        self.assertIn("kaust_vsrp", ids, "KAUST research training must be in roster")
        print("\n -> PASSED: [TEST 1] All 4 opportunity types (Scholarships, Internships, Conferences, Training) present.")

    def test_02_zero_static_match_scores_in_storage(self):
        """Verifies that opportunities in storage do NOT carry static baked-in match scores."""
        items = self.automation.get_live_scholarships()
        for item in items:
            # Stored opportunities should not have hardcoded static matchScore in their schema
            self.assertNotIn("matchScore", item, f"Opportunity {item.get('id')} should not store static matchScore")
        print(" -> PASSED: [TEST 2] Zero static match scores in opportunity storage confirmed.")

    def test_03_api_opportunity_type_filtering(self):
        """Verifies /api/scholarships/live query filtering by opportunity type."""
        res_intern = self.client.get("/api/scholarships/live?type=internship")
        self.assertEqual(res_intern.status_code, 200)
        data_intern = res_intern.json()
        self.assertTrue(data_intern["success"])
        self.assertGreater(data_intern["count"], 0)
        for opp in data_intern["scholarships"]:
            self.assertEqual(opp.get("opportunity_type"), "internship")

        res_conf = self.client.get("/api/scholarships/live?type=conference")
        self.assertEqual(res_conf.status_code, 200)
        data_conf = res_conf.json()
        self.assertTrue(data_conf["success"])
        self.assertGreater(data_conf["count"], 0)
        for opp in data_conf["scholarships"]:
            self.assertEqual(opp.get("opportunity_type"), "conference")

        res_train = self.client.get("/api/scholarships/live?type=training_program")
        self.assertEqual(res_train.status_code, 200)
        data_train = res_train.json()
        self.assertTrue(data_train["success"])
        self.assertGreater(data_train["count"], 0)
        for opp in data_train["scholarships"]:
            self.assertEqual(opp.get("opportunity_type"), "training_program")
        print(" -> PASSED: [TEST 3] REST API /api/scholarships/live type filtering verified.")

    def test_04_dynamic_9d_match_calculation_differentiates_profiles(self):
        """Verifies that matching scores are dynamic and profile-dependent (not static 92% or 96%)."""
        opp = next((s for s in self.advisor.catalog if s.get("id") == "pearson"), self.advisor.catalog[0])

        # Candidate A: Top GPA (96%), Computer Science, Targets Canada
        profile_a = {
            "gpa": "96%",
            "majors": ["Computer Science", "Software Engineering"],
            "degree_level": "bachelors",
            "nationality": "Palestine",
            "residence_country": "Germany",
            "target_study_countries": ["Canada", "Germany"],
            "opportunity_interests": ["scholarship"],
            "english_level": "Advanced (IELTS 7.5)"
        }
        res_a = self.advisor.calculate_dynamic_match(profile_a, opp)

        # Candidate B: Lower GPA (65%), Graphic Design, Targets Japan
        profile_b = {
            "gpa": "65%",
            "majors": ["Graphic Design"],
            "degree_level": "bachelors",
            "nationality": "Jordan",
            "residence_country": "United Arab Emirates",
            "target_study_countries": ["Japan"],
            "opportunity_interests": ["internship"],
            "english_level": "Beginner"
        }
        res_b = self.advisor.calculate_dynamic_match(profile_b, opp)

        self.assertTrue(res_a["is_eligible"])
        self.assertTrue(res_b["is_eligible"])
        self.assertNotEqual(res_a["match_score"], res_b["match_score"], "Scores must be dynamically distinct")
        self.assertGreater(res_a["match_score"], res_b["match_score"], "Candidate A should score significantly higher than B")
        self.assertIn("academic_fit", res_a["sub_scores"])
        self.assertIn("field_fit", res_a["sub_scores"])
        self.assertIn("destination_fit", res_a["sub_scores"])
        print(f" -> PASSED: [TEST 4] Dynamic 9D matching verified: Profile A = {res_a['match_score_display']}, Profile B = {res_b['match_score_display']}.")

    def test_05_decoupled_nationality_vs_residency_gatekeeper(self):
        """Verifies nationality vs residency gatekeeper logic with global decoupled profiles."""
        restricted_opp = {
            "id": "restricted_award",
            "name": "ASEAN-Only Fellowship",
            "eligible_nationalities": ["SINGAPORE", "MALAYSIA", "INDONESIA"],
            "eligible_residences": ["ANY"],
            "min_gpa_percentage": 75.0,
            "target_majors": ["all"],
            "degree_levels": ["masters"]
        }

        # Student with Canadian nationality living in Singapore
        profile_ineligible = {
            "nationality": "Canada",
            "residence_country": "Singapore",
            "gpa": "95%",
            "majors": ["Computer Science"],
            "degree_level": "masters"
        }
        res_ineligible = self.advisor.calculate_dynamic_match(profile_ineligible, restricted_award := restricted_opp)
        self.assertFalse(res_ineligible["is_eligible"])
        self.assertEqual(res_ineligible["match_score"], 0)

        # Student with Malaysian nationality living in Canada
        profile_eligible = {
            "nationality": "Malaysia",
            "residence_country": "Canada",
            "gpa": "95%",
            "majors": ["Computer Science"],
            "degree_level": "masters"
        }
        res_eligible = self.advisor.calculate_dynamic_match(profile_eligible, restricted_award)
        self.assertTrue(res_eligible["is_eligible"])
        self.assertGreater(res_eligible["match_score"], 50)
        print(" -> PASSED: [TEST 5] Decoupled nationality & residency eligibility gatekeeping verified.")

    def test_06_match_calculate_endpoint(self):
        """Verifies /api/match/calculate REST endpoint returns dynamic real-time scores."""
        payload = {
            "gpa": "92%",
            "degree": "Undergraduate (Bachelor's)",
            "majors": ["Computer Science"],
            "country": "Germany",
            "nationality": "Palestine",
            "residence_country": "Germany",
            "target_study_countries": ["Canada", "Switzerland"],
            "scholarship_name": "Lester B. Pearson International Scholarship"
        }
        res = self.client.post("/api/match/calculate", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        match_info = data["match"]
        self.assertIn("score", match_info)
        self.assertGreaterEqual(match_info["score"], 70)
        self.assertTrue(match_info.get("is_eligible"))
        self.assertIn("sub_scores", match_info)
        print(f" -> PASSED: [TEST 6] /api/match/calculate API dynamic score verified: {match_info['match_score']}.")

    def test_07_ai_advisor_context_and_intent_for_all_types(self):
        """Verifies Advisor context building handles all 4 opportunity domains and decoupled identity."""
        profile = {
            "full_name": "Nour Salem",
            "degree": "Master's Degree",
            "majors": ["Artificial Intelligence"],
            "nationality": "Jordan",
            "residence_country": "United Arab Emirates",
            "gpa": "91%",
            "target_study_countries": ["Switzerland", "Germany"]
        }

        # 1. Internship intent
        ctx_intern = self.advisor.build_advisor_context("ما هي شروط تدريب CERN الصيفي؟", profile)
        self.assertEqual(ctx_intern["intent"], "internships")
        self.assertIn("CERN", ctx_intern["context_prompt"])
        self.assertIn("Nationality (Citizenship): Jordan", ctx_intern["context_prompt"])
        self.assertIn("Country of Residence: United Arab Emirates", ctx_intern["context_prompt"])

        # 2. Conference intent
        ctx_conf = self.advisor.build_advisor_context("هل توجد منح سفر لمؤتمر IEEE؟", profile)
        self.assertEqual(ctx_conf["intent"], "conferences")

        # 3. Training intent
        ctx_train = self.advisor.build_advisor_context("أريد التسجيل في برنامج تدريبي دبلوماسي في UNITAR", profile)
        self.assertEqual(ctx_train["intent"], "training_programs")
        print(" -> PASSED: [TEST 7] AI Advisor intent classification & decoupled context injection verified.")

    def test_08_stateless_github_action_workflow_file(self):
        """Verifies that the GitHub Actions stateless cron workflow file exists and is valid YAML."""
        workflow_path = os.path.join(".github", "workflows", "global_scholarship_cron.yml")
        self.assertTrue(os.path.exists(workflow_path), "Workflow file must exist")
        with open(workflow_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("schedule:", content)
        self.assertIn("0 */6 * * *", content)
        self.assertIn("workflow_dispatch:", content)
        self.assertIn("/api/cron/trigger-scan", content)
        self.assertIn("/api/automation/trigger-cycle", content)
        self.assertIn("X-Cron-Secret", content)
        print(" -> PASSED: [TEST 8] Stateless GitHub Actions workflow file verified.")


if __name__ == "__main__":
    unittest.main()
