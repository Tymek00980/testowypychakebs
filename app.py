# -*- coding: utf-8 -*-
import os
import sqlite3
import io
from datetime import datetime, time as dtime
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, jsonify, g, send_file, flash
)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'pychakebs-pro-secret-2027-krakow')
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 86400  # 1 day cache for static assets

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'store.db')

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def execute_db(query, args=()):
    db = get_db()
    cur = db.execute(query, args)
    db.commit()
    return cur.lastrowid

def log_activity(action_type, description):
    try:
        execute_db(
            "INSERT INTO activity_logs (action_type, description, created_at) VALUES (?, ?, ?)",
            (action_type, description, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        )
        execute_db(
            "DELETE FROM activity_logs WHERE id NOT IN (SELECT id FROM activity_logs ORDER BY id DESC LIMIT 25)"
        )
    except Exception:
        pass

def get_settings_dict():
    rows = query_db("SELECT key, value FROM site_settings")
    return {r['key']: r['value'] for r in rows}

def get_live_status(location_id):
    now = datetime.now()
    day_of_week = now.isoweekday()  # 1=Poniedzialek .. 7=Niedziela
    hour_row = query_db(
        "SELECT open_time, close_time, is_closed FROM opening_hours WHERE location_id=? AND day_of_week=?",
        (location_id, day_of_week), one=True
    )
    if not hour_row or hour_row['is_closed']:
        return {'is_open': False, 'label': 'Zamknięte dzisiaj'}
    try:
        parts_o = [int(p) for p in hour_row['open_time'].split(':')]
        parts_c = [int(p) for p in hour_row['close_time'].split(':')]
        ot = dtime(parts_o[0], parts_o[1])
        ct = dtime(parts_c[0], parts_c[1])
        current = now.time()
        if ot <= current <= ct:
            return {'is_open': True, 'label': f"Otwarte teraz · do {hour_row['close_time']}"}
        elif current < ot:
            return {'is_open': False, 'label': f"Zamknięte teraz · Otwarte od {hour_row['open_time']}"}
        else:
            return {'is_open': False, 'label': f"Zamknięte · Otwarte jutro"}
    except Exception:
        return {'is_open': False, 'label': 'Godziny w karcie'}

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash('Zaloguj się, aby uzyskać dostęp do panelu.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def init_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    c = db.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        sort_order INTEGER DEFAULT 0
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        price REAL NOT NULL DEFAULT 0,
        image_url TEXT,
        is_available INTEGER DEFAULT 1,
        is_featured INTEGER DEFAULT 0,
        is_new INTEGER DEFAULT 0,
        is_vegetarian INTEGER DEFAULT 0,
        is_spicy INTEGER DEFAULT 0,
        sort_order INTEGER DEFAULT 0,
        FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE CASCADE
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS announcements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        content TEXT NOT NULL,
        badge_text TEXT DEFAULT '🔥 OGŁOSZENIE',
        is_active INTEGER DEFAULT 1,
        created_at TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS site_settings (
        key TEXT PRIMARY KEY,
        value TEXT,
        label TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        address TEXT,
        phone TEXT,
        rating REAL DEFAULT 4.8,
        reviews_count INTEGER DEFAULT 0,
        badge_text TEXT,
        map_embed_url TEXT,
        google_maps_url TEXT,
        sort_order INTEGER DEFAULT 0
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS opening_hours (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        location_id INTEGER,
        day_of_week INTEGER,
        day_name TEXT,
        open_time TEXT,
        close_time TEXT,
        is_closed INTEGER DEFAULT 0,
        FOREIGN KEY (location_id) REFERENCES locations (id) ON DELETE CASCADE
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS activity_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action_type TEXT,
        description TEXT,
        created_at TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS gallery (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        image_url TEXT NOT NULL,
        sort_order INTEGER DEFAULT 0
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS order_methods (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        url TEXT NOT NULL,
        image_url TEXT,
        sort_order INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1
    )""")

    # Seed Admin
    existing_admin = c.execute("SELECT id FROM admins WHERE username='admin'").fetchone()
    if not existing_admin:
        c.execute("INSERT INTO admins (username, password_hash) VALUES (?, ?)",
                  ('admin', generate_password_hash('admin123')))

    # Seed Categories
    cat_count = c.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
    if cat_count == 0:
        categories_data = [
            ('kebaby', 'Kebaby', 1),
            ('zapiekanki', 'Zapiekanki', 2),
            ('przystawki', 'Przystawki', 3),
            ('dodatki', 'Dodatki & Sosy', 4),
            ('napoje', 'Napoje', 5)
        ]
        for slug, name, sort_order in categories_data:
            c.execute("INSERT INTO categories (slug, name, sort_order) VALUES (?, ?, ?)",
                      (slug, name, sort_order))

    # Seed Site Settings
    defaults = [
        ('hero_badge', '🔥 Najlepsze kebaby w Krakowie', 'Hero Badge'),
        ('hero_title_1', 'Najlepszy kebab', 'Hero Tytuł cz. 1'),
        ('hero_title_2', 'Krakowie', 'Hero Tytuł wyróżniony'),
        ('hero_subtitle', 'Przekonaj się sam! Soczyste mięso, autorskie sosy i porcje, które naprawdę sycą.', 'Hero Podtytuł'),
        ('hero_rating', '4.6', 'Hero Ocena'),
        ('hero_reviews', '880+', 'Hero Liczba opinii'),
        ('hero_min_price', 'od 27 zł', 'Hero Cena od'),
        ('about_subtitle', 'O nas', 'O nas Podtytuł'),
        ('about_title', 'Dlaczego właśnie u nas?', 'O nas Tytuł główny'),
        ('about_p1', 'Od 2022 roku robimy kebaby tak, jak lubimy je sami jeść. ze świeżego mięsa, chrupiących warzyw i własnych sosów.', 'O nas Akapit 1'),
        ('about_p2', 'Dwa lokale w Krakowie: Korpala 20 i Wrocławska 31. Na miejscu, na wynos lub z dostawą.', 'O nas Akapit 2'),
        ('feature1_icon', '🥗', 'Cecha 1 Ikona'),
        ('feature1_title', 'Świeże składniki', 'Cecha 1 Tytuł'),
        ('feature1_desc', 'Codziennie świeże warzywa i mięso', 'Cecha 1 Opis'),
        ('feature2_icon', '🚀', 'Cecha 2 Ikona'),
        ('feature2_title', 'Szybka dostawa', 'Cecha 2 Tytuł'),
        ('feature2_desc', 'Uber · Glovo · Wolt', 'Cecha 2 Opis'),
        ('feature3_icon', '📞', 'Cecha 3 Ikona'),
        ('feature3_title', 'Zamów telefonicznie', 'Cecha 3 Tytuł'),
        ('feature3_desc', 'Zadzwoń i odbierz bez czekania', 'Cecha 3 Opis'),
    ]
    for key, val, label in defaults:
        ex = c.execute("SELECT key FROM site_settings WHERE key=?", (key,)).fetchone()
        if not ex:
            c.execute("INSERT INTO site_settings (key, value, label) VALUES (?, ?, ?)", (key, val, label))
        else:
            if key in ('about_title', 'about_p1', 'about_p2', 'feature1_title', 'feature2_title', 'feature2_desc', 'feature3_title'):
                c.execute("UPDATE site_settings SET value=? WHERE key=?", (val, key))

    # Seed Locations
    loc_count = c.execute("SELECT COUNT(*) FROM locations").fetchone()[0]
    if loc_count == 0:
        c.execute("""INSERT INTO locations (id, name, address, phone, rating, reviews_count, badge_text, map_embed_url, google_maps_url, sort_order)
            VALUES (1, 'Korpala 20', 'Michała Korpala 20, 30-389 Kraków', '735 615 619', 4.4, 574, 'Otwarty dzisiaj',
            'https://maps.google.com/maps?q=Micha%C5%82a+Korpala+20,+30-389+Krak%C3%B3w&t=&z=16&ie=UTF8&iwloc=&output=embed',
            'https://www.google.com/maps/search/?api=1&query=Micha%C5%82a+Korpala+20+Krak%C3%B3w', 1)""")
        c.execute("""INSERT INTO locations (id, name, address, phone, rating, reviews_count, badge_text, map_embed_url, google_maps_url, sort_order)
            VALUES (2, 'Wrocławska 31', 'Wrocławska 31, 30-011 Kraków', '793 619 303', 4.8, 306, 'Najwyżej oceniany',
            'https://maps.google.com/maps?q=Wroc%C5%82awska+31,+30-011+Krak%C3%B3w&t=&z=16&ie=UTF8&iwloc=&output=embed',
            'https://www.google.com/maps/search/?api=1&query=Wroc%C5%82awska+31+Krak%C3%B3w', 2)""")

    # Seed Opening Hours
    oh_count = c.execute("SELECT COUNT(*) FROM opening_hours").fetchone()[0]
    if oh_count == 0:
        korpala_hours = [
            (1, 1, 'Poniedziałek', '12:00', '21:00', 1),
            (1, 2, 'Wtorek', '12:00', '21:00', 0),
            (1, 3, 'Środa', '12:00', '21:00', 0),
            (1, 4, 'Czwartek', '12:00', '21:00', 0),
            (1, 5, 'Piątek', '12:00', '22:00', 0),
            (1, 6, 'Sobota', '12:00', '22:00', 0),
            (1, 7, 'Niedziela', '13:00', '21:00', 0),
        ]
        wroclawska_hours = [
            (2, 1, 'Poniedziałek', '12:00', '21:00', 0),
            (2, 2, 'Wtorek', '12:00', '21:00', 0),
            (2, 3, 'Środa', '12:00', '21:00', 0),
            (2, 4, 'Czwartek', '12:00', '21:00', 0),
            (2, 5, 'Piątek', '12:00', '22:00', 0),
            (2, 6, 'Sobota', '13:00', '22:00', 0),
            (2, 7, 'Niedziela', '13:00', '21:00', 0),
        ]
        for row in korpala_hours + wroclawska_hours:
            c.execute("""INSERT INTO opening_hours (location_id, day_of_week, day_name, open_time, close_time, is_closed)
                VALUES (?, ?, ?, ?, ?, ?)""", row)

    # Seed Announcement
    ann_count = c.execute("SELECT COUNT(*) FROM announcements").fetchone()[0]
    if ann_count == 0:
        c.execute("""INSERT INTO announcements (title, content, badge_text, is_active, created_at)
            VALUES ('Witamy w PYCHA KEBS!', 'Zapraszamy na nasz kultowy Kebab Box i autorskie sosy! Dwa lokale otwarte w Krakowie.', '🔥 OGŁOSZENIE', 1, ?)""",
            (datetime.now().strftime('%Y-%m-%d %H:%M'),))

    # Seed Products
    prod_count = c.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    if prod_count == 0:
        cat_map = {r['slug']: r['id'] for r in c.execute("SELECT id, slug FROM categories").fetchall()}
        initial_products = [
            (cat_map['kebaby'], 'Kebab mały', 'Bułka lub tortilla, mięso, chrupiące warzywa i sos', 27.00, 'kebab bułka.png', 1, 0, 0, 0, 0, 1),
            (cat_map['kebaby'], 'Tortilla wegetariańska', 'Ser, frytki, świeże warzywa, autorski sos', 28.00, 'kebab w tortilli.png', 1, 0, 0, 1, 0, 2),
            (cat_map['kebaby'], 'Kebab w bułce', 'Klasyczny, chrupiąca bułka wypiekana na miejscu, świeże warzywa, sos', 30.00, 'kebab w bułce.png', 1, 1, 0, 0, 0, 3),
            (cat_map['kebaby'], 'Kebab w tortilli', 'Zwijany w cienkie, chrupiące ciasto pszenne', 30.00, 'kebab w tortilli.png', 1, 0, 0, 0, 0, 4),
            (cat_map['kebaby'], 'Kebab z frytkami w tortilli', 'Frytki w środku, mięso, warzywa, sos', 33.00, 'kebab z frytkami.png', 1, 0, 0, 0, 0, 5),
            (cat_map['kebaby'], 'Servets', 'Soczyste mięso + porcja złocistych frytek', 33.00, 'kebab z frytkami.png', 1, 0, 0, 0, 0, 6),
            (cat_map['kebaby'], 'Kebab zestaw', 'Mięso, frytki, świeża surówka, sos', 34.00, 'kebab box.png', 1, 0, 0, 0, 0, 7),
            (cat_map['kebaby'], 'Kebab Box', 'Boczek, ziemniaki, podwójne mięso, ciągnący ser', 38.00, 'kebab box.png', 1, 1, 1, 0, 0, 8),
            (cat_map['zapiekanki'], 'Zapiekanka Zwykła', 'Chrupiąca bułka, ser mozzarella, pieczarki, sos', 18.00, 'zapiekanka wiejska.png', 1, 0, 0, 1, 0, 1),
            (cat_map['zapiekanki'], 'Zapiekanka Salami', 'Ser, pieczarki, wyraziste salami', 20.00, 'zapiekanka z salami.png', 1, 1, 0, 0, 0, 2),
            (cat_map['zapiekanki'], 'Zapiekanka Mięso kebab', 'Ser, pieczarki, soczyste mięso kebab', 21.00, 'zapiekanka kebab.png', 1, 0, 0, 0, 0, 3),
            (cat_map['zapiekanki'], 'Zapiekanka Wiejska', 'Ser, pieczarki, kiełbasa wiejska, ogórek kiszony, boczek', 24.00, 'zapiekanka wiejska.png', 1, 0, 0, 0, 0, 4),
            (cat_map['zapiekanki'], 'Kompozycja własna', 'Ser, pieczarki + 3 dowolne składniki do wyboru', 25.00, 'zapiekanka kebab.png', 1, 0, 1, 0, 0, 5),
            (cat_map['przystawki'], 'Frytki', 'Złociste, chrupiące frytki belgijskie', 15.00, 'frytki.png', 1, 0, 0, 1, 0, 1),
            (cat_map['przystawki'], 'Krążki cebulowe', 'Chrupiące panierowane krążki cebulowe', 16.00, 'krążki cebulowe.png', 1, 0, 0, 1, 0, 2),
            (cat_map['przystawki'], 'Nuggetsy', 'Chrupiące kawałki piersi kurczaka z sosem', 19.00, 'nuggetsy.png', 1, 1, 0, 0, 0, 3),
            (cat_map['przystawki'], 'Camembert', 'Panierowany ser camembert z żurawiną', 22.00, 'serki.png', 1, 0, 0, 1, 0, 4),
            (cat_map['przystawki'], 'Stripsy', 'Pikantne paski z polędwiczek kurczaka', 23.00, 'nuggetsy.png', 1, 0, 0, 0, 1, 5),
            (cat_map['przystawki'], 'Jalapeño & Cheese Bites', 'Pikantne papryczki jalapeño z płynnym serem', 23.00, 'serki.png', 1, 0, 0, 1, 1, 6),
            (cat_map['przystawki'], 'Mozzarella Sticks', 'Ciągnące się paluszki serowe w ziołowej panierce', 23.00, 'serki.png', 1, 0, 0, 1, 0, 7),
            (cat_map['dodatki'], 'Dodatkowe mięso', 'Dodatkowa porcja soczystego mięsa do kebaba', 9.00, '', 1, 0, 0, 0, 0, 1),
            (cat_map['dodatki'], 'Ser dodatkowy', 'Dodatkowy ciągnący ser do kebaba lub zapiekanki', 7.00, '', 1, 0, 0, 1, 0, 2),
            (cat_map['dodatki'], 'Jalapeño', 'Pikantne marynowane papryczki jalapeño', 3.00, '', 1, 0, 0, 1, 1, 3),
            (cat_map['dodatki'], 'Ogórek kiszony', 'Tradycyjny polski ogórek kiszony', 3.00, '', 1, 0, 0, 1, 0, 4),
            (cat_map['dodatki'], 'Cebulka prażona', 'Chrupiąca prażona złocista cebulka', 2.00, '', 1, 0, 0, 1, 0, 5),
            (cat_map['dodatki'], 'Autorski sos (dodatkowy)', 'Do wyboru: Łagodny / Średni / Czosnek / Ostry', 4.00, '', 1, 0, 0, 1, 0, 6),
            (cat_map['dodatki'], 'Sosy specjalne', 'Serowy, ostry sriracha, serowy chilli, 1000 wysp, ketchup', 4.00, '', 1, 0, 0, 1, 1, 7),
            (cat_map['napoje'], 'Woda 0,5l', 'Gazowana lub niegazowana', 6.00, '', 1, 0, 0, 1, 0, 1),
            (cat_map['napoje'], 'Sok 0,33l', 'Pomarańczowy / jabłkowy Cappy', 7.00, '', 1, 0, 0, 1, 0, 2),
            (cat_map['napoje'], 'Puszka 0,33l', 'Coca-Cola, Coca-Cola Zero, Fanta, Sprite', 7.00, '', 1, 0, 0, 1, 0, 3),
            (cat_map['napoje'], 'Puszka 0,5l', 'Coca-Cola, Pepsi, Monster Energy', 9.00, '', 1, 0, 0, 1, 0, 4),
            (cat_map['napoje'], 'Butelka 0,85l', 'Coca-Cola, Coca-Cola Zero', 11.00, '', 1, 0, 0, 1, 0, 5),
            (cat_map['napoje'], 'Sok 1l', 'Pomarańczowy / jabłkowy', 12.00, '', 1, 0, 0, 1, 0, 6),
        ]
        c.executemany("""INSERT INTO products 
            (category_id, name, description, price, image_url, is_available, is_featured, is_new, is_vegetarian, is_spicy, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", initial_products)

    # Seed Gallery
    gal_count = c.execute("SELECT COUNT(*) FROM gallery").fetchone()[0]
    if gal_count == 0:
        initial_gallery = [
            ('kebab w bułce.png', 1), ('kebab z frytkami.png', 2),
            ('kebab box.png', 3), ('kebab w tortilli.png', 4),
            ('kebab bułka.png', 5), ('zapiekanka z salami.png', 6),
            ('zapiekanka wiejska.png', 7), ('zapiekanka kebab.png', 8),
            ('frytki.png', 9), ('krążki cebulowe.png', 10),
            ('nuggetsy.png', 11), ('serki.png', 12)
        ]
        c.executemany("INSERT INTO gallery (image_url, sort_order) VALUES (?, ?)", initial_gallery)

    # Seed Order Methods
    om_count = c.execute("SELECT COUNT(*) FROM order_methods").fetchone()[0]
    if om_count == 0:
        initial_om = [
            ('Uber Eats', 'Szybka dostawa', 'https://www.ubereats.com/pl/store/pycha-kebs/F_G-w2RTTu25I73nC5Wt1w', 'uber eats.png', 1, 1),
            ('Glovo', 'Dostawa', 'https://glovoapp.com/pl/pl/krakow/stores/pycha-kebs-kra-1', 'glovo.png', 2, 1),
            ('Wolt', 'Kebab i więcej', 'https://wolt.com/pl/pol/krakow/restaurant/pycha-kebs', 'wolt.png', 3, 1),
            ('Pyszne.pl', 'Dostawa / odbiór', 'https://www.pyszne.pl/menu/pycha-kebs-krakow-1', 'pyszne.pl.png', 4, 1)
        ]
        c.executemany("INSERT INTO order_methods (name, description, url, image_url, sort_order, is_active) VALUES (?, ?, ?, ?, ?, ?)", initial_om)

    db.commit()
    db.close()

# Inicjalizacja bazy danych przy starcie aplikacji (np. Gunicorn)
init_db()

# -------------------------------------------------------------
# PUBLIC ROUTES
# -------------------------------------------------------------

@app.route('/')
def index():
    categories = query_db("SELECT * FROM categories ORDER BY sort_order, name")
    products = query_db("""
        SELECT p.*, c.slug as category_slug, c.name as category_name 
        FROM products p 
        JOIN categories c ON p.category_id = c.id 
        WHERE p.is_available = 1 
        ORDER BY p.sort_order, p.name
    """)
    announcement = query_db("SELECT * FROM announcements WHERE is_active = 1 ORDER BY id DESC LIMIT 1", one=True)
    settings = get_settings_dict()
    locations = query_db("SELECT * FROM locations ORDER BY sort_order, id")
    
    gallery_items = query_db("SELECT * FROM gallery ORDER BY sort_order, id")
    order_methods = query_db("SELECT * FROM order_methods WHERE is_active = 1 ORDER BY sort_order, id")

    loc_data = []
    for loc in locations:
        status = get_live_status(loc['id'])
        hours = query_db("SELECT * FROM opening_hours WHERE location_id = ? ORDER BY day_of_week", (loc['id'],))
        loc_data.append({'loc': loc, 'status': status, 'hours': hours})

    products_by_category = {}
    for p in products:
        slug = p['category_slug']
        if slug not in products_by_category:
            products_by_category[slug] = []
        products_by_category[slug].append(p)

    return render_template('index.html',
                           categories=categories,
                           products=products,
                           products_by_category=products_by_category,
                           announcement=announcement,
                           settings=settings,
                           loc_data=loc_data,
                           gallery=gallery_items,
                           order_methods=order_methods)

# -------------------------------------------------------------
# AUTH
# -------------------------------------------------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin'))
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        admin_row = query_db("SELECT * FROM admins WHERE username = ?", (username,), one=True)
        if admin_row:
            stored_hash = admin_row['password_hash']
            is_valid = False
            if stored_hash.startswith('scrypt:') or stored_hash.startswith('pbkdf2:'):
                is_valid = check_password_hash(stored_hash, password)
            else:
                is_valid = (stored_hash == password)

            if is_valid:
                session['admin_logged_in'] = True
                session['admin_user'] = username
                log_activity('login', f'Zalogowano administratora: {username}')
                flash('Pomyślnie zalogowano do Panelu Administratora.', 'success')
                return redirect(url_for('admin'))
        error = 'Nieprawidłowy login lub hasło.'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    user = session.get('admin_user', 'admin')
    log_activity('logout', f'Wylogowano administratora: {user}')
    session.clear()
    flash('Zostałeś wylogowany.', 'info')
    return redirect(url_for('index'))

# -------------------------------------------------------------
# ADMIN DASHBOARD & CMS
# -------------------------------------------------------------

@app.route('/admin')
@login_required
def admin():
    categories = query_db("SELECT * FROM categories ORDER BY sort_order, name")
    products = query_db("""
        SELECT p.*, c.name as category_name, c.slug as category_slug 
        FROM products p 
        LEFT JOIN categories c ON p.category_id = c.id 
        ORDER BY p.sort_order, p.name
    """)
    announcements = query_db("SELECT * FROM announcements ORDER BY id DESC")
    settings = get_settings_dict()
    locations = query_db("SELECT * FROM locations ORDER BY sort_order, id")
    hours_all = query_db("SELECT * FROM opening_hours ORDER BY location_id, day_of_week")
    logs = query_db("SELECT * FROM activity_logs ORDER BY id DESC LIMIT 25")

    img_dir = os.path.join(os.path.dirname(__file__), 'static', 'images')
    available_images = []
    if os.path.exists(img_dir):
        available_images = sorted([f for f in os.listdir(img_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))])

    total_prod = len(products)
    active_prod = sum(1 for p in products if p['is_available'])
    hidden_prod = total_prod - active_prod
    featured_prod = sum(1 for p in products if p['is_featured'])
    new_prod = sum(1 for p in products if p['is_new'])
    stats = {
        'total': total_prod,
        'active': active_prod,
        'hidden': hidden_prod,
        'featured': featured_prod,
        'new': new_prod,
        'locations': len(locations)
    }

    gallery_items = query_db("SELECT * FROM gallery ORDER BY sort_order, id")
    order_methods = query_db("SELECT * FROM order_methods ORDER BY sort_order, id")

    return render_template('admin.html',
                           categories=categories,
                           products=products,
                           announcements=announcements,
                           settings=settings,
                           locations=locations,
                           hours_all=hours_all,
                           logs=logs,
                           available_images=available_images,
                           stats=stats,
                           gallery=gallery_items,
                           order_methods=order_methods)

# ── Products ──

@app.route('/admin/product/add', methods=['POST'])
@login_required
def add_product():
    name = request.form.get('name', '').strip()
    category_id = request.form.get('category_id')
    description = request.form.get('description', '').strip()
    price = float(request.form.get('price', 0))
    image_url = request.form.get('image_url', '').strip()
    sort_order = int(request.form.get('sort_order', 10))
    is_vegetarian = 1 if request.form.get('is_vegetarian') else 0
    is_spicy = 1 if request.form.get('is_spicy') else 0
    is_featured = 1 if request.form.get('is_featured') else 0
    is_new = 1 if request.form.get('is_new') else 0

    if name and category_id:
        execute_db("""INSERT INTO products 
            (category_id, name, description, price, image_url, is_available, is_featured, is_new, is_vegetarian, is_spicy, sort_order)
            VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?)""",
            (category_id, name, description, price, image_url, is_featured, is_new, is_vegetarian, is_spicy, sort_order))
        log_activity('product_add', f'Dodano nowy produkt: {name} ({price:.2f} zł)')
        flash(f'Produkt "{name}" został dodany.', 'success')
    return redirect(url_for('admin') + '#tab-menu')

@app.route('/admin/product/<int:pid>/edit', methods=['POST'])
@login_required
def edit_product(pid):
    name = request.form.get('name', '').strip()
    category_id = request.form.get('category_id')
    description = request.form.get('description', '').strip()
    price = float(request.form.get('price', 0))
    image_url = request.form.get('image_url', '').strip()
    sort_order = int(request.form.get('sort_order', 0))
    is_vegetarian = 1 if request.form.get('is_vegetarian') else 0
    is_spicy = 1 if request.form.get('is_spicy') else 0
    is_featured = 1 if request.form.get('is_featured') else 0
    is_new = 1 if request.form.get('is_new') else 0

    execute_db("""UPDATE products SET 
        name=?, category_id=?, description=?, price=?, image_url=?, sort_order=?, 
        is_vegetarian=?, is_spicy=?, is_featured=?, is_new=? 
        WHERE id=?""",
        (name, category_id, description, price, image_url, sort_order, is_vegetarian, is_spicy, is_featured, is_new, pid))
    log_activity('product_edit', f'Zaktualizowano produkt ID {pid}: {name}')
    flash(f'Produkt "{name}" został zaktualizowany.', 'success')
    return redirect(url_for('admin') + '#tab-menu')

@app.route('/admin/product/<int:pid>/delete', methods=['POST'])
@login_required
def delete_product(pid):
    row = query_db("SELECT name FROM products WHERE id=?", (pid,), one=True)
    name = row['name'] if row else f'ID {pid}'
    execute_db("DELETE FROM products WHERE id=?", (pid,))
    log_activity('product_delete', f'Usunięto produkt: {name}')
    flash(f'Produkt "{name}" został usunięty.', 'info')
    return redirect(url_for('admin') + '#tab-menu')

@app.route('/admin/product/<int:pid>/toggle', methods=['POST'])
@login_required
def toggle_product(pid):
    field = request.form.get('field', 'is_available')
    allowed = {'is_available', 'is_featured', 'is_new', 'is_vegetarian', 'is_spicy'}
    if field not in allowed:
        return jsonify({'error': 'Niedozwolone pole'}), 400
    row = query_db(f"SELECT {field}, name FROM products WHERE id=?", (pid,), one=True)
    if row:
        new_val = 0 if row[field] else 1
        execute_db(f"UPDATE products SET {field}=? WHERE id=?", (new_val, pid))
        log_activity('product_toggle', f'Zmieniono {field} dla "{row["name"]}" na {new_val}')
        return jsonify({'success': True, 'field': field, 'value': new_val})
    return jsonify({'error': 'Nie znaleziono produktu'}), 404

@app.route('/admin/product/<int:pid>/price', methods=['POST'])
@login_required
def update_price(pid):
    try:
        price = float(request.form.get('price', 0))
        row = query_db("SELECT name FROM products WHERE id=?", (pid,), one=True)
        execute_db("UPDATE products SET price=? WHERE id=?", (price, pid))
        prod_name = row['name'] if row else f'ID {pid}'
        log_activity('price_update', f'Zmieniono cenę "{prod_name}" na {price:.2f} zł')
        return jsonify({'success': True, 'price': f"{price:.2f}"})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ── Announcements ──

@app.route('/admin/announcement/save', methods=['POST'])
@login_required
def save_announcement():
    aid = request.form.get('id')
    content = request.form.get('content', '').strip()
    badge_text = request.form.get('badge_text', '🔥 OGŁOSZENIE').strip()
    is_active = 1 if request.form.get('is_active') else 0
    if aid:
        execute_db("UPDATE announcements SET content=?, badge_text=?, is_active=? WHERE id=?",
                   (content, badge_text, is_active, aid))
        log_activity('announcement_edit', f'Zaktualizowano ogłoszenie ID {aid}')
    else:
        if content:
            execute_db("INSERT INTO announcements (content, badge_text, is_active, created_at) VALUES (?, ?, ?, ?)",
                       (content, badge_text, is_active, datetime.now().strftime('%Y-%m-%d %H:%M')))
            log_activity('announcement_add', f'Dodano ogłoszenie: {content[:30]}...')
    flash('Ogłoszenie zostało zapisane.', 'success')
    return redirect(url_for('admin') + '#tab-ogloszenia')

@app.route('/admin/announcement/<int:aid>/delete', methods=['POST'])
@login_required
def delete_announcement(aid):
    execute_db("DELETE FROM announcements WHERE id=?", (aid,))
    log_activity('announcement_delete', f'Usunięto ogłoszenie ID {aid}')
    flash('Ogłoszenie zostało usunięte.', 'info')
    return redirect(url_for('admin') + '#tab-ogloszenia')

# ── Site settings ──

@app.route('/admin/settings/save', methods=['POST'])
@login_required
def save_settings():
    for key, val in request.form.items():
        if key not in ('csrf_token',):
            execute_db("INSERT INTO site_settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                       (key, val))
    log_activity('settings_save', 'Zaktualizowano treści strony głównej')
    flash('Treści strony zostały pomyślnie zaktualizowane.', 'success')
    return redirect(url_for('admin') + '#tab-tresci')

# ── Locations ──

@app.route('/admin/location/add', methods=['POST'])
@login_required
def add_location():
    name = request.form.get('name', '').strip()
    address = request.form.get('address', '').strip()
    phone = request.form.get('phone', '').strip()
    rating = float(request.form.get('rating', 4.8))
    reviews_count = int(request.form.get('reviews_count', 0))
    badge_text = request.form.get('badge_text', '').strip()
    map_embed_url = request.form.get('map_embed_url', '').strip()
    google_maps_url = request.form.get('google_maps_url', '').strip()

    if name:
        loc_id = execute_db("""INSERT INTO locations 
            (name, address, phone, rating, reviews_count, badge_text, map_embed_url, google_maps_url, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 10)""",
            (name, address, phone, rating, reviews_count, badge_text, map_embed_url, google_maps_url))

        days = [(1, 'Poniedziałek'), (2, 'Wtorek'), (3, 'Środa'), (4, 'Czwartek'),
                (5, 'Piątek'), (6, 'Sobota'), (7, 'Niedziela')]
        for dnum, dname in days:
            execute_db("""INSERT INTO opening_hours (location_id, day_of_week, day_name, open_time, close_time, is_closed)
                VALUES (?, ?, ?, '12:00', '21:00', 0)""", (loc_id, dnum, dname))

        log_activity('location_add', f'Dodano nowy lokal: {name}')
        flash(f'Lokal "{name}" został pomyślnie dodany wraz z harmonogramem.', 'success')
    return redirect(url_for('admin') + '#tab-lokale')

@app.route('/admin/location/<int:lid>/save', methods=['POST'])
@login_required
def save_location(lid):
    name = request.form.get('name', '').strip()
    address = request.form.get('address', '').strip()
    phone = request.form.get('phone', '').strip()
    rating = float(request.form.get('rating', 4.8))
    reviews_count = int(request.form.get('reviews_count', 0))
    badge_text = request.form.get('badge_text', '').strip()
    map_embed_url = request.form.get('map_embed_url', '').strip()
    google_maps_url = request.form.get('google_maps_url', '').strip()

    execute_db("""UPDATE locations SET 
        name=?, address=?, phone=?, rating=?, reviews_count=?, badge_text=?, 
        map_embed_url=?, google_maps_url=? 
        WHERE id=?""",
        (name, address, phone, rating, reviews_count, badge_text, map_embed_url, google_maps_url, lid))
    log_activity('location_edit', f'Zaktualizowano dane lokalu: {name}')
    flash(f'Dane lokalu "{name}" zostały zaktualizowane.', 'success')
    return redirect(url_for('admin') + '#tab-lokale')

@app.route('/admin/location/<int:lid>/delete', methods=['POST'])
@login_required
def delete_location(lid):
    row = query_db("SELECT name FROM locations WHERE id=?", (lid,), one=True)
    name = row['name'] if row else f'ID {lid}'
    execute_db("DELETE FROM opening_hours WHERE location_id=?", (lid,))
    execute_db("DELETE FROM locations WHERE id=?", (lid,))
    log_activity('location_delete', f'Usunięto lokal: {name}')
    flash(f'Lokal "{name}" został usunięty.', 'info')
    return redirect(url_for('admin') + '#tab-lokale')

# ── Opening Hours ──

@app.route('/admin/hours/save', methods=['POST'])
@login_required
def save_hours():
    location_id = request.form.get('location_id')
    loc = query_db("SELECT name FROM locations WHERE id=?", (location_id,), one=True)
    loc_name = loc['name'] if loc else f'ID {location_id}'

    for key, val in request.form.items():
        if key.startswith('open_'):
            day = key.replace('open_', '')
            close_time = request.form.get(f'close_{day}', '')
            is_closed = 1 if request.form.get(f'closed_{day}') else 0
            execute_db("""UPDATE opening_hours SET open_time=?, close_time=?, is_closed=? 
                WHERE location_id=? AND day_of_week=?""",
                (val, close_time, is_closed, location_id, day))

    log_activity('hours_save', f'Zaktualizowano godziny otwarcia dla: {loc_name}')
    flash(f'Godziny otwarcia dla lokalu "{loc_name}" zostały zapisane.', 'success')
    return redirect(url_for('admin') + '#tab-godziny')

# ── Change Password ──

@app.route('/admin/change-password', methods=['POST'])
@login_required
def change_password():
    current_pass = request.form.get('current_password', '')
    new_pass = request.form.get('new_password', '')
    username = session.get('admin_user', 'admin')

    admin_row = query_db("SELECT * FROM admins WHERE username=?", (username,), one=True)
    if admin_row:
        stored = admin_row['password_hash']
        is_valid = check_password_hash(stored, current_pass) if (stored.startswith('scrypt:') or stored.startswith('pbkdf2:')) else (stored == current_pass)
        if is_valid and len(new_pass) >= 4:
            new_hash = generate_password_hash(new_pass)
            execute_db("UPDATE admins SET password_hash=? WHERE username=?", (new_hash, username))
            log_activity('password_change', f'Zmieniono hasło administratora: {username}')
            flash('Hasło zostało pomyślnie zmienione.', 'success')
        else:
            flash('Błędne aktualne hasło lub nowe hasło jest za krótkie (min. 4 znaki).', 'error')
    return redirect(url_for('admin') + '#tab-tresci')

# ── Download Backup ──

@app.route('/admin/backup/download')
@login_required
def download_backup():
    if not os.path.exists(DATABASE):
        flash('Brak pliku bazy danych.', 'error')
        return redirect(url_for('admin'))
    with open(DATABASE, 'rb') as f:
        data = f.read()
    buf = io.BytesIO(data)
    buf.seek(0)
    filename = f"pychakebs_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    log_activity('backup', 'Pobrano kopię zapasową bazy danych store.db')
    return send_file(buf, as_attachment=True, download_name=filename, mimetype='application/x-sqlite3')

# ── Gallery ──

@app.route('/admin/gallery/add', methods=['POST'])
@login_required
def add_gallery():
    image_url = request.form.get('image_url', '').strip()
    sort_order = int(request.form.get('sort_order', 10))
    if image_url:
        execute_db("INSERT INTO gallery (image_url, sort_order) VALUES (?, ?)", (image_url, sort_order))
        log_activity('gallery_add', f'Dodano zdjęcie do galerii: {image_url}')
        flash('Zdjęcie dodane do galerii.', 'success')
    return redirect(url_for('admin') + '#tab-galeria')

@app.route('/admin/gallery/<int:gid>/delete', methods=['POST'])
@login_required
def delete_gallery(gid):
    execute_db("DELETE FROM gallery WHERE id=?", (gid,))
    log_activity('gallery_delete', f'Usunięto zdjęcie ID {gid}')
    flash('Zdjęcie usunięte z galerii.', 'info')
    return redirect(url_for('admin') + '#tab-galeria')

# ── Order Methods ──

@app.route('/admin/ordermethod/add', methods=['POST'])
@login_required
def add_order_method():
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    url_link = request.form.get('url', '').strip()
    image_url = request.form.get('image_url', '').strip()
    try:
        sort_order = int(request.form.get('sort_order', 10) or 10)
    except (ValueError, TypeError):
        sort_order = 10
    if name and url_link:
        execute_db("INSERT INTO order_methods (name, description, url, image_url, sort_order) VALUES (?, ?, ?, ?, ?)",
                   (name, description, url_link, image_url, sort_order))
        log_activity('order_method_add', f'Dodano formę zamówienia: {name}')
        flash('Forma zamówienia dodana.', 'success')
    return redirect(url_for('admin') + '#tab-zamowienia')

@app.route('/admin/ordermethod/<int:oid>/save', methods=['POST'])
@login_required
def save_order_method(oid):
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    url_link = request.form.get('url', '').strip()
    image_url = request.form.get('image_url', '').strip()
    try:
        sort_order = int(request.form.get('sort_order', 10) or 10)
    except (ValueError, TypeError):
        sort_order = 10
    execute_db("UPDATE order_methods SET name=?, description=?, url=?, image_url=?, sort_order=? WHERE id=?",
               (name, description, url_link, image_url, sort_order, oid))
    log_activity('order_method_edit', f'Zaktualizowano formę zamówienia: {name}')
    flash('Forma zamówienia zapisana.', 'success')
    return redirect(url_for('admin') + '#tab-zamowienia')

@app.route('/admin/ordermethod/<int:oid>/delete', methods=['POST'])
@login_required
def delete_order_method(oid):
    execute_db("DELETE FROM order_methods WHERE id=?", (oid,))
    log_activity('order_method_delete', f'Usunięto formę zamówienia ID {oid}')
    flash('Forma zamówienia usunięta.', 'info')
    return redirect(url_for('admin') + '#tab-zamowienia')

# -------------------------------------------------------------
# RUN
# -------------------------------------------------------------

if __name__ == '__main__':
    print("\n" + "="*60)
    print("  🌯  PYCHA KEBS PRO 2.0  –  Panel Administratora")
    print("="*60)
    print("  Strona klienta:  http://127.0.0.1:5000")
    print("  Logowanie:       http://127.0.0.1:5000/login")
    print("  Panel:           http://127.0.0.1:5000/admin")
    print("  Domyślny login:  admin  |  Hasło: admin123")
    print("="*60 + "\n")
    app.run(debug=True, host='127.0.0.1', port=5000)
