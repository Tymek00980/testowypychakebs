# -*- coding: utf-8 -*-
"""
Automated test suite for PYCHA KEBS PRO 2.0
"""
import unittest
import os
import sys
import sqlite3

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, CURRENT_DIR)
os.chdir(CURRENT_DIR)

from app import app, init_db, DATABASE

class PychaKebsProTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret'
        cls.client = app.test_client()

    def login(self, username='admin', password='admin123'):
        return self.client.post('/login', data=dict(
            username=username,
            password=password
        ), follow_redirects=True)

    def logout(self):
        return self.client.get('/logout', follow_redirects=True)

    def test_01_public_index_content(self):
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        self.assertIn("Dlaczego właśnie u nas?", html)
        self.assertIn("Od 2022 roku robimy kebaby tak, jak lubimy je sami jeść. ze świeżego mięsa, chrupiących warzyw i własnych sosów.", html)
        self.assertIn("Dwa lokale w Krakowie: Korpala 20 i Wrocławska 31. Na miejscu, na wynos lub z dostawą.", html)
        self.assertIn("Świeże składniki", html)
        self.assertIn("Szybka dostawa", html)
        self.assertIn("Uber · Glovo · Wolt", html)
        self.assertIn("Zamów telefonicznie", html)
        self.assertIn("logo.png", html)

        self.assertNotIn("Na rożnie", html)
        self.assertIn("Korpala 20", html)
        self.assertIn("Wrocławska 31", html)
        self.assertIn("live-pill", html)
        self.assertIn("discreet-gear", html)
        self.assertIn("⚙️", html)

    def test_02_login_and_security(self):
        res = self.client.get('/login')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn("Panel Administratora", html)
        self.assertNotIn("admin123", html)
        self.assertNotIn("Domyślne hasło", html)

        bad_res = self.login('admin', 'wrongpassword')
        self.assertIn("Nieprawidłowy login lub hasło", bad_res.get_data(as_text=True))

        ok_res = self.login('admin', 'admin123')
        self.assertEqual(ok_res.status_code, 200)
        self.assertIn("Panel Administratora", ok_res.get_data(as_text=True))
        self.logout()

    def test_03_admin_panel_tabs(self):
        anon_res = self.client.get('/admin')
        self.assertEqual(anon_res.status_code, 302)

        self.login()
        res = self.client.get('/admin')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        self.assertIn("Panel Administratora", html)
        self.assertNotIn("Panel Admina", html)

        self.assertIn('id="tab-menu"', html)
        self.assertIn('id="tab-ogloszenia"', html)
        self.assertIn('id="tab-tresci"', html)
        self.assertIn('id="tab-lokale"', html)
        self.assertIn('id="tab-godziny"', html)
        self.assertIn('id="tab-dziennik"', html)
        self.logout()

    def test_04_product_quick_actions(self):
        self.login()
        db = sqlite3.connect(DATABASE)
        p = db.execute("SELECT id, price FROM products LIMIT 1").fetchone()
        pid = p[0]
        db.close()

        res = self.client.post(f'/admin/product/{pid}/price', data={'price': 39.50})
        self.assertEqual(res.status_code, 200)
        json_data = res.get_json()
        self.assertTrue(json_data.get('success'))
        self.assertEqual(json_data.get('price'), '39.50')

        toggle_res = self.client.post(f'/admin/product/{pid}/toggle', data={'field': 'is_vegetarian'})
        self.assertEqual(toggle_res.status_code, 200)
        self.assertTrue(toggle_res.get_json().get('success'))

        toggle_spicy = self.client.post(f'/admin/product/{pid}/toggle', data={'field': 'is_spicy'})
        self.assertEqual(toggle_spicy.status_code, 200)
        self.assertTrue(toggle_spicy.get_json().get('success'))
        self.logout()

    def test_05_site_settings_save(self):
        self.login()
        res = self.client.post('/admin/settings/save', data={
            'about_title': 'Dlaczego właśnie u nas?',
            'about_p1': 'Od 2022 roku robimy kebaby tak, jak lubimy je sami jeść. ze świeżego mięsa, chrupiących warzyw i własnych sosów.',
            'about_p2': 'Dwa lokale w Krakowie: Korpala 20 i Wrocławska 31. Na miejscu, na wynos lub z dostawą.',
            'feature1_title': 'Świeże składniki',
            'feature2_title': 'Szybka dostawa',
            'feature2_desc': 'Uber · Glovo · Wolt',
            'feature3_title': 'Zamów telefonicznie'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        home = self.client.get('/')
        h_text = home.get_data(as_text=True)
        self.assertIn("Dlaczego właśnie u nas?", h_text)
        self.assertIn("Uber · Glovo · Wolt", h_text)
        self.logout()

    def test_06_locations_and_hours(self):
        self.login()
        add_res = self.client.post('/admin/location/add', data={
            'name': 'Testowy Lokal 3',
            'address': 'ul. Floriańska 1, Kraków',
            'phone': '111 222 333',
            'rating': 4.9,
            'reviews_count': 50,
            'badge_text': 'Nowy punkt'
        }, follow_redirects=True)
        self.assertEqual(add_res.status_code, 200)

        db = sqlite3.connect(DATABASE)
        loc = db.execute("SELECT id FROM locations WHERE name='Testowy Lokal 3'").fetchone()
        self.assertIsNotNone(loc)
        loc_id = loc[0]

        hours_count = db.execute("SELECT count(*) FROM opening_hours WHERE location_id=?", (loc_id,)).fetchone()[0]
        self.assertEqual(hours_count, 7)
        db.close()

        del_res = self.client.post(f'/admin/location/{loc_id}/delete', follow_redirects=True)
        self.assertEqual(del_res.status_code, 200)

        db2 = sqlite3.connect(DATABASE)
        loc_check = db2.execute("SELECT id FROM locations WHERE id=?", (loc_id,)).fetchone()
        self.assertIsNone(loc_check)
        db2.close()
        self.logout()

    def test_07_activity_logs_and_backup(self):
        self.login()
        backup_res = self.client.get('/admin/backup/download')
        self.assertEqual(backup_res.status_code, 200)
        self.assertTrue(len(backup_res.data) > 1000)
        self.assertIn('attachment', backup_res.headers.get('Content-Disposition', ''))

        db = sqlite3.connect(DATABASE)
        logs = db.execute("SELECT count(*) FROM activity_logs").fetchone()[0]
        self.assertGreater(logs, 0)
        db.close()
        self.logout()

    def test_08_order_methods_crud(self):
        self.login()

        # 1. Add new delivery method
        add_res = self.client.post('/admin/ordermethod/add', data={
            'name': 'Bolt Food Test',
            'description': 'Dostawa ekspresowa',
            'url': 'https://food.bolt.eu/pl-pl/',
            'image_url': 'glovo.png',
            'sort_order': '5'
        }, follow_redirects=True)
        self.assertEqual(add_res.status_code, 200)

        db = sqlite3.connect(DATABASE)
        om = db.execute("SELECT id, name, description, url FROM order_methods WHERE name='Bolt Food Test'").fetchone()
        self.assertIsNotNone(om)
        om_id = om[0]
        db.close()

        # Verify on public page
        home_res = self.client.get('/')
        self.assertIn('Bolt Food Test', home_res.get_data(as_text=True))

        # 2. Edit delivery method
        edit_res = self.client.post(f'/admin/ordermethod/{om_id}/save', data={
            'name': 'Bolt Food Edytowany',
            'description': 'Super szybka dostawa',
            'url': 'https://food.bolt.eu/pl-pl/krakow',
            'image_url': 'uber eats.png',
            'sort_order': '6'
        }, follow_redirects=True)
        self.assertEqual(edit_res.status_code, 200)

        db = sqlite3.connect(DATABASE)
        om_edited = db.execute("SELECT name, description, url FROM order_methods WHERE id=?", (om_id,)).fetchone()
        self.assertEqual(om_edited[0], 'Bolt Food Edytowany')
        self.assertEqual(om_edited[1], 'Super szybka dostawa')
        db.close()

        home_res2 = self.client.get('/')
        self.assertIn('Bolt Food Edytowany', home_res2.get_data(as_text=True))

        # 3. Delete delivery method
        del_res = self.client.post(f'/admin/ordermethod/{om_id}/delete', follow_redirects=True)
        self.assertEqual(del_res.status_code, 200)

        db = sqlite3.connect(DATABASE)
        om_del = db.execute("SELECT id FROM order_methods WHERE id=?", (om_id,)).fetchone()
        self.assertIsNone(om_del)
        db.close()

        home_res3 = self.client.get('/')
        self.assertNotIn('Bolt Food Edytowany', home_res3.get_data(as_text=True))
        self.logout()

if __name__ == '__main__':
    unittest.main(verbosity=2)
