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

    def test_09_about_image_and_size_settings(self):
        self.login()
        # Save custom about image and size
        res = self.client.post('/admin/settings/save', data={
            'about_image': 'kebab box.png',
            'about_image_size': '250px',
            'about_badge_text': '🌯 Testowy Tekst Odznaki',
            'about_box_max_width': '400px'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Verify on public homepage
        home_res = self.client.get('/')
        html = home_res.get_data(as_text=True)
        self.assertTrue('kebab%20box.png' in html or 'kebab box.png' in html)
        self.assertIn('250px', html)
        self.assertIn('Testowy Tekst Odznaki', html)
        self.assertIn('400px', html)

        # Restore default logo.png
        self.client.post('/admin/settings/save', data={
            'about_image': 'logo.png',
            'about_image_size': '200px',
            'about_badge_text': '🌯 Najlepszy smak od 2022',
            'about_box_max_width': '370px'
        }, follow_redirects=True)
        self.logout()

    def test_10_about_box_toggle_and_alignment(self):
        import io
        self.login()

        # 1. Test disabling the box (about_show_box=0) and center alignment
        res = self.client.post('/admin/settings/save', data={
            'about_show_box': '0',
            'about_align': 'center'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        html = self.client.get('/').get_data(as_text=True)
        self.assertIn('no-image', html)
        self.assertIn('about-align-center', html)
        self.assertNotIn('about-image-wrapper', html)

        # 2. Test right alignment
        self.client.post('/admin/settings/save', data={
            'about_show_box': '1',
            'about_align': 'right'
        }, follow_redirects=True)
        html2 = self.client.get('/').get_data(as_text=True)
        self.assertIn('about-align-right', html2)
        self.assertIn('about-image-wrapper', html2)

        # 3. Test real file upload to about_image
        test_file = (io.BytesIO(b"fake image content"), "nowe_logo_test.png")
        self.client.post('/admin/settings/save', data={
            'about_image_file': test_file,
            'about_image': 'logo.png',  # should NOT overwrite uploaded file
            'about_show_box': '1',
            'about_align': 'left'
        }, content_type='multipart/form-data', follow_redirects=True)

        html3 = self.client.get('/').get_data(as_text=True)
        self.assertIn('nowe_logo_test.png', html3)
        self.assertIn('about-align-left', html3)

        # Cleanup uploaded test file
        test_path = os.path.join(CURRENT_DIR, 'static', 'images', 'nowe_logo_test.png')
        if os.path.exists(test_path):
            os.remove(test_path)

        # Restore default settings
        self.client.post('/admin/settings/save', data={
            'about_image': 'logo.png',
            'about_image_size': '200px',
            'about_show_box': '1',
            'about_align': 'left',
            'about_badge_text': '🌯 Najlepszy smak od 2022',
            'about_box_max_width': '370px'
        }, follow_redirects=True)
        self.logout()

    def test_11_mobile_menu_fix(self):
        # Verify index.html does not have duplicate inline onclick on hamburger or overlay
        with open(os.path.join(CURRENT_DIR, 'templates', 'index.html'), 'r', encoding='utf-8') as f:
            html_src = f.read()
        self.assertNotIn('id="hamburger" aria-label="Menu nawigacyjne" onclick=', html_src)
        self.assertNotIn('id="navOverlay" onclick=', html_src)
        self.assertIn('class="hamburger" id="hamburger"', html_src)
        self.assertIn('class="nav-overlay" id="navOverlay"', html_src)

        # Verify script.js implements toggleMobileMenu and event listeners
        with open(os.path.join(CURRENT_DIR, 'static', 'js', 'script.js'), 'r', encoding='utf-8') as f:
            js_src = f.read()
        self.assertIn('window.toggleMobileMenu = function', js_src)
        self.assertIn("hamburger.addEventListener('click'", js_src)
        self.assertIn("navOverlay.addEventListener('click'", js_src)
        self.assertIn("menu-locked", js_src)

    def test_12_seasonal_offer_management_and_toggle(self):
        self.login()

        # 1. Verify admin has tab-sezonowa
        res_admin = self.client.get('/admin')
        self.assertEqual(res_admin.status_code, 200)
        admin_html = res_admin.get_data(as_text=True)
        self.assertIn('id="tab-sezonowa"', admin_html)
        self.assertIn('href="#tab-sezonowa"', admin_html)
        self.assertIn('Oferta Sezonowa', admin_html)

        # 2. Get seasonal category id
        db = sqlite3.connect(DATABASE)
        sez_row = db.execute("SELECT id FROM categories WHERE slug='sezonowa'").fetchone()
        self.assertIsNotNone(sez_row)
        sez_id = sez_row[0]
        db.close()

        # 3. Add a new seasonal product
        add_res = self.client.post('/admin/product/add', data={
            'name': 'Kebab Jesienny Drwala Test',
            'category_id': sez_id,
            'description': 'Soczyste mięso, sos żurawinowy, bekon i cheddar',
            'price': 36.50,
            'image_url': 'kebab box.png',
            'sort_order': 1,
            'is_vegetarian': 0,
            'is_spicy': 1,
            'is_featured': 1,
            'is_new': 1,
            'return_tab': 'tab-sezonowa'
        }, follow_redirects=True)
        self.assertEqual(add_res.status_code, 200)

        # 4. Activate seasonal offer via settings
        set_res = self.client.post('/admin/seasonal/settings', data={
            'seasonal_title': 'Oferta Zimowa Test',
            'seasonal_subtitle': 'Gorące nowości w mroźne dni!',
            'seasonal_badge': '❄️ ZIMOWY HIT',
            'seasonal_active': '1'
        }, follow_redirects=True)
        self.assertEqual(set_res.status_code, 200)

        # 5. Check public page when active
        home_active = self.client.get('/')
        h_act_text = home_active.get_data(as_text=True)
        self.assertIn('Oferta Zimowa Test', h_act_text)
        self.assertIn('❄️ ZIMOWY HIT', h_act_text)
        self.assertIn('Gorące nowości w mroźne dni!', h_act_text)
        self.assertIn('Kebab Jesienny Drwala Test', h_act_text)
        self.assertIn('menu-tab-seasonal', h_act_text)

        # 6. Toggle seasonal offer to inactive via toggle route
        tog_res = self.client.post('/admin/seasonal/toggle', data={'return_tab': 'tab-sezonowa'}, follow_redirects=True)
        self.assertEqual(tog_res.status_code, 200)

        # 7. Check public page when inactive -> should be hidden!
        home_inactive = self.client.get('/')
        h_inact_text = home_inactive.get_data(as_text=True)
        self.assertNotIn('menu-tab-seasonal', h_inact_text)
        self.assertNotIn('data-tab="sezonowa"', h_inact_text)
        self.assertNotIn('Kebab Jesienny Drwala Test', h_inact_text)

        # 8. Test AJAX toggle back to active
        ajax_res = self.client.post('/admin/seasonal/toggle', headers={'X-Requested-With': 'XMLHttpRequest'})
        self.assertEqual(ajax_res.status_code, 200)
        self.assertTrue(ajax_res.get_json().get('active'))

        # 9. Clean up added test product
        db = sqlite3.connect(DATABASE)
        p_row = db.execute("SELECT id FROM products WHERE name='Kebab Jesienny Drwala Test'").fetchone()
        if p_row:
            db.execute("DELETE FROM products WHERE id=?", (p_row[0],))
            db.commit()
        db.close()

        # Restore default seasonal settings
        self.client.post('/admin/seasonal/settings', data={
            'seasonal_title': 'Oferta Sezonowa',
            'seasonal_subtitle': 'Wyjątkowe specjały dostępne tylko przez ograniczony czas!',
            'seasonal_badge': '🍁 EDYCJA SEZONOWA',
            'seasonal_active': '1'
        }, follow_redirects=True)
        self.logout()

    def test_13_category_sort_order_and_reorder(self):
        """Test that sezonowa is last in sort_order and reorder route works."""
        # 1. Verify sezonowa sort_order >= all others in DB
        db = sqlite3.connect(DATABASE)
        rows = db.execute("SELECT slug, sort_order FROM categories ORDER BY sort_order").fetchall()
        db.close()
        slugs_in_order = [r[0] for r in rows]
        self.assertEqual(slugs_in_order[-1], 'sezonowa',
                         f"Oczekiwano 'sezonowa' na końcu, jest: {slugs_in_order}")

        # 2. Admin panel should show the reorder form card
        self.login()
        res = self.client.get('/admin')
        html = res.get_data(as_text=True)
        self.assertIn('Kolejność kategorii w menu', html)
        self.assertIn('cat-reorder-input', html)
        self.assertIn('/admin/categories/reorder', html)

        # 3. POST to reorder — set napoje=3, kebaby=10
        db2 = sqlite3.connect(DATABASE)
        cat_rows = db2.execute("SELECT id, slug FROM categories").fetchall()
        db2.close()
        form_data = {}
        for cid, slug in cat_rows:
            if slug == 'napoje':
                form_data[f'sort_order_{cid}'] = '3'
            elif slug == 'kebaby':
                form_data[f'sort_order_{cid}'] = '10'
            else:
                # leave others unchanged — still supply field
                orig = next(r[1] for r in rows if r[0] == slug)
                form_data[f'sort_order_{cid}'] = str(orig)
        res2 = self.client.post('/admin/categories/reorder', data=form_data, follow_redirects=True)
        self.assertEqual(res2.status_code, 200)

        # Verify DB updated
        db3 = sqlite3.connect(DATABASE)
        for cid, slug in cat_rows:
            if slug == 'napoje':
                val = db3.execute("SELECT sort_order FROM categories WHERE id=?", (cid,)).fetchone()[0]
                self.assertEqual(val, 3)
            elif slug == 'kebaby':
                val = db3.execute("SELECT sort_order FROM categories WHERE id=?", (cid,)).fetchone()[0]
                self.assertEqual(val, 10)
        db3.close()

        # 4. Restore original order
        restore_data = {}
        original = {'kebaby': 1, 'zapiekanki': 2, 'przystawki': 3, 'dodatki': 4, 'napoje': 5, 'sezonowa': 99}
        for cid, slug in cat_rows:
            restore_data[f'sort_order_{cid}'] = str(original.get(slug, 10))
        self.client.post('/admin/categories/reorder', data=restore_data, follow_redirects=True)
        self.logout()

if __name__ == '__main__':
    unittest.main(verbosity=2)
