/* =========================================
   Company: Seal and Lube, spol. s r.o.
   Author: Ing. Viliam Schneider
   File: root/assets/js/git_exe_release.js
========================================= */

/**
 * Automaticky zisťuje najnovšie vydanie z GitHub API a vloží verziu do hlavičky aj tlačidla
 */
async function fetchLatestGitHubRelease() {
    const versionBadge = document.getElementById('latestVersionBadge');
    const headerVersionBadge = document.getElementById('headerVersionBadge');
    const releaseInfoBox = document.getElementById('releaseInfoBox');

    try {
        const response = await fetch('https://api.github.com/repos/schnidi/VenvHub/releases/latest');
        if (response.ok) {
            const data = await response.json();
            const rawTagName = data.tag_name || data.name || '';

            if (rawTagName) {
                // Vytiahne z reťazca "VenvHubPro_v2.5.25" iba časť "v2.5.25"
                const versionMatch = rawTagName.match(/v\d+(\.\d+)*/i);
                const cleanVersion = versionMatch ? versionMatch[0] : rawTagName;

                // 1. Nastavenie verzie v logu v hlavičke
                if (headerVersionBadge) {
                    headerVersionBadge.textContent = cleanVersion;
                }

                // 2. Nastavenie verzie v zelenom tlačidle na stiahnutie
                if (versionBadge) {
                    versionBadge.textContent = `(${cleanVersion})`;
                }

                // 3. Info box pod tlačidlami
                if (releaseInfoBox && data.published_at) {
                    const releaseDate = new Date(data.published_at).toLocaleDateString();
                    releaseInfoBox.innerHTML = `Najnovšie zostavenie: <strong>${cleanVersion}</strong> | Dátum vydania: ${releaseDate}`;
                }
            }
        }
    } catch (err) {
        console.log('GitHub API nedostupné, používa sa predvolená verzia.');
    }
}