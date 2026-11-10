/* Live decision feed (Server-Sent Events). Text is set with textContent only; nothing from the server is parsed as HTML. */
(function () {
    const root = document.getElementById('live-feed');
    if (!root || !window.EventSource) return;
    const list = root.querySelector('.live-list');
    const status = root.querySelector('.live-status');
    const label = root.querySelector('.live-label');
    const rateOut = root.querySelector('.live-rate-out');
    const counts = {};
    const seen = new Set();
    const stamps = [];
    const MAX_ROWS = 40;
    const icons = { APPROVED: 'check', HOLD: 'pause', BLOCKED: 'ban', REJECTED: 'x' };
    const cls = { APPROVED: 'approved', HOLD: 'hold', BLOCKED: 'blocked', REJECTED: 'rejected' };
    const riskCls = { LOW: 'low', MEDIUM: 'med', HIGH: 'high' };

    function el(tag, className, text) {
        const n = document.createElement(tag);
        if (className) n.className = className;
        if (text !== undefined && text !== null) n.textContent = text;
        return n;
    }
    function svg(name) {
        const ns = 'http://www.w3.org/2000/svg';
        const s = document.createElementNS(ns, 'svg');
        s.setAttribute('class', 'icon'); s.setAttribute('aria-hidden', 'true');
        const u = document.createElementNS(ns, 'use');
        u.setAttribute('href', '#i-' + name);
        s.appendChild(u);
        return s;
    }
    function setState(state, text) { status.dataset.state = state; label.textContent = text; }
    const fmt = new Intl.NumberFormat(undefined, { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });

    const aiByTx = new Map();
    function aiNote(text) {
        const n = el('span', 'live-ai xsmall');
        n.appendChild(svg('sparkles'));
        n.appendChild(document.createTextNode('AI · advisory: ' + text));
        return n;
    }
    function onAI(ev) {
        if (!ev.tx_id || !ev.summary) return;
        aiByTx.set(ev.tx_id, ev.summary);
        list.querySelectorAll('.live-row').forEach((li) => {
            if (li.dataset.tx === ev.tx_id && li.dataset.decision === 'HOLD' && !li.querySelector('.live-ai')) li.appendChild(aiNote(ev.summary));
        });
    }

    function render(ev, animate) {
        if (ev.type === 'ai') { onAI(ev); return; }
        if (seen.has(ev.seq)) return;
        seen.add(ev.seq);
        const empty = list.querySelector('.live-empty');
        if (empty) empty.remove();
        const li = el('li', 'live-row' + (animate ? ' is-new' : '') + (ev.simulated ? ' is-sim' : ''));
        const time = el('time', 'live-time font-mono', new Date(ev.ts).toLocaleTimeString());
        time.dateTime = new Date(ev.ts).toISOString();
        const id = ev.simulated ? el('span', 'tx-id is-sim-id', ev.tx_id) : el('a', 'tx-id', ev.tx_id);
        if (!ev.simulated) id.href = root.dataset.txUrl.replace('__TX__', encodeURIComponent(ev.tx_id));
        const meta = el('span', 'live-meta', (ev.corridor || '') + (ev.amount_usd != null ? ' · ' + fmt.format(ev.amount_usd) : ''));
        const risk = el('span', 'live-risk badge badge-' + (riskCls[ev.risk_level] || 'neutral'));
        risk.appendChild(el('span', 'dot dot-' + (riskCls[ev.risk_level] || 'neutral')));
        risk.appendChild(document.createTextNode(ev.risk_level + (ev.risk_score != null ? ' · ' + ev.risk_score : '')));
        const dec = el('span', 'live-dec badge badge-' + (cls[ev.decision] || 'neutral'));
        dec.appendChild(svg(icons[ev.decision] || 'info'));
        dec.appendChild(document.createTextNode(ev.decision));
        const tags = el('span', 'live-tags');
        if (ev.type === 'review') tags.appendChild(el('span', 'badge badge-neutral', 'officer review'));
        if (ev.block) tags.appendChild(el('span', 'badge badge-neutral', 'block #' + ev.block));
        if (ev.simulated) tags.appendChild(el('span', 'badge badge-ai', 'SIMULATED'));
        li.append(time, id, meta, risk, dec, tags);
        li.dataset.tx = ev.tx_id; li.dataset.decision = ev.decision;
        if (ev.decision === 'HOLD' && aiByTx.has(ev.tx_id)) li.appendChild(aiNote(aiByTx.get(ev.tx_id)));
        list.prepend(li);
        while (list.children.length > MAX_ROWS) list.lastElementChild.remove();
        counts[ev.decision] = (counts[ev.decision] || 0) + 1;
        const c = root.querySelector('[data-count="' + ev.decision + '"]');
        if (c) c.textContent = counts[ev.decision];
        if (animate) {
            const now = Date.now();
            stamps.push(now);
            while (stamps.length && now - stamps[0] > 10000) stamps.shift();
            rateOut.textContent = (stamps.length / 10).toFixed(1) + ' decisions/s (last 10 s)';
        }
    }

    function syncSim(sim) {
        const btn = document.getElementById('sim-toggle');
        if (!btn || !sim) return;
        btn.setAttribute('aria-pressed', sim.running ? 'true' : 'false');
        btn.classList.toggle('btn-danger', sim.running);
        btn.classList.toggle('btn-secondary', !sim.running);
        btn.querySelector('span').textContent = sim.running ? 'Stop simulated traffic' : 'Start simulated traffic';
        const rate = document.getElementById('sim-rate');
        if (rate && sim.rate_per_sec) rate.value = String(sim.rate_per_sec);
    }

    fetch(root.dataset.snapshot, { credentials: 'same-origin' })
        .then((r) => (r.ok ? r.json() : null))
        .then((data) => {
            if (!data) return;
            (data.events || []).forEach((e) => render(e, false));
            syncSim(data.simulator);
        })
        .catch(() => {});

    const source = new EventSource(root.dataset.events, { withCredentials: true });
    source.onopen = () => setState('live', 'Live');
    source.onerror = () => setState(source.readyState === EventSource.CLOSED ? 'offline' : 'connecting',
        source.readyState === EventSource.CLOSED ? 'Offline' : 'Reconnecting…');
    ['decision', 'review'].forEach((t) => source.addEventListener(t, (m) => {
        try { render(JSON.parse(m.data), true); } catch (e) { /* ignore malformed */ }
    }));
    source.addEventListener('ai', (m) => { try { onAI(JSON.parse(m.data)); } catch (e) { /* ignore malformed */ } });
    window.addEventListener('pagehide', () => source.close());

    const simUrl = root.dataset.sim;
    const btn = document.getElementById('sim-toggle');
    if (simUrl && btn) {
        const post = (body) => fetch(simUrl, {
            method: 'POST', credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
        }).then((r) => r.json()).then(syncSim).catch(() => {});
        btn.addEventListener('click', () => {
            const running = btn.getAttribute('aria-pressed') === 'true';
            post({ running: !running, rate_per_sec: Number(document.getElementById('sim-rate').value) });
        });
        document.getElementById('sim-rate').addEventListener('change', (e) => post({ rate_per_sec: Number(e.target.value) }));
    }
})();
