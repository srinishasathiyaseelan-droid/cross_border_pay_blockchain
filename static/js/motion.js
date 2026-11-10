/**
 * CrossPay motion layer ("Signed Ledger"). Spec and full table: design-work/06-motion.md
 *  - Tier 1 (micro) lives in CSS transitions on tokens.
 *  - Tier 2/3 (component, page) uses Anime.js v4 (window.anime) when present; otherwise everything is shown instantly.
 * Animates transform and opacity only. Under prefers-reduced-motion nothing moves: elements just appear.
 */
(function () {
    'use strict';
    const A = window.anime;
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const root = document.documentElement;
    const DUR = { fast: 150, base: 220, slow: 350, page: 500 };
    const EASE = { standard: 'cubicBezier(0.2, 0, 0, 1)', emphasized: 'cubicBezier(0.3, 0, 0, 1.15)', exit: 'cubicBezier(0.4, 0, 1, 1)' };

    function done() { root.classList.remove('motion-pending'); }
    // Safety: never leave content hidden if something fails.
    setTimeout(done, 1600);

    function reveal() {
        const items = Array.from(document.querySelectorAll('[data-reveal]'));
        if (!items.length || reduce || !A) { done(); return; }
        A.animate(items, {
            opacity: [0, 1],
            translateY: [10, 0],
            duration: DUR.page,
            delay: A.stagger(50),
            ease: EASE.standard,
            onBegin: done,
        });
    }

    function pipeline() {
        document.querySelectorAll('.pipeline[data-progress]').forEach((p) => {
            const target = parseFloat(p.dataset.progress) || 0;
            const fill = p.querySelector('.pipeline-line > i');
            if (!fill) return;
            if (reduce || !A) { fill.style.transform = 'scaleX(' + target + ')'; return; }
            fill.style.transform = 'scaleX(0)';
            A.animate(fill, { scaleX: [0, target], duration: 900, delay: 250, ease: EASE.standard });
        });
    }

    function tickers() {
        const els = Array.from(document.querySelectorAll('[data-ticker]'));
        if (!els.length || reduce || !A || !('IntersectionObserver' in window)) return;
        const io = new IntersectionObserver((entries) => {
            entries.forEach((e) => {
                if (!e.isIntersecting) return;
                io.unobserve(e.target);
                const el = e.target;
                const finalText = el.textContent;
                const value = parseFloat(el.dataset.ticker);
                if (!isFinite(value) || value === 0 || document.hidden) return;
                const decimals = (el.dataset.decimals | 0);
                const state = { v: 0 };
                const anim = A.animate(state, {
                    v: value, duration: 900, ease: EASE.standard,
                    onUpdate: () => { el.textContent = state.v.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals }); },
                    onComplete: () => { el.textContent = finalText; },   // always end on the server-rendered text
                });
                // If frames stall (background tab), stop the count and show the real number; a late frame can't overwrite it.
                setTimeout(() => { if (anim && anim.pause) anim.pause(); el.textContent = finalText; }, 1400);
            });
        }, { threshold: 0.4 });
        els.forEach((el) => io.observe(el));
    }

    function bars() {
        const fills = Array.from(document.querySelectorAll('.bar-fill'));
        if (!fills.length || reduce || !A) return;
        A.animate(fills, { scaleX: [0, 1], duration: DUR.page + 200, delay: A.stagger(40), ease: EASE.standard });
    }

    function receipt() {
        const r = document.querySelector('.receipt');
        if (!r || reduce || !A) return;
        A.animate(r, { opacity: [0, 1], translateY: [-14, 0], duration: DUR.page, ease: EASE.emphasized });
        const stamp = r.querySelector('.stamp');
        if (stamp) A.animate(stamp, { opacity: [0, 1], scale: [1.25, 1], rotate: ['-10deg', '-4deg'], duration: DUR.slow, delay: 380, ease: EASE.emphasized });
    }

    function ledgerLinks() {
        const links = Array.from(document.querySelectorAll('.chain-link path'));
        if (!links.length || reduce || !A || !('IntersectionObserver' in window)) return;
        links.forEach((p) => { const len = p.getTotalLength(); p.style.strokeDasharray = len; p.style.strokeDashoffset = len; });
        const io = new IntersectionObserver((entries) => entries.forEach((e) => {
            if (!e.isIntersecting) return;
            io.unobserve(e.target);
            A.animate(e.target, { strokeDashoffset: [e.target.getTotalLength(), 0], duration: 600, ease: EASE.standard });
        }), { threshold: 0.6 });
        links.forEach((p) => io.observe(p));
    }

    // Expose small helpers for other scripts (toasts, AI panels) without duplicating timing values.
    window.CrossPayMotion = {
        reduce,
        enter(el) {
            if (!el || reduce || !A) return;
            A.animate(el, { opacity: [0, 1], translateY: [6, 0], duration: DUR.base, ease: EASE.standard });
        },
    };

    document.addEventListener('DOMContentLoaded', () => {
        reveal();
        pipeline();
        tickers();
        bars();
        receipt();
        ledgerLinks();
    });
})();
