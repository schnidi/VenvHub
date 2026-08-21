/* =========================================
   Company: Seal and Lube, spol. s r.o.
   Author: Ing. Viliam Schneider
   File: assets/js/seo/seo_title.js
   Description: Dynamic SEO, Meta tags, OpenGraph & Schema.org engine for Portal & Manual
========================================= */

/**
 * Dynamicky načíta JSON metadáta a aktualizuje celú hlavičku stránky (pre portál aj manuál)
 * @param {string} lang - 'sk' alebo 'en'
 * @param {string|null} chapterId - ID kapitoly (ak je null, načíta hlavné SEO portálu)
 * @param {string} basePath - relatívna cesta k priečinku assets ('assets' alebo '../assets')
 */
async function updateSEOMetadata(lang, chapterId = null, basePath = 'assets') {
    // Ak je zadané chapterId, ťahá SEO kapitoly, inak hlavné SEO portálu
    const seoFilePath = chapterId 
        ? `${basePath}/seo/${lang}/kapitoly/${chapterId}.json`
        : `${basePath}/seo/${lang}/seo_meta.json`;

    try {
        const response = await fetch(seoFilePath);
        if (!response.ok) {
            throw new Error(`Nepodarilo sa načítať ${seoFilePath} (HTTP ${response.status})`);
        }

        const data = await response.json();

        // 1. Nastavenie jazyka dokumentu a titulku okna
        document.documentElement.lang = lang;
        if (data.title) {
            document.title = data.title;
        }

        // 2. Štandardné Meta tagy
        if (data.description) setMetaTag('name', 'description', data.description);
        if (data.keywords) setMetaTag('name', 'keywords', data.keywords);

        // 3. OpenGraph tagy (Facebook, LinkedIn, Discord)
        setMetaTag('property', 'og:locale', data.og_locale || (lang === 'sk' ? 'sk_SK' : 'en_US'));
        setMetaTag('property', 'og:type', data.og_type || 'article');
        setMetaTag('property', 'og:site_name', data.og_site_name || 'VenvHub Pro');
        if (data.og_title || data.title) setMetaTag('property', 'og:title', data.og_title || data.title);
        if (data.og_description || data.description) setMetaTag('property', 'og:description', data.og_description || data.description);
        if (data.og_image) setMetaTag('property', 'og:image', data.og_image);

        // 4. Twitter Card tagy
        setMetaTag('name', 'twitter:card', data.twitter_card || 'summary_large_image');
        if (data.twitter_title || data.title) setMetaTag('name', 'twitter:title', data.twitter_title || data.title);
        if (data.twitter_description || data.description) setMetaTag('name', 'twitter:description', data.twitter_description || data.description);
        if (data.twitter_image || data.og_image) setMetaTag('name', 'twitter:image', data.twitter_image || data.og_image);

        // 5. Štruktúrované dáta Schema.org (len ak sú v JSON definované)
        if (data.schema_name || data.schema_description) {
            updateSchemaOrg(data);
        }

        // 6. Tooltipy pre hlavné menu portálu
        updateNavTooltips(data);

    } catch (error) {
        console.error('Chyba pri aktualizácii SEO metadát:', error);
    }
}

/**
 * Pomocná funkcia: Nájde existujúci meta tag alebo vytvorí nový
 */
function setMetaTag(attributeName, attributeValue, content) {
    if (!content) return;

    let element = document.querySelector(`meta[${attributeName}="${attributeValue}"]`);
    if (!element) {
        element = document.createElement('meta');
        element.setAttribute(attributeName, attributeValue);
        document.head.appendChild(element);
    }
    element.setAttribute('content', content);
}

/**
 * Pomocná funkcia: Aktualizuje JSON-LD Schema.org skript v hlavičke
 */
function updateSchemaOrg(data) {
    let scriptTag = document.getElementById('schemaOrgJsonLd');
    if (!scriptTag) {
        scriptTag = document.createElement('script');
        scriptTag.id = 'schemaOrgJsonLd';
        scriptTag.type = 'application/ld+json';
        document.head.appendChild(scriptTag);
    }

    const schemaData = {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": data.schema_name || data.title,
        "description": data.schema_description || data.description,
        "applicationCategory": data.schema_application_category || "DeveloperApplication",
        "operatingSystem": data.schema_operating_system || "Windows 10, Windows 11"
    };

    scriptTag.textContent = JSON.stringify(schemaData, null, 2);
}

/**
 * Pomocná funkcia: Nastaví atribúty title na navigačné odkazy
 */
function updateNavTooltips(data) {
    const navMap = {
        'nav_home': data.nav_home_title,
        'nav_about': data.nav_about_title,
        'nav_manual': data.nav_manual_title,
        'nav_community': data.nav_community_title
    };

    Object.keys(navMap).forEach(key => {
        if (navMap[key]) {
            const el = document.querySelector(`[data-i18n="${key}"]`);
            if (el) {
                el.setAttribute('title', navMap[key]);
            }
        }
    });
}