/* global html2canvas */

/** @type {HTMLDivElement | null} */
const postEl = /** @type {HTMLDivElement | null} */ (document.getElementById('post'));

/** @type {HTMLButtonElement | null} */
const downloadBtn = /** @type {HTMLButtonElement | null} */ (document.getElementById('downloadBtn'));

/** @type {HTMLParagraphElement | null} */
const statusEl = /** @type {HTMLParagraphElement | null} */ (document.getElementById('status'));

/** @type {HTMLImageElement | null} */
const brandLogoEl = /** @type {HTMLImageElement | null} */ (document.getElementById('brandLogo'));

/** @type {HTMLImageElement | null} */
const postLogoEl = /** @type {HTMLImageElement | null} */ (document.getElementById('postLogo'));

/** @type {HTMLElement | null} */
const pageTitleEl = /** @type {HTMLElement | null} */ (document.getElementById('pageTitle'));

/** @type {any} */
const html2canvasFn = /** @type {any} */ (window)['html2canvas'];

/** @type {NodeListOf<HTMLButtonElement>} */
const variantButtons = document.querySelectorAll('[data-post-variant]');

/** @type {Record<string, string>} */
const variantToFileTag = {
    v1: 'premium',
    v2: 'callouts',
    v3: 'midnight',
    v4: 'editorial',
    v5: 'ribbon',
};

function isPreviewMode() {
    try {
        const url = new URL(window.location.href);
        return url.searchParams.get('preview') === '1';
    } catch {
        return false;
    }
}

function setStatus(text) {
    if (!statusEl) return;
    statusEl.textContent = text || '';
}

function setVariant(nextVariant) {
    if (!postEl) return;
    postEl.dataset.variant = nextVariant;

    variantButtons.forEach((btn) => {
        const variant = btn.getAttribute('data-post-variant');
        btn.setAttribute('aria-pressed', variant === nextVariant ? 'true' : 'false');
    });
}

variantButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
        const nextVariant = btn.getAttribute('data-post-variant');
        if (!nextVariant) return;
        setVariant(nextVariant);
    });
});

setVariant(postEl?.dataset?.variant || 'v1');

function sanitizeBrandId(raw) {
    const value = String(raw || '').trim().toLowerCase();
    if (!value) return '';
    return value.replace(/[^a-z0-9-_]/g, '');
}

function resolveParams() {
    let brand = 'happy-eats';
    let year = String(new Date().getFullYear() + 1);

    try {
        const url = new URL(window.location.href);
        brand = sanitizeBrandId(url.searchParams.get('brand')) || brand;
        year = String(url.searchParams.get('year') || year).trim() || year;
    } catch {
        // ignore
    }

    return { brand, year };
}

async function loadBrandConfig(brandId) {
    const safe = sanitizeBrandId(brandId);
    if (!safe) return null;
    const url = `/static/brands/${encodeURIComponent(safe)}/brand.json`;
    try {
        const res = await fetch(url, { cache: 'no-cache' });
        if (!res.ok) return null;
        const json = await res.json();
        if (!json || typeof json !== 'object') return null;
        return /** @type {any} */ (json);
    } catch {
        return null;
    }
}

function setMaybeText(selector, text) {
    document.querySelectorAll(selector).forEach((el) => {
        el.textContent = text;
    });
}

function setMaybeAttr(el, attr, value) {
    if (!el) return;
    if (!value) {
        el.removeAttribute(attr);
        return;
    }
    el.setAttribute(attr, value);
}

function applyYear(year) {
    setMaybeText('[data-year]', year);
}

function applyTheme(theme) {
    if (!postEl || !theme || typeof theme !== 'object') return;

    const map = {
        background0: '--p0',
        background1: '--p1',
        ink: '--pInk',
        muted: '--pMuted',
        accent: '--pAccent',
        accent2: '--pAccent2',
    };

    Object.entries(map).forEach(([key, cssVar]) => {
        const value = theme[key];
        if (typeof value === 'string' && value.trim()) {
            postEl.style.setProperty(cssVar, value.trim());
        }
    });

    const uiAccent = typeof theme.accent2 === 'string' && theme.accent2.trim()
        ? theme.accent2.trim()
        : (typeof theme.accent === 'string' ? theme.accent.trim() : '');
    if (uiAccent) {
        document.documentElement.style.setProperty('--ui-accent', uiAccent);
    }
}

function applyCopyOverrides(campaign) {
    if (!campaign || typeof campaign !== 'object') return;

    const roles = campaign.signatureRoles;
    if (roles && typeof roles === 'object') {
        document.querySelectorAll('[data-role]').forEach((el) => {
            const key = el.getAttribute('data-role');
            if (!key) return;
            const value = roles[key];
            if (typeof value === 'string' && value.trim()) el.textContent = value.trim();
        });
    }

    const callouts = Array.isArray(campaign.callouts) ? campaign.callouts : null;
    if (callouts) {
        document.querySelectorAll('[data-callout]').forEach((el) => {
            const idx = Number(el.getAttribute('data-callout'));
            const value = callouts[idx];
            if (typeof value === 'string' && value.trim()) el.textContent = value.trim();
        });
    }

    const badges = Array.isArray(campaign.badges) ? campaign.badges : null;
    if (badges) {
        document.querySelectorAll('[data-badge]').forEach((el) => {
            const idx = Number(el.getAttribute('data-badge'));
            const value = badges[idx];
            if (typeof value === 'string' && value.trim()) el.textContent = value.trim();
        });
    }

    const promises = Array.isArray(campaign.promises) ? campaign.promises : null;
    if (promises) {
        document.querySelectorAll('[data-promise-title]').forEach((el) => {
            const idx = Number(el.getAttribute('data-promise-title'));
            const value = promises[idx]?.title;
            if (typeof value === 'string' && value.trim()) el.textContent = value.trim();
        });
        document.querySelectorAll('[data-promise-body]').forEach((el) => {
            const idx = Number(el.getAttribute('data-promise-body'));
            const value = promises[idx]?.body;
            if (typeof value === 'string' && value.trim()) el.textContent = value.trim();
        });
    }
}

function applyBrand(brandId, brandConfig, year) {
    const name = typeof brandConfig?.name === 'string' && brandConfig.name.trim()
        ? brandConfig.name.trim()
        : brandId;
    const website = typeof brandConfig?.website === 'string' && brandConfig.website.trim()
        ? brandConfig.website.trim()
        : '';
    const logoUrl = typeof brandConfig?.logoUrl === 'string' && brandConfig.logoUrl.trim()
        ? brandConfig.logoUrl.trim()
        : '';

    if (pageTitleEl) pageTitleEl.textContent = `${name} • New Year ${year} Post Generator`;
    document.title = `${name} - New Year ${year} Post Generator`;
    if (postEl) postEl.setAttribute('aria-label', `${name} New Year ${year} social post`);

    setMaybeText('[data-website]', website || '');
    if (brandLogoEl) {
        if (logoUrl) {
            brandLogoEl.classList.remove('isHidden');
            brandLogoEl.src = logoUrl;
            brandLogoEl.alt = `${name} logo`;
        } else {
            brandLogoEl.classList.add('isHidden');
        }
    }
    if (postLogoEl) {
        if (logoUrl) {
            postLogoEl.classList.remove('isHidden');
            postLogoEl.src = logoUrl;
            setMaybeAttr(postLogoEl, 'alt', '');
        } else {
            postLogoEl.classList.add('isHidden');
        }
    }

    applyTheme(brandConfig?.theme);

    const campaign = brandConfig?.campaigns?.newYear || {};
    const fallbackBadges = Array.isArray(brandConfig?.badges) ? brandConfig.badges : null;
    if (!Array.isArray(campaign.badges) && fallbackBadges) {
        campaign.badges = fallbackBadges;
    }
    if (!Array.isArray(campaign.callouts) && Array.isArray(campaign.badges)) {
        campaign.callouts = campaign.badges.slice(0, 3);
    }
    applyCopyOverrides(campaign);
}

async function initBranding() {
    const { brand, year } = resolveParams();
    applyYear(year);

    const config = await loadBrandConfig(brand);
    applyBrand(brand, config || {}, year);

    const safeBrand = sanitizeBrandId(brand) || 'brand';
    variantButtons.forEach((btn) => {
        btn.dataset.filePrefix = `${safeBrand}-new-year-${year}`;
    });

    if (downloadBtn) {
        downloadBtn.dataset.filePrefix = `${safeBrand}-new-year-${year}`;
    }
}

async function downloadPostPng() {
    if (!postEl) return;
    if (typeof html2canvasFn !== 'function') {
        setStatus('html2canvas failed to load. Check your connection.');
        return;
    }
    if (!downloadBtn) return;

    downloadBtn.disabled = true;
    setStatus('Rendering...');

    try {
        const canvas = await html2canvasFn(postEl, {
            scale: 2,
            backgroundColor: null,
            logging: false,
            useCORS: true,
        });

        const variant = postEl.dataset.variant || 'v1';
        const fileTag = variantToFileTag[variant] || variant;
        const prefix = downloadBtn.dataset.filePrefix || 'post';

        const link = document.createElement('a');
        link.download = `${prefix}-${fileTag}.png`;
        link.href = canvas.toDataURL('image/png');
        document.body.appendChild(link);
        link.click();
        link.remove();

        setStatus('Downloaded.');
    } catch (err) {
        console.error('Error downloading image:', err);
        setStatus('Download failed. See console for details.');
    } finally {
        downloadBtn.disabled = false;
        window.setTimeout(() => setStatus(''), 2000);
    }
}

if (downloadBtn) {
    downloadBtn.addEventListener('click', downloadPostPng);
}

if (isPreviewMode()) {
    const root = document.documentElement;
    root.classList.add('preview');

    function applyScale() {
        const scale = Math.max(0.05, Math.min(window.innerWidth, window.innerHeight) / 1080);
        root.style.setProperty('--preview-scale', String(scale));
    }

    applyScale();
    window.addEventListener('resize', applyScale, { passive: true });
}

initBranding();

