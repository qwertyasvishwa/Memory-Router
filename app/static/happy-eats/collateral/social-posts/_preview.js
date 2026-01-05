(function () {
    const params = new URLSearchParams(window.location.search);
    if (params.get('preview') !== '1') return;

    const root = document.documentElement;
    const post = document.querySelector('.post');
    if (!post) return;

    root.classList.add('preview');

    function applyScale() {
        const scale = Math.max(0.05, Math.min(window.innerWidth, window.innerHeight) / 1080);
        root.style.setProperty('--preview-scale', String(scale));
    }

    applyScale();
    window.addEventListener('resize', applyScale, { passive: true });
})();

