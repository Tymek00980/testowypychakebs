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
    window.toggleMobileMenu = function(e, forceState) {
        if (e && e.stopPropagation) e.stopPropagation();
        const hamburger = document.getElementById('hamburger');
        const navLinks = document.getElementById('navLinks');
        const navOverlay = document.getElementById('navOverlay');
        if (!navLinks) return;
        const willOpen = (forceState !== undefined) ? forceState : !navLinks.classList.contains('active');
        if (hamburger) {
            hamburger.classList.toggle('active', willOpen);
            hamburger.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
        }
        navLinks.classList.toggle('active', willOpen);
        if (navOverlay) navOverlay.classList.toggle('active', willOpen);
        document.body.classList.toggle('menu-locked', willOpen);
    };

    const hamburger = document.getElementById('hamburger');
    const navOverlay = document.getElementById('navOverlay');
    if (hamburger) {
        hamburger.addEventListener('click', (e) => {
            if (e && e.preventDefault) e.preventDefault();
            window.toggleMobileMenu(e);
        });
    }
    if (navOverlay) {
        navOverlay.addEventListener('click', (e) => {
            if (e && e.preventDefault) e.preventDefault();
            window.toggleMobileMenu(e, false);
        });
    }
    document.querySelectorAll('.nav-links a').forEach(link => {
        link.addEventListener('click', () => window.toggleMobileMenu(null, false));
    });
    document.addEventListener('keydown', (e) => {
        const navLinks = document.getElementById('navLinks');
        if (e.key === 'Escape' && navLinks && navLinks.classList.contains('active')) {
            window.toggleMobileMenu(null, false);
        }
    });
    document.addEventListener('click', (e) => {
        const navLinks = document.getElementById('navLinks');
        const hamburger = document.getElementById('hamburger');
        if (navLinks && navLinks.classList.contains('active')) {
            if (!navLinks.contains(e.target) && !hamburger.contains(e.target)) {
                window.toggleMobileMenu(null, false);
            }
        }
    });
    window.addEventListener('resize', () => {
        if (window.innerWidth > 860) {
            const navLinks = document.getElementById('navLinks');
            if (navLinks && navLinks.classList.contains('active')) {
                window.toggleMobileMenu(null, false);
            }
        }
    });

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
