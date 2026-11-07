import os, sys, re
sys.path.insert(0, os.path.abspath('.'))

import unittest
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
from web.app import app

class TestStickyNavbarAndRoutingModifications(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_01_browser_tab_titles_and_favicon(self):
        """[REQ 1] Verifies dynamic browser tab titles and favicons across all routes."""
        expected_titles = {
            "/": "EduAtlas",
            "/radar": "رادار المنح | EduAtlas",
            "/assistant": "المساعد الذكي | EduAtlas",
            "/community": "مجتمع الطلبة | EduAtlas",
            "/news": "أخبار المنح | EduAtlas",
            "/account": "حسابي | EduAtlas",
            "/dashboard": "حسابي | EduAtlas",
            "/notifications": "مركز التنبيهات | EduAtlas",
        }

        for path, exp_title in expected_titles.items():
            res = self.client.get(path, follow_redirects=False)
            self.assertEqual(res.status_code, 200, f"Route {path} did not return 200")
            soup = BeautifulSoup(res.text, 'html.parser')
            
            title_tag = soup.find('title')
            self.assertIsNotNone(title_tag, f"No <title> found on {path}")
            self.assertEqual(title_tag.text.strip(), exp_title, f"Wrong title on {path}")
            
            # Check favicon
            favicon_links = soup.find_all('link', rel=lambda r: r and 'icon' in r)
            self.assertGreaterEqual(len(favicon_links), 1, f"No favicon link on {path}")
            self.assertTrue(any('/favicon.ico' in link.get('href', '') or 'static/img' in link.get('href', '') for link in favicon_links))

        print(" -> PASSED: [REQ 1] Browser Tab Titles and Favicon Links Verified.")

    def test_02_remove_how_it_works_and_faq_from_navbar(self):
        """[REQ 2] Verifies 'كيف نعمل' and 'الأسئلة الشائعة' are deleted from navbar and mobile drawer."""
        routes = ["/", "/radar", "/assistant", "/community", "/news", "/account", "/dashboard"]
        for path in routes:
            res = self.client.get(path)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            header = soup.find('header')
            self.assertIsNotNone(header, f"Header not found on {path}")
            self.assertNotIn("كيف نعمل", header.text)
            self.assertNotIn("الأسئلة الشائعة", header.text)
            
            drawer = soup.find(id='mobileNavDrawer')
            if drawer:
                self.assertNotIn("كيف نعمل", drawer.text)
                self.assertNotIn("الأسئلة الشائعة", drawer.text)

        print(" -> PASSED: [REQ 2] 'كيف نعمل' and 'الأسئلة الشائعة' completely removed from Top Nav & Drawer.")

    def test_03_my_account_with_auth_guard(self):
        """[REQ 3] Verifies 'حسابي' item exists in navbar and mobile drawer with handleMyAccountNavigation."""
        routes = ["/", "/radar", "/assistant", "/community", "/news", "/account", "/dashboard"]
        for path in routes:
            res = self.client.get(path)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            header = soup.find('header')
            account_btn = header.find(id='navMyAccountBtn')
            self.assertIsNotNone(account_btn, f"navMyAccountBtn not found in header on {path}")
            self.assertIn("حسابي", account_btn.text)
            self.assertIn("handleMyAccountNavigation", account_btn.get('onclick', ''))
            
            # Script check for Auth Guard logic and toast prompt
            self.assertIn("function handleMyAccountNavigation", res.text)
            self.assertIn("يرجى تسجيل الدخول أو إنشاء حساب أولاً للوصول إلى صفحة حسابك", res.text)
            self.assertIn("window.location.href = '/account?next=/account'", res.text)

        print(" -> PASSED: [REQ 3] 'حسابي' (My Account) with Auth Guard and friendly toast prompt verified.")

    def test_04_persistent_sticky_navbar_across_all_pages(self):
        """[REQ 4] Verifies persistent sticky navbar on all pages with active page highlighting."""
        routes = ["/", "/radar", "/assistant", "/community", "/news", "/dashboard"]
        for path in routes:
            res = self.client.get(path)
            soup = BeautifulSoup(res.text, 'html.parser')
            header = soup.find('header')
            self.assertIsNotNone(header)
            
            # Verify persistent sticky CSS properties
            classes = header.get('class', [])
            style = header.get('style', '')
            self.assertIn('sp-sticky-nav', classes)
            self.assertIn('sticky', classes)
            self.assertIn('position: sticky', style)
            self.assertIn('backdrop-filter: blur(12px)', style)
            
            # Verify active state
            if path in ("/dashboard", "/account"):
                btn = header.find(id='navMyAccountBtn')
                self.assertTrue(any(('emerald' in c or 'blue' in c) for c in btn.get('class', [])))
            else:
                nav = header.find('nav')
                self.assertIsNotNone(nav, f"<nav> not found in header on {path}")
                active_link = nav.find('a', href=path)
                self.assertIsNotNone(active_link, f"Nav link for {path} not found in <nav>")
                classes_str = " ".join(active_link.get('class', []))
                self.assertTrue(('text-emerald-700' in classes_str or 'text-blue-600' in classes_str), f"Active primary class missing on link {path}")

        print(" -> PASSED: [REQ 4] Persistent Sticky Navbar and Active Highlights Verified Across Pages.")

    def test_05_separate_and_hide_radar_from_home(self):
        """[REQ 5] Verifies #radarSection is hidden on / and standalone /radar page exists."""
        # Homepage check
        res_home = self.client.get("/")
        soup_home = BeautifulSoup(res_home.text, 'html.parser')
        radar_sec = soup_home.find(id='radarSection')
        self.assertIsNotNone(radar_sec, "#radarSection should exist in DOM to prevent JS errors")
        self.assertIn('hidden', radar_sec.get('class', []))
        self.assertIn('display: none', radar_sec.get('style', ''))
        
        # Hero CTA to /radar check
        radar_cta = soup_home.find('a', href='/radar')
        self.assertIsNotNone(radar_cta, "Hero button linking to /radar not found on home page")
        
        # Dedicated /radar page check
        res_radar = self.client.get("/radar")
        self.assertEqual(res_radar.status_code, 200)
        soup_radar = BeautifulSoup(res_radar.text, 'html.parser')
        self.assertIn("رادار المنح", soup_radar.find('title').text)

        print(" -> PASSED: [REQ 5] Radar Section Separated & Hidden from Home; /radar fully operational.")

    def test_06_assistant_navigation_and_rendering(self):
        """[REQ 6] Verifies /assistant navigation and that clicking assistant works without redirect bounce."""
        res = self.client.get("/assistant", follow_redirects=False)
        self.assertEqual(res.status_code, 200, "Unauthenticated /assistant must return 200 (guest mode)")
        self.assertIn("المساعد الذكي", res.text)
        
        # Verify navbar on /assistant links cleanly
        soup = BeautifulSoup(res.text, 'html.parser')
        header = soup.find('header')
        self.assertIsNotNone(header)
        assistant_link = header.find('a', href='/assistant')
        self.assertIsNotNone(assistant_link)

        print(" -> PASSED: [REQ 6] AI Assistant Navigation and Guest Rendering Verified (200 OK).")

    def test_07_community_navigation_and_rendering(self):
        """[REQ 7] Verifies /community navigation and that clicking student community renders without errors."""
        res = self.client.get("/community")
        self.assertEqual(res.status_code, 200)
        self.assertIn("مجتمع الطلبة", res.text)
        self.assertIn("sp-sticky-nav", res.text)
        
        soup = BeautifulSoup(res.text, 'html.parser')
        header = soup.find('header')
        comm_link = header.find('a', href='/community')
        self.assertIsNotNone(comm_link)

        print(" -> PASSED: [REQ 7] Student Community Navigation & View Verified (200 OK).")

    def test_08_news_navigation_and_rendering(self):
        """[REQ 8] Verifies /news navigation and that clicking scholarship news renders without errors."""
        res = self.client.get("/news")
        self.assertEqual(res.status_code, 200)
        self.assertIn("أخبار المنح", res.text)
        self.assertIn("sp-sticky-nav", res.text)
        
        soup = BeautifulSoup(res.text, 'html.parser')
        header = soup.find('header')
        news_link = header.find('a', href='/news')
        self.assertIsNotNone(news_link)

        print(" -> PASSED: [REQ 8] Scholarship News Navigation & View Verified (200 OK).")

if __name__ == "__main__":
    unittest.main()
