/**
 * CrossPay front-end behaviour (vanilla JS, no build step).
 * - Live FX conversion (GET /api/convert_currency)
 * - Live risk preview from the SAME server model (POST /api/risk_preview; nothing is stored)  [M5]
 * - Demo scenarios (DEMO_MODE only): send scenario=low|medium|high; the server loads a fixed vector  [C4]
 * - Ledger verification, double-submit guard, AI advisory polling, theme toggle
 */
(function () {
    'use strict';

    const CURRENCY_SYMBOLS = { USD: '$', EUR: '€', GBP: '£', INR: '₹', SGD: 'S$', AED: 'AED ', AUD: 'A$', CAD: 'C$', JPY: '¥' };
    const $ = (id) => document.getElementById(id);
    const debounce = (fn, ms) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };

    function setText(el, text) { if (el) el.textContent = text; }

    function jsonPost(url, body) {
        return fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify(body)
        }).then((r) => r.json().then((d) => ({ ok: r.ok, status: r.status, data: d })));
    }

    /* ---------- Theme (per-viewer convenience only) ---------- */
    function initTheme() {
        const btn = $('theme-toggle');
        const root = document.documentElement;
        try {
            const saved = localStorage.getItem('crosspay-theme');
            if (saved === 'light' || saved === 'dark') root.setAttribute('data-theme', saved);
        } catch (e) { /* storage unavailable */ }
        if (!btn) return;
        btn.addEventListener('click', () => {
            const current = root.getAttribute('data-theme') ||
                (window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
            const next = current === 'dark' ? 'light' : 'dark';
            root.setAttribute('data-theme', next);
            try { localStorage.setItem('crosspay-theme', next); } catch (e) { /* ignore */ }
            document.dispatchEvent(new CustomEvent('crosspay:theme', { detail: next }));
        });
    }

    /* ---------- Flash messages ---------- */
    function initFlashes() {
        document.querySelectorAll('.alert[data-autodismiss]').forEach((el) => {
            setTimeout(() => { el.classList.add('is-leaving'); setTimeout(() => el.remove(), 400); }, 6000);
        });
        document.querySelectorAll('.alert .alert-close').forEach((b) => b.addEventListener('click', () => b.closest('.alert').remove()));
    }

    /* ---------- Mobile nav ---------- */
    function initNav() {
        const toggle = $('nav-toggle');
        const links = $('nav-links');
        if (!toggle || !links) return;
        toggle.addEventListener('click', () => {
            const open = links.classList.toggle('is-open');
            toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
        });
    }

    /* ---------- Payment form ---------- */
    function paymentPayload() {
        const v = (id) => ($(id) ? $(id).value : '');
        return {
            amount: v('amount'), sender_currency: v('sender_currency'), receiver_currency: v('receiver_currency'),
            sender_country: v('sender_country'), receiver_country: v('receiver_country'),
            receiver: v('receiver') || 'preview', notes: v('notes'), scenario: v('scenario')
        };
    }

    function initCurrencyConverter() {
        const amount = $('amount');
        const src = $('sender_currency');
        const tgt = $('receiver_currency');
        if (!amount || !src || !tgt) return;
        const symbol = () => { setText($('amount-currency-symbol'), (CURRENCY_SYMBOLS[src.value] || '').trim()); setText($('source-currency-label'), src.value); };
        const countryDefaults = window.CROSSPAY_COUNTRY_CURRENCY || {};
        [['sender_country', src], ['receiver_country', tgt]].forEach(([id, sel]) => {
            const c = $(id);
            if (c) c.addEventListener('change', () => { if (countryDefaults[c.value]) sel.value = countryDefaults[c.value]; symbol(); convert(); preview(); });
        });
        const convert = debounce(performConversion, 450);
        [amount, src, tgt].forEach((el) => { el.addEventListener('input', () => { symbol(); convert(); }); el.addEventListener('change', () => { symbol(); convert(); }); });
        const btn = $('btn-convert-currency');
        if (btn) btn.addEventListener('click', performConversion);
        symbol();
        performConversion();
    }

    function performConversion() {
        const amount = $('amount'), src = $('sender_currency'), tgt = $('receiver_currency');
        const loading = $('conversion-loading-indicator'), errBox = $('conversion-error-box'), details = $('conversion-details-content');
        if (!amount || !amount.value || parseFloat(amount.value) <= 0) return;
        if (loading) loading.hidden = false;
        if (errBox) errBox.hidden = true;
        const btn = $('btn-convert-currency');
        if (btn) btn.classList.add('is-busy');
        const qs = new URLSearchParams({ amount: amount.value, from: src.value, to: tgt.value });
        fetch('/api/convert_currency?' + qs.toString(), { credentials: 'same-origin' })
            .then((r) => r.json())
            .then((d) => {
                if (loading) loading.hidden = true;
                if (btn) btn.classList.remove('is-busy');
                if (!d.success) {
                    if (errBox) { errBox.hidden = false; setText($('conversion-error-text'), d.error || 'Rate unavailable.'); }
                    if (details) details.classList.add('is-dim');
                    return;
                }
                if (details) details.classList.remove('is-dim');
                setText($('display-exchange-rate'), d.exchange_rate_formatted);
                setText($('display-converted-amount'), d.formatted_converted_amount);
                setText($('display-target-currency-code'), d.target_currency + ' · ' + d.target_name);
                setText($('display-rate-provider'), d.provider);
                setText($('display-rate-timestamp'), 'Updated ' + d.last_updated + (d.stale ? ' · STALE RATE' : ''));
                setText($('display-usd-amount'), '$' + Number(d.normalized_usd_amount).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
                preview();
            })
            .catch(() => {
                if (loading) loading.hidden = true;
                if (btn) btn.classList.remove('is-busy');
                if (errBox) { errBox.hidden = false; setText($('conversion-error-text'), 'Could not reach the rate service.'); }
            });
    }

    const preview = debounce(function () {
        const box = $('risk-preview');
        if (!box || !$('amount') || !$('amount').value) return;
        box.classList.add('is-loading');
        jsonPost('/api/risk_preview', paymentPayload()).then(({ ok, data }) => {
            box.classList.remove('is-loading');
            if (!ok || !data.success) { box.dataset.level = 'unknown'; setText($('live-risk-level'), '—'); setText($('live-risk-detail'), data.error || 'Preview unavailable'); return; }
            box.dataset.level = data.level.toLowerCase();
            setText($('live-risk-level'), data.level);
            setText($('live-risk-score'), data.score.toFixed(1));
            setText($('live-decision'), data.decision);
            setText($('live-risk-detail'), (data.engine === 'model' ? 'Random Forest' : 'Fallback rules') +
                (data.feature_source === 'demo_vector' ? ' · demo vector' : ' · your account history'));
            const meter = $('live-risk-meter');
            if (meter) meter.style.setProperty('--value', Math.min(100, data.score) + '%');
        }).catch(() => box.classList.remove('is-loading'));
    }, 500);

    function initRiskPreview() {
        if (!$('risk-preview')) return;
        ['amount', 'sender_country', 'receiver_country', 'sender_currency', 'receiver_currency'].forEach((id) => {
            const el = $(id);
            if (el) { el.addEventListener('input', preview); el.addEventListener('change', preview); }
        });
    }

    const SCENARIOS = {
        low: { sender_country: 'United States', sender_currency: 'USD', receiver: 'EuroTech Industrial GmbH', receiver_country: 'Germany', receiver_currency: 'EUR', amount: '4500', notes: 'Invoice 8841 - machined steel components, 30-day terms' },
        medium: { sender_country: 'United States', sender_currency: 'USD', receiver: 'Apex Pacific Trade Corp', receiver_country: 'Brazil', receiver_currency: 'EUR', amount: '28500', notes: 'Seasonal electronics shipment, larger than usual batch' },
        high: { sender_country: 'United States', sender_currency: 'USD', receiver: 'Shadow Frontier Express', receiver_country: 'Nigeria', receiver_currency: 'INR', amount: '145000', notes: 'Offshore consulting fee, no invoice attached' }
    };

    function initScenarios() {
        document.querySelectorAll('[data-scenario]').forEach((btn) => {
            btn.addEventListener('click', () => {
                const key = btn.dataset.scenario;
                const s = SCENARIOS[key];
                if (!s) return;
                Object.entries(s).forEach(([id, val]) => { if ($(id)) $(id).value = val; });
                if ($('scenario')) $('scenario').value = key;
                const chip = $('scenario-chip');
                if (chip) { chip.hidden = false; setText($('scenario-chip-label'), 'Demo vector: ' + key.toUpperCase()); }
                document.querySelectorAll('[data-scenario]').forEach((b) => b.classList.toggle('is-active', b === btn));
                performConversion();
            });
        });
        const clear = $('scenario-clear');
        if (clear) clear.addEventListener('click', () => {
            if ($('scenario')) $('scenario').value = '';
            if ($('scenario-chip')) $('scenario-chip').hidden = true;
            document.querySelectorAll('[data-scenario]').forEach((b) => b.classList.remove('is-active'));
            preview();
        });
    }

    function initSubmitGuard() {
        document.querySelectorAll('form[data-once]').forEach((form) => {
            form.addEventListener('submit', (e) => {
                if (form.dataset.submitted === '1') { e.preventDefault(); return; }
                form.dataset.submitted = '1';
                const btn = form.querySelector('[type=submit]');
                if (btn) { btn.classList.add('is-busy'); btn.setAttribute('aria-busy', 'true'); }
            });
        });
    }

    /* ---------- Ledger verification ---------- */
    function initLedgerVerify() {
        const btn = $('btn-verify-blockchain');
        const out = $('blockchain-verify-result');
        if (!btn || !out) return;
        btn.addEventListener('click', () => {
            btn.classList.add('is-busy');
            fetch('/api/validate_chain', { credentials: 'same-origin' }).then((r) => r.json()).then((d) => {
                btn.classList.remove('is-busy');
                out.innerHTML = '';
                const div = document.createElement('div');
                div.className = 'alert ' + (d.valid ? 'alert-success' : 'alert-danger');
                const strong = document.createElement('strong');
                strong.textContent = d.valid ? 'Chain verified. ' : 'Integrity check failed. ';
                div.appendChild(strong);
                div.appendChild(document.createTextNode(d.message + (d.total_blocks !== undefined ? ' (' + d.total_blocks + ' blocks)' : '')));
                out.appendChild(div);
            }).catch(() => btn.classList.remove('is-busy'));
        });
    }

    /* ---------- AI advisory polling (rendered as plain text only) ---------- */
    function initAIPanels() {
        document.querySelectorAll('[data-ai-poll]').forEach((panel) => {
            const url = panel.dataset.aiPoll;
            let tries = 0;
            const tick = () => {
                fetch(url, { credentials: 'same-origin' }).then((r) => r.json()).then((d) => {
                    if (d.status === 'DONE' && d.result) { renderAI(panel, d.result); return; }
                    if (d.status === 'PENDING' && tries++ < 20) { setTimeout(tick, 1500); return; }
                    panel.classList.add('is-unavailable');
                    panel.classList.remove('is-loading');
                }).catch(() => { panel.classList.add('is-unavailable'); panel.classList.remove('is-loading'); });
            };
            tick();
        });
    }

    function renderAI(panel, result) {
        panel.classList.remove('is-loading');
        const target = panel.querySelector('[data-ai-body]');
        if (!target) return;
        target.innerHTML = '';
        const p = document.createElement('p');
        p.className = 'ai-summary';
        p.textContent = result.summary || '';
        target.appendChild(p);
        if (Array.isArray(result.factors) && result.factors.length) {
            const ul = document.createElement('ul');
            ul.className = 'ai-list';
            result.factors.forEach((f) => { const li = document.createElement('li'); li.textContent = f.plain_reason + ' [' + f.evidence_id + ']'; ul.appendChild(li); });
            target.appendChild(ul);
        }
        if (Array.isArray(result.what_would_lower_risk) && result.what_would_lower_risk.length) {
            const h = document.createElement('div'); h.className = 'ai-subhead'; h.textContent = 'What could lower the risk';
            target.appendChild(h);
            const ul = document.createElement('ul'); ul.className = 'ai-list';
            result.what_would_lower_risk.forEach((t) => { const li = document.createElement('li'); li.textContent = t; ul.appendChild(li); });
            target.appendChild(ul);
        }
        if (result.confidence_note) { const n = document.createElement('p'); n.className = 'ai-note'; n.textContent = result.confidence_note; target.appendChild(n); }
        panel.classList.add('is-ready');
    }

    /* ---------- SME assistant chat ---------- */
    function initAssistant() {
        const form = $('assistant-form');
        if (!form) return;
        const log = $('assistant-log');
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            const input = $('assistant-input');
            const msg = input.value.trim();
            if (!msg) return;
            appendMsg(log, 'user', msg);
            input.value = '';
            form.classList.add('is-busy');
            jsonPost(form.dataset.endpoint, { message: msg }).then(({ data }) => {
                form.classList.remove('is-busy');
                appendMsg(log, 'ai', data.answer || data.error || 'No answer available.');
            }).catch(() => { form.classList.remove('is-busy'); appendMsg(log, 'ai', 'The assistant is unavailable.'); });
        });
    }

    function appendMsg(log, who, text) {
        const div = document.createElement('div');
        div.className = 'chat-msg chat-' + who;
        div.textContent = text;
        log.appendChild(div);
        log.scrollTop = log.scrollHeight;
    }

    /* ---------- Natural-language filter ---------- */
    function initNLFilter() {
        const form = $('nlq-form');
        if (!form) return;
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            const q = $('nlq-input').value.trim();
            if (!q) return;
            form.classList.add('is-busy');
            jsonPost('/api/ai/nl_filter', { query: q }).then(({ data }) => {
                form.classList.remove('is-busy');
                if (data.success && data.query_string !== undefined) { window.location.search = data.query_string; return; }
                const out = $('nlq-error');
                if (out) { out.hidden = false; out.textContent = data.error || 'Could not understand that filter.'; }
            }).catch(() => form.classList.remove('is-busy'));
        });
    }

    document.addEventListener('DOMContentLoaded', () => {
        initTheme();
        initFlashes();
        initNav();
        initCurrencyConverter();
        initScenarios();
        initRiskPreview();
        initSubmitGuard();
        initLedgerVerify();
        initAIPanels();
        initAssistant();
        initNLFilter();
    });
})();
