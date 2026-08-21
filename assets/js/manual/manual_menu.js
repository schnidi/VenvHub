/* =========================================
   Company: Seal and Lube, spol. s r.o.
   Author: Ing. Viliam Schneider
   File: assets/js/manual/manual_menu.js
========================================= */

let chaptersList = [];
let currentChapterIndex = 0;
let currentLanguage = localStorage.getItem('venvhub_lang') || 'sk';

document.addEventListener('DOMContentLoaded', () => {
    initMobileDrawer();
    initLanguageDropdowns();
    window.loadLanguage(currentLanguage);
});

/**
 * Hlavná funkcia pre prepnutie jazyka
 */
window.loadLanguage = async function(lang) {
    currentLanguage = lang;
    localStorage.setItem('venvhub_lang', lang);

    updateLanguageLabels(lang);
    await loadModularManual(lang);

    document.getElementById('desktopLangDropdown')?.classList.remove('show');
    document.getElementById('mobileLangDropdown')?.classList.remove('show');
};

/**
 * Načíta manifest a jednotlivé JSON súbory kapitol
 */
async function loadModularManual(lang) {
    try {
        // 1. Načítame manifest so zoznamom kapitol
        const manifestRes = await fetch('../assets/manual/manifest.json');
        if (!manifestRes.ok) {
            throw new Error(`Nepodarilo sa načítať manifest.json (HTTP ${manifestRes.status})`);
        }
        const fileNames = await manifestRes.json();

        // 2. Paralelne načítame všetky samostatné JSON súbory pre daný jazyk
        const fetchPromises = fileNames.map(fileName => 
            fetch(`../assets/manual/${lang}/${fileName}.json`).then(r => {
                if (!r.ok) throw new Error(`Chyba načítania ${fileName}.json (HTTP ${r.status})`);
                return r.json();
            })
        );

        chaptersList = await Promise.all(fetchPromises);

        // 3. Vykreslíme menu poskladané zo všetkých modulov
        renderSidebar();

        // 4. Zobrazíme kapitolu podľa URL hashu alebo prvú
        const hash = window.location.hash.replace('#', '');
        let targetIndex = chaptersList.findIndex(ch => ch.id === hash);
        if (targetIndex === -1) {
            targetIndex = currentChapterIndex < chaptersList.length ? currentChapterIndex : 0;
        }

        showChapter(targetIndex);

    } catch (error) {
        console.error('Chyba modulárneho manuálu:', error);
        document.getElementById('contentArea').innerHTML = `
            <div style="color: red; padding: 20px;">
                Chyba pri načítavaní modulov manuálu: ${error.message}
            </div>
        `;
    }
}

/**
 * Vykreslí dynamické bočné menu
 */
function renderSidebar() {
    const nav = document.getElementById('sidebarNav');
    if (!nav || chaptersList.length === 0) return;

    nav.innerHTML = '';

    chaptersList.forEach((chapter, index) => {
        const a = document.createElement('a');
        a.href = `#${chapter.id}`;
        a.className = 'nav-item';
        a.textContent = chapter.title;
        a.dataset.index = index;

        a.addEventListener('click', (e) => {
            e.preventDefault();
            showChapter(index);
            closeMobileDrawer();
        });

        nav.appendChild(a);

        // Podkapitoly modulu
        if (chapter.sections && chapter.sections.length > 0) {
            const subNav = document.createElement('div');
            subNav.className = 'sub-nav';
            subNav.id = `sub-nav-${index}`;
            subNav.style.display = 'none';

            chapter.sections.forEach(sec => {
                const subA = document.createElement('a');
                subA.href = `#${sec.id}`;
                subA.className = 'sub-item';
                subA.textContent = sec.title;

                subA.addEventListener('click', (e) => {
                    e.preventDefault();
                    if (currentChapterIndex !== index) {
                        showChapter(index);
                    }
                    scrollToSection(sec.id);
                    closeMobileDrawer();
                });

                subNav.appendChild(subA);
            });

            nav.appendChild(subNav);
        }
    });
}

/**
 * Zobrazí obsah vybranej kapitoly
 */
function showChapter(index) {
    if (!chaptersList[index]) return;

    currentChapterIndex = index;
    const chapter = chaptersList[index];

    const contentArea = document.getElementById('contentArea');
    contentArea.innerHTML = chapter.content;

    window.location.hash = chapter.id;

    document.querySelectorAll('.nav-item').forEach((el, i) => {
        el.classList.toggle('active', i === index);
    });

    document.querySelectorAll('.sub-nav').forEach((el, i) => {
        el.style.display = i === index ? 'flex' : 'none';
    });

    updateChapterNavigation(index);
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function scrollToSection(sectionId) {
    setTimeout(() => {
        const el = document.getElementById(sectionId);
        if (el) {
            const offset = 80;
            const top = el.getBoundingClientRect().top + window.pageYOffset - offset;
            window.scrollTo({ top: top, behavior: 'smooth' });
        }
    }, 50);
}

function updateChapterNavigation(index) {
    const prevBtn = document.getElementById('prevChapterBtn');
    const nextBtn = document.getElementById('nextChapterBtn');
    const prevTitle = document.getElementById('prevChapterTitle');
    const nextTitle = document.getElementById('nextChapterTitle');

    if (index > 0) {
        prevBtn.style.display = 'flex';
        prevTitle.textContent = chaptersList[index - 1].title;
        prevBtn.onclick = () => showChapter(index - 1);
    } else {
        prevBtn.style.display = 'none';
    }

    if (index < chaptersList.length - 1) {
        nextBtn.style.display = 'flex';
        nextTitle.textContent = chaptersList[index + 1].title;
        nextBtn.onclick = () => showChapter(index + 1);
    } else {
        nextBtn.style.display = 'none';
    }
}

function updateLanguageLabels(lang) {
    const desktopLabel = document.getElementById('desktopLangLabel');
    const mobileLabel = document.getElementById('mobileLangLabel');
    const backHome = document.getElementById('backHomeLink');
    const manualBadge = document.getElementById('manualBadge');
    const prevSubText = document.getElementById('prevSubText');
    const nextSubText = document.getElementById('nextSubText');

    if (lang === 'en') {
        if (desktopLabel) desktopLabel.textContent = 'English';
        if (mobileLabel) mobileLabel.textContent = 'EN';
        if (backHome) backHome.textContent = '← Back to Portal';
        if (manualBadge) manualBadge.textContent = 'User Manual v2.5';
        if (prevSubText) prevSubText.textContent = '← Previous';
        if (nextSubText) nextSubText.textContent = 'Next Chapter →';
    } else {
        if (desktopLabel) desktopLabel.textContent = 'Slovenčina';
        if (mobileLabel) mobileLabel.textContent = 'SK';
        if (backHome) backHome.textContent = '← Späť na web VenvHub';
        if (manualBadge) manualBadge.textContent = 'Užívateľský Manuál v2.5';
        if (prevSubText) prevSubText.textContent = '← Predchádzajúca';
        if (nextSubText) nextSubText.textContent = 'Ďalšia kapitola →';
    }
}

function initLanguageDropdowns() {
    setupDropdown('desktopLangBtn', 'desktopLangDropdown');
    setupDropdown('mobileLangBtn', 'mobileLangDropdown');
}

function setupDropdown(btnId, dropdownId) {
    const btn = document.getElementById(btnId);
    const dropdown = document.getElementById(dropdownId);

    if (!btn || !dropdown || btn.dataset.listener) return;
    btn.dataset.listener = 'true';

    btn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropdown.classList.toggle('show');
    });

    document.addEventListener('click', (e) => {
        if (!btn.contains(e.target) && !dropdown.contains(e.target)) {
            dropdown.classList.remove('show');
        }
    });
}

function initMobileDrawer() {
    const menuBtn = document.getElementById('mobileMenuBtn');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');

    if (!menuBtn || !sidebar || !overlay) return;

    menuBtn.addEventListener('click', () => {
        sidebar.classList.toggle('open');
        overlay.classList.toggle('active');
    });

    overlay.addEventListener('click', closeMobileDrawer);
}

function closeMobileDrawer() {
    document.getElementById('sidebar')?.classList.remove('open');
    document.getElementById('sidebarOverlay')?.classList.remove('active');
}