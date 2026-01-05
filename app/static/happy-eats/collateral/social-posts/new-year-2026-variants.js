/* global html2canvas */

/** @type {HTMLDivElement | null} */
const postEl = /** @type {HTMLDivElement | null} */ (document.getElementById('post'));

/** @type {HTMLButtonElement | null} */
const downloadBtn = /** @type {HTMLButtonElement | null} */ (document.getElementById('downloadBtn'));

/** @type {HTMLParagraphElement | null} */
const statusEl = /** @type {HTMLParagraphElement | null} */ (document.getElementById('status'));

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

        const link = document.createElement('a');
        link.download = `happy-eats-new-year-2026-${fileTag}.png`;
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
