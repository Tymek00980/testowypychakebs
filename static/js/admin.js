// PYCHA KEBS PRO – Admin Panel JavaScript
document.addEventListener('DOMContentLoaded', () => {

    // 1. Tab Navigation
    const sidebarLinks = document.querySelectorAll('.sidebar-link[data-tab]');
    const tabPanels = document.querySelectorAll('.tab-panel');
    const pageTitle = document.getElementById('pageTitle');

    const tabTitles = {
        'tab-menu': '🍽️ Menu i Cennik',
        'tab-ogloszenia': '📢 Ogłoszenia na stronie',
        'tab-tresci': '✏️ Treści strony & Hasło',
        'tab-lokale': '📍 Lokale – Znajdź nas w Krakowie',
        'tab-godziny': '🕐 Godziny otwarcia lokali',
        'tab-dziennik': '📋 Dziennik zdarzeń',
        'tab-galeria': '🖼️ Galeria zdjęć',
        'tab-zamowienia': '🛵 Sposoby zamówień (Dostawcy)'
    };

    function activateTab(tabId) {
        tabPanels.forEach(panel => {
            panel.classList.toggle('active', panel.id === tabId);
        });
        sidebarLinks.forEach(link => {
            link.classList.toggle('active', link.getAttribute('data-tab') === tabId);
        });
        if (pageTitle && tabTitles[tabId]) {
            pageTitle.textContent = tabTitles[tabId];
        }
        // Save to hash
        history.replaceState(null, '', '#' + tabId);
    }

    sidebarLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetTab = link.getAttribute('data-tab');
            activateTab(targetTab);
            // Close mobile sidebar if open
            const sidebar = document.getElementById('sidebar');
            if (sidebar) sidebar.classList.remove('open');
        });
    });

    // Check hash on load
    const currentHash = window.location.hash.replace('#', '');
    if (currentHash && document.getElementById(currentHash)) {
        activateTab(currentHash);
    }

    // 2. Mobile Menu Toggle
    const menuToggle = document.getElementById('menuToggle');
    const sidebar = document.getElementById('sidebar');
    if (menuToggle && sidebar) {
        menuToggle.addEventListener('click', () => {
            sidebar.classList.toggle('open');
        });
    }

    // 3. Search and Category Filter for Menu
    const searchInput = document.getElementById('menuSearchInput');
    const catFilter = document.getElementById('menuCatFilter');
    const tableRows = document.querySelectorAll('#productsTable tbody tr');

    function filterMenuTable() {
        const query = searchInput ? searchInput.value.toLowerCase().trim() : '';
        const cat = catFilter ? catFilter.value : '';

        tableRows.forEach(row => {
            const name = row.querySelector('.prod-title')?.textContent.toLowerCase() || '';
            const desc = row.querySelector('.prod-desc')?.textContent.toLowerCase() || '';
            const rowCat = row.getAttribute('data-category') || '';

            const matchesQuery = !query || name.includes(query) || desc.includes(query);
            const matchesCat = !cat || rowCat === cat;

            row.style.display = (matchesQuery && matchesCat) ? '' : 'none';
        });
    }

    if (searchInput) searchInput.addEventListener('input', filterMenuTable);
    if (catFilter) catFilter.addEventListener('change', filterMenuTable);

    // Close modals on escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            document.querySelectorAll('.modal-backdrop.open').forEach(m => m.classList.remove('open'));
        }
    });

    // Close modals on clicking backdrop
    document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
        backdrop.addEventListener('click', (e) => {
            if (e.target === backdrop) {
                backdrop.classList.remove('open');
            }
        });
    });
});

// --- MODAL HELPERS ---
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.add('open');
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.remove('open');
}

// --- QUICK PRICE SAVE (AJAX) ---
function saveQuickPrice(pid) {
    const input = document.getElementById('price-input-' + pid);
    const badge = document.getElementById('price-badge-' + pid);
    if (!input) return;

    const priceVal = parseFloat(input.value);
    if (isNaN(priceVal) || priceVal < 0) {
        alert('Podaj prawidłową cenę.');
        return;
    }

    const formData = new FormData();
    formData.append('price', priceVal);

    fetch('/admin/product/' + pid + '/price', {
        method: 'POST',
        body: formData
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            if (badge) {
                badge.style.display = 'inline-block';
                setTimeout(() => { badge.style.display = 'none'; }, 2000);
            }
        } else {
            alert('Błąd zapisu ceny: ' + (data.error || 'Nieznany błąd'));
        }
    })
    .catch(err => {
        alert('Błąd sieci podczas zapisu ceny.');
    });
}

// --- TOGGLE PRODUCT FIELD (AJAX) ---
function toggleField(pid, field, btn) {
    const formData = new FormData();
    formData.append('field', field);

    fetch('/admin/product/' + pid + '/toggle', {
        method: 'POST',
        body: formData
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            const val = data.value;
            if (field === 'is_available') {
                btn.className = 'status-btn ' + (val ? 'status-on' : 'status-off');
                btn.querySelector('span').textContent = val ? '● W ofercie' : '○ Ukryty';
            } else if (field === 'is_vegetarian') {
                btn.classList.toggle('active-vege', val === 1);
            } else if (field === 'is_spicy') {
                btn.classList.toggle('active-spicy', val === 1);
            } else if (field === 'is_featured') {
                btn.classList.toggle('active-featured', val === 1);
            } else if (field === 'is_new') {
                btn.classList.toggle('active-new', val === 1);
            }
        } else {
            alert('Błąd: ' + (data.error || 'Nie można zmienić pola'));
        }
    })
    .catch(err => {
        alert('Błąd połączenia podczas przełączania.');
    });
}

// --- OPEN EDIT PRODUCT MODAL ---
function openEditProductModal(pid, name, catId, desc, price, img, sort, vege, spicy, feat, isNew) {
    document.getElementById('edit-pid').value = pid;
    document.getElementById('edit-name').value = name;
    document.getElementById('edit-category').value = catId;
    document.getElementById('edit-description').value = desc;
    document.getElementById('edit-price').value = parseFloat(price).toFixed(2);
    document.getElementById('edit-image').value = img;
    document.getElementById('edit-sort').value = sort;
    document.getElementById('edit-vege').checked = (vege === 1 || vege === true);
    document.getElementById('edit-spicy').checked = (spicy === 1 || spicy === true);
    document.getElementById('edit-featured').checked = (feat === 1 || feat === true);
    document.getElementById('edit-new').checked = (isNew === 1 || isNew === true);

    document.getElementById('edit-product-form').action = '/admin/product/' + pid + '/edit';
    openModal('edit-product-modal');
}

// --- OPEN EDIT ANNOUNCEMENT MODAL ---
function openEditAnnModal(id, badge, content, isActive) {
    document.getElementById('edit-ann-id').value = id;
    document.getElementById('edit-ann-badge').value = badge;
    document.getElementById('edit-ann-content').value = content;
    document.getElementById('edit-ann-active').checked = (isActive === 1 || isActive === true);
    openModal('edit-ann-modal');
}

// --- TOGGLE HOURS INPUTS WHEN DAY CLOSED ---
function toggleHoursInputs(checkbox) {
    const row = checkbox.closest('.hours-edit-row');
    if (row) {
        const timeInputs = row.querySelectorAll('input[type="time"]');
        timeInputs.forEach(inp => {
            inp.disabled = checkbox.checked;
        });
    }
}

// --- OPEN EDIT ORDER METHOD MODAL ---
function openEditOrderMethodModal(id, name, desc, url, img, sort) {
    document.getElementById('edit-om-name').value = name || '';
    document.getElementById('edit-om-desc').value = desc || '';
    document.getElementById('edit-om-url').value = url || '';
    document.getElementById('edit-om-img').value = img || '';
    document.getElementById('edit-om-sort').value = (sort !== undefined && sort !== null) ? sort : 10;

    document.getElementById('edit-ordermethod-form').action = '/admin/ordermethod/' + id + '/save';
    openModal('edit-ordermethod-modal');
}

function openEditOrderMethodModalFromBtn(btn) {
    const id = btn.getAttribute('data-id');
    const name = btn.getAttribute('data-name') || '';
    const desc = btn.getAttribute('data-desc') || '';
    const url = btn.getAttribute('data-url') || '';
    const img = btn.getAttribute('data-img') || '';
    const sort = btn.getAttribute('data-sort') || '10';
    openEditOrderMethodModal(id, name, desc, url, img, sort);
}
