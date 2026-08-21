/* =========================================
   Company: Seal and Lube, spol. s r.o.
   Author: Ing. Viliam Schneider
   File: root/assets/js/index_page.js
========================================= */

document.addEventListener('DOMContentLoaded', () => {
    initLanguageSwitcher();
    // Výchozí jazyk pri štarte (SK)
    window.loadLanguage('sk');
});

/**
 * Dynamicky načíta HTML fragment z príslušnej jazykovej zložky
 */
window.loadLanguage = async function(lang) {
    const container = document.getElementById('content-container');
    const label = document.getElementById('currentLangLabel');
    const filePath = `${lang}/index_text.html`;

    try {
        const response = await fetch(filePath);
        if (!response.ok) {
            throw new Error(`Nepodarilo sa načítať súbor ${filePath}`);
        }

        const htmlContent = await response.text();
        if (container) {
            container.innerHTML = htmlContent;
        }

        // Aktualizovať názov jazyka na tlačidle
        if (label) {
            label.textContent = lang === 'sk' ? 'Slovenčina' : 'English';
        }

        // Re-inicializovať zvýrazňovanie menu po načítaní nového obsahu
        initNavigationHighlight();

        if (typeof fetchLatestGitHubRelease === 'function') {
            fetchLatestGitHubRelease();
        }

    } catch (error) {
        console.error('Chyba pri načítavaní jazyka:', error);
        if (container) {
            container.innerHTML = `<div style="color: red; padding: 20px;">Chyba pri načítavaní obsahu (${error.message}).</div>`;
        }
    }

    // Zatvoriť dropdown
    document.getElementById('langDropdown')?.classList.remove('show');
};

/**
 * Obsluha roztovieracieho tlačidla pre jazyky
 */
function initLanguageSwitcher() {
    const langBtn = document.getElementById('langBtn');
    const langDropdown = document.getElementById('langDropdown');

    if (!langBtn || !langDropdown || langBtn.dataset.listener) return;
    langBtn.dataset.listener = 'true';

    langBtn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        langDropdown.classList.toggle('show');
    });

    document.addEventListener('click', (e) => {
        if (!langBtn.contains(e.target) && !langDropdown.contains(e.target)) {
            langDropdown.classList.remove('show');
        }
    });
}

/**
 * Zvýrazňovanie aktívneho odkazu v hornom menu pri skrolovaní
 */
function initNavigationHighlight() {
    const navLinks = document.querySelectorAll('.nav-menu a');
    const sections = document.querySelectorAll('section');

    window.addEventListener('scroll', () => {
        let current = '';

        sections.forEach(section => {
            const sectionTop = section.offsetTop - 80;
            if (window.scrollY >= sectionTop) {
                current = section.getAttribute('id');
            }
        });

        navLinks.forEach(link => {
            link.classList.remove('active');
            if (current && link.getAttribute('href') === `#${current}`) {
                link.classList.add('active');
            }
        });
    });
}