// PYCHA KEBS - Ultra-smooth Client Script
document.addEventListener('DOMContentLoaded', () => {

    // 1. Hardware-Accelerated Reveal Animations (Zero Jank via IntersectionObserver)
    const reveals = document.querySelectorAll('.reveal');
    if ('IntersectionObserver' in window) {
        const revealObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('active');
                    observer.unobserve(entry.target);
                }
            });
        }, {
            root: null,
            rootMargin: '0px 0px -40px 0px',
            threshold: 0.08
        });

        reveals.forEach(el => revealObserver.observe(el));
    } else {
        // Fallback for older browsers
        const revealOnScroll = () => {
            const windowHeight = window.innerHeight;
            reveals.forEach(el => {
                if (el.getBoundingClientRect().top < windowHeight - 50) {
                    el.classList.add('active');
                }
            });
        };
        window.addEventListener('scroll', revealOnScroll, { passive: true });
        revealOnScroll();
    }

    // 2. High Performance Passive Navbar Scroll Effect
    const navbar = document.getElementById('navbar');
    if (navbar) {
        let lastScrollY = window.scrollY;
        let ticking = false;

        const updateNavbar = () => {
            navbar.classList.toggle('scrolled', lastScrollY > 25);
            ticking = false;
        };

        window.addEventListener('scroll', () => {
            lastScrollY = window.scrollY;
            if (!ticking) {
                window.requestAnimationFrame(updateNavbar);
                ticking = true;
            }
        }, { passive: true });
        updateNavbar();
    }

    // 3. Mobile Hamburger & Drawer Menu
    const hamburger = document.getElementById('hamburger');
    const navLinks = document.getElementById('navLinks');
    let navOverlay = document.getElementById('navOverlay');

    if (!navOverlay && hamburger) {
        navOverlay = document.createElement('div');
        navOverlay.id = 'navOverlay';
        navOverlay.className = 'nav-overlay';
        document.body.appendChild(navOverlay);
    }

    function toggleNavMenu(open) {
        if (!hamburger || !navLinks) return;
        const isOpen = (open !== undefined) ? open : !navLinks.classList.contains('active');
        hamburger.classList.toggle('active', isOpen);
        navLinks.classList.toggle('active', isOpen);
        if (navOverlay) navOverlay.classList.toggle('active', isOpen);
        document.body.classList.toggle('menu-locked', isOpen);
    }

    if (hamburger && navLinks) {
        hamburger.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleNavMenu();
        });

        if (navOverlay) {
            navOverlay.addEventListener('click', () => toggleNavMenu(false));
        }

        document.querySelectorAll('.nav-links a').forEach(link => {
            link.addEventListener('click', () => toggleNavMenu(false));
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && navLinks.classList.contains('active')) {
                toggleNavMenu(false);
            }
        });
    }

    // 4. Social Media Dropdown
    const socialBtn = document.getElementById('socialBtn');
    const socialMenu = document.getElementById('socialMenu');
    if (socialBtn && socialMenu) {
        socialBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            socialMenu.classList.toggle('active');
        });
        document.addEventListener('click', (e) => {
            if (!socialMenu.contains(e.target) && e.target !== socialBtn) {
                socialMenu.classList.remove('active');
            }
        });
    }

    // 5. Mobile-Optimized Menu Category Tabs
    const menuTabs = document.querySelectorAll('.menu-tab');
    const menuCategories = document.querySelectorAll('.menu-category');

    menuTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            menuTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            // Center tab in viewport on touch devices if container is scrollable
            if (tab.parentElement && tab.parentElement.scrollWidth > tab.parentElement.clientWidth) {
                tab.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
            }

            const targetSlug = tab.getAttribute('data-tab');
            menuCategories.forEach(cat => {
                const isTarget = cat.id === 'cat-' + targetSlug;
                cat.classList.toggle('active', isTarget);
                if (isTarget) {
                    cat.querySelectorAll('.reveal').forEach(r => r.classList.add('active'));
                }
            });
        });
    });

    // 6. Phone Order Toggle (Call options)
    const phoneToggle = document.getElementById('phoneToggle');
    const phoneLocations = document.getElementById('phoneLocations');
    if (phoneToggle && phoneLocations) {
        phoneToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            const isActive = phoneLocations.classList.toggle('active');
            phoneToggle.textContent = isActive ? 'Ukryj lokale' : 'Wybierz lokal';
        });

        document.addEventListener('click', (e) => {
            if (phoneLocations.classList.contains('active') && !phoneLocations.contains(e.target) && e.target !== phoneToggle) {
                phoneLocations.classList.remove('active');
                phoneToggle.textContent = 'Wybierz lokal';
            }
        });
    }

    // 7. Announcement Banner
    const closeAnnBtn = document.getElementById('closeAnnouncementBtn');
    const annBanner = document.getElementById('announcementBanner');
    if (closeAnnBtn && annBanner) {
        if (sessionStorage.getItem('pycha_ann_dismissed') === '1') {
            annBanner.style.display = 'none';
        }

        closeAnnBtn.addEventListener('click', () => {
            annBanner.style.display = 'none';
            sessionStorage.setItem('pycha_ann_dismissed', '1');
            const hero = document.querySelector('.hero');
            if (hero) hero.classList.remove('with-announcement');
        });
    }
});
