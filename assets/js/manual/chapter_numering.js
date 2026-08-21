/* =========================================
   Company: Seal and Lube, spol. s r.o.
   Author: Ing. Viliam Schneider
   File: assets/js/manual/chapter_numering.js
   Description: Dynamic documentation engine with SEO URL routing & dynamic per-chapter SEO
========================================= */

let chaptersList = [];
let currentChapterIndex = 0;
let currentLanguage = 'sk';

document.addEventListener('DOMContentLoaded', () => {
    initMobileDrawer();
    initLanguageDropdowns();

    // 1. Zistenie jazyka z URL (?lang=..) -> pamäť -> predvolený 'sk'
    const urlParams = new URLSearchParams(window.location.search);
    const lang = urlParams.get('lang') || localStorage.getItem('venvhub_lang') || 'sk';

    window.loadLanguage(lang, false);
});

/**
 * Pomocná funkcia: Očistí názov od starých natvrdo napísaných čísel
 */
function cleanTitleString(str) {
    if (!str) return '';
    return str.replace(/^([^\w\s\u00C0-\u017F]*\s*)?(\d+(\.\d+)*[\.\)]\s*)?/, '').trim();
}

/**
 * Hlavná funkcia pre prepnutie jazyka celej dokumentácie
 */
window.loadLanguage = async function(lang, pushToHistory = true) {
    currentLanguage = lang;
    localStorage.setItem('venvhub_lang', lang);

    // Aktualizácia textov a spätných odkazov na portál
    updateLanguageLabels(lang);

    // Načítanie obsahu kapitol
    await loadModularManual(lang, pushToHistory);

    document.getElementById('desktopLangDropdown')?.classList.remove('show');
    document.getElementById('mobileLangDropdown')?.classList.remove('show');
};

// Reakcia na tlačidlá Späť / Dopredu v prehliadači
window.addEventListener('popstate', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const lang = urlParams.get('lang') || 'sk';
    const chParam = urlParams.get('ch');

    if (lang !== currentLanguage) {
        window.loadLanguage(lang, false);
    } else if (chParam) {
        const targetIndex = chaptersList.findIndex(ch => ch.id === chParam);
        if (targetIndex !== -1 && targetIndex !== currentChapterIndex) {
            showChapter(targetIndex, null, false);
        }
    }
});

/**
 * Načíta manifest.json a paralelne stiahne čisté JSON súbory kapitol
 */
async function loadModularManual(lang, pushToHistory = true) {
    try {
        const manifestRes = await fetch('../assets/manual/manifest.json');
        if (!manifestRes.ok) {
            throw new Error(`Nepodarilo sa načítať manifest.json (HTTP ${manifestRes.status})`);
        }
        const fileNames = await manifestRes.json();

        const fetchPromises = fileNames.map(async (fileName) => {
            const filePath = `../assets/manual/${lang}/${fileName}.json`;
            const res = await fetch(filePath);
            if (!res.ok) {
                throw new Error(`Súbor "${fileName}.json" neexistuje (HTTP ${res.status})`);
            }
            const rawText = await res.text();
            try {
                return JSON.parse(rawText);
            } catch (jsonErr) {
                throw new Error(`Chyba syntaxe v "${fileName}.json": ${jsonErr.message}`);
            }
        });

        chaptersList = await Promise.all(fetchPromises);

        // Vykreslenie bočného menu s novými SEO URL adresami
        renderSidebar();

        // 2. Vyhľadanie kapitoly podľa URL parametra ?ch=... alebo starého hashu #...
        const urlParams = new URLSearchParams(window.location.search);
        const chParam = urlParams.get('ch');
        const hash = window.location.hash.replace('#', '');
        const targetId = chParam || hash;

        let targetIndex = chaptersList.findIndex(ch => ch.id === targetId);
        let targetSectionId = null;

        if (targetIndex === -1 && targetId) {
            chaptersList.forEach((ch, chIdx) => {
                if (ch.sections && ch.sections.some(s => s.id === targetId)) {
                    targetIndex = chIdx;
                    targetSectionId = targetId;
                }
            });
        }

        if (targetIndex === -1) {
            targetIndex = currentChapterIndex < chaptersList.length ? currentChapterIndex : 0;
        }

        showChapter(targetIndex, targetSectionId, pushToHistory);

    } catch (error) {
        console.error('Chyba dynamického manuálu:', error);
        document.getElementById('contentArea').innerHTML = `
            <div style="color: #ff4d4d; background: #2a1515; border: 1px solid #ff4d4d; padding: 20px; border-radius: 6px; font-family: monospace;">
                <strong>⚠️ Chyba pri načítavaní manuálu:</strong><br><br>
                ${error.message}
            </div>
        `;
    }
}

/**
 * Vykreslí bočné menu s čistými SEO odkazmi (?lang=en&ch=...)
 */
function renderSidebar() {
    const nav = document.getElementById('sidebarNav');
    if (!nav || chaptersList.length === 0) return;

    nav.innerHTML = '';

    chaptersList.forEach((chapter, chIdx) => {
        const chNum = chIdx + 1;
        const icon = chapter.icon ? `${chapter.icon} ` : '';
        const cleanTitle = cleanTitleString(chapter.title);
        const fullTitle = `${icon}${chNum}. ${cleanTitle}`;

        const a = document.createElement('a');
        a.href = `index-manual.html?lang=${currentLanguage}&ch=${chapter.id}`;
        a.className = 'nav-item';
        a.textContent = fullTitle;
        a.dataset.index = chIdx;

        a.addEventListener('click', (e) => {
            e.preventDefault();
            showChapter(chIdx);
            closeMobileDrawer();
        });

        nav.appendChild(a);

        if (chapter.sections && chapter.sections.length > 0) {
            const subNav = document.createElement('div');
            subNav.className = 'sub-nav';
            subNav.id = `sub-nav-${chIdx}`;
            subNav.style.display = 'none';

            chapter.sections.forEach((sec, secIdx) => {
                const secNum = `${chNum}.${secIdx + 1}`;
                const cleanSecTitle = cleanTitleString(sec.title);
                const subA = document.createElement('a');
                subA.href = `index-manual.html?lang=${currentLanguage}&ch=${chapter.id}#${sec.id}`;
                subA.className = 'sub-item';
                subA.textContent = `${secNum} ${cleanSecTitle}`;

                subA.addEventListener('click', (e) => {
                    e.preventDefault();
                    if (currentChapterIndex !== chIdx) {
                        showChapter(chIdx, sec.id);
                    } else {
                        scrollToSection(sec.id);
                    }
                    closeMobileDrawer();
                });

                subNav.appendChild(subA);
            });

            nav.appendChild(subNav);
        }
    });
}

/**
 * Zostaví a zobrazí čistý HTML obsah a aktualizuje URL aj SEO metadáta
 */
function showChapter(chIdx, targetSectionId = null, pushToHistory = true) {
    if (!chaptersList[chIdx]) return;

    currentChapterIndex = chIdx;
    const chapter = chaptersList[chIdx];
    const chNum = chIdx + 1;
    const contentArea = document.getElementById('contentArea');
    const cleanChTitle = cleanTitleString(chapter.title);

    let html = `<h1>${chNum}. ${cleanChTitle}</h1>`;

    const hasSectionContents = chapter.sections && chapter.sections.length > 0 && chapter.sections.some(s => s.content);

    if (hasSectionContents) {
        chapter.sections.forEach((sec, secIdx) => {
            const secNum = `${chNum}.${secIdx + 1}`;
            const cleanSecTitle = cleanTitleString(sec.title);
            const bodyContent = sec.content || '';
            html += `
                <div id="${sec.id}" class="section-box" style="margin-bottom: 35px;">
                    <h2>${secNum} ${cleanSecTitle}</h2>
                    ${bodyContent}
                </div>
            `;
        });
    } else if (chapter.content) {
        html += chapter.content;
    }

    contentArea.innerHTML = html;

    // 1. Aktualizácia URL adresy: index-manual.html?lang=en&ch=nazov_kapitoly
    const sectionAnchor = targetSectionId ? `#${targetSectionId}` : '';
    const newUrl = `${window.location.pathname}?lang=${currentLanguage}&ch=${chapter.id}${sectionAnchor}`;

    if (pushToHistory) {
        window.history.pushState({ lang: currentLanguage, ch: chapter.id }, '', newUrl);
    } else {
        window.history.replaceState({ lang: currentLanguage, ch: chapter.id }, '', newUrl);
    }

    // 2. Dynamická aktualizácia SEO hlavičky pre túto konkrétnu kapitolu
    if (typeof updateSEOMetadata === 'function') {
        updateSEOMetadata(currentLanguage, chapter.id, '../assets');
    }

    document.querySelectorAll('.nav-item').forEach((el, i) => {
        el.classList.toggle('active', i === chIdx);
    });

    document.querySelectorAll('.sub-nav').forEach((el, i) => {
        el.style.display = i === chIdx ? 'flex' : 'none';
    });

    updateChapterNavigation(chIdx);

    if (targetSectionId) {
        scrollToSection(targetSectionId);
    } else {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
}

function scrollToSection(sectionId) {
    setTimeout(() => {
        const el = document.getElementById(sectionId);
        if (el) {
            const offset = 80;
            const top = el.getBoundingClientRect().top + window.pageYOffset - offset;
            window.scrollTo({ top: top, behavior: 'smooth' });
        }
    }, 60);
}

/**
 * Aktualizuje spodné tlačidlá s čistými SEO URL odkazmi (?lang=en&ch=...)
 */
function updateChapterNavigation(chIdx) {
    const prevBtn = document.getElementById('prevChapterBtn');
    const nextBtn = document.getElementById('nextChapterBtn');
    const prevTitle = document.getElementById('prevChapterTitle');
    const nextTitle = document.getElementById('nextChapterTitle');

    // 1. Predchádzajúca kapitola
    if (chIdx > 0) {
        const prevNum = chIdx;
        const prevChapter = chaptersList[chIdx - 1];
        prevBtn.style.display = 'flex';
        prevBtn.href = `index-manual.html?lang=${currentLanguage}&ch=${prevChapter.id}`;
        prevTitle.textContent = `${prevNum}. ${cleanTitleString(prevChapter.title)}`;
        
        prevBtn.onclick = (e) => {
            e.preventDefault();
            showChapter(chIdx - 1);
        };
    } else {
        prevBtn.style.display = 'none';
        prevBtn.removeAttribute('href');
        prevBtn.onclick = null;
    }

    // 2. Nasledujúca kapitola
    if (chIdx < chaptersList.length - 1) {
        const nextNum = chIdx + 2;
        const nextChapter = chaptersList[chIdx + 1];
        nextBtn.style.display = 'flex';
        nextBtn.href = `index-manual.html?lang=${currentLanguage}&ch=${nextChapter.id}`;
        nextTitle.textContent = `${nextNum}. ${cleanTitleString(nextChapter.title)}`;
        
        nextBtn.onclick = (e) => {
            e.preventDefault();
            showChapter(chIdx + 1);
        };
    } else {
        nextBtn.style.display = 'none';
        nextBtn.removeAttribute('href');
        nextBtn.onclick = null;
    }
}

/**
 * Aktualizuje preklady rozhrania a synchronizuje spätný odkaz na portál
 */
function updateLanguageLabels(lang) {
    const desktopLabel = document.getElementById('desktopLangLabel');
    const mobileLabel = document.getElementById('mobileLangLabel');
    const backHome = document.getElementById('backHomeLink');
    const mobileHome = document.querySelector('.mobile-home-btn');
    const manualBadge = document.getElementById('manualBadge');
    const prevSubText = document.getElementById('prevSubText');
    const nextSubText = document.getElementById('nextSubText');

    // Spätný odkaz na portál v rovnakom jazyku
    const homeUrl = `../index.html?lang=${lang}`;
    if (backHome) backHome.href = homeUrl;
    if (mobileHome) mobileHome.href = homeUrl;

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

    // Plynulé prepnutie jazyka cez data-lang atribút
    dropdown.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetLang = link.getAttribute('data-lang');
            if (targetLang) {
                window.loadLanguage(targetLang);
            }
        });
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