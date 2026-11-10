/* Live operations console. Every server value is written with textContent; nothing is parsed as HTML. */
(function () {
    const root = document.getElementById('live-ops');
    if (!root || !window.EventSource) return;
    const rowsEl = document.getElementById('ops-rows');
    const queueEl = document.getElementById('ops-queue');
    const dialog = document.getElementById('ops-trace');
    const statusEl = root.querySelector('.live-status');
    const labelEl = root.querySelector('.live-label');
    const rateEl = root.querySelector('.ops-rate');
    const totalEl = document.getElementById('ops-total');
    const MAX_ROWS = 200;
    const events = new Map();      // seq -> event
    const aiByTx = new Map();      // tx_id -> advisory one-liner
    const simCounts = {};
    const stamps = [];
    let filter = 'ALL';
    let paused = false;
    let hovering = false;
    let pending = [];
    let total = 0;

    const usd = new Intl.NumberFormat(undefined, { style: 'currency', currency: 'USD', maximumFractionDigits: 2 });
    const verdict = {
        APPROVED: ['approved', 'check', 'Approved'], HOLD: ['hold', 'pause', 'Hold'], BLOCKED: ['blocked', 'ban', 'Blocked'],
        REJECTED: ['rejected', 'x', 'Rejected'], DUPLICATE: ['neutral', 'refresh', 'Duplicate'],
    };
    const riskCls = { LOW: 'low', MEDIUM: 'med', HIGH: 'high' };

    function el(tag, cls, text) {
        const n = document.createElement(tag);
        if (cls) n.className = cls;
        if (text !== undefined && text !== null) n.textContent = String(text);
        return n;
    }
    function svg(name) {
        const ns = 'http://www.w3.org/2000/svg';
        const s = document.createElementNS(ns, 'svg');
        s.setAttribute('class', 'icon'); s.setAttribute('aria-hidden', 'true');
        const u = document.createElementNS(ns, 'use'); u.setAttribute('href', '#i-' + name); s.appendChild(u);
        return s;
    }
    function badge(ev) {
        const v = verdict[ev.decision] || ['neutral', 'info', ev.decision];
        const b = el('span', 'badge badge-' + v[0]);
        b.append(svg(v[1]), document.createTextNode(v[2]));
        return b;
    }
    function amountText(ev) {
        const parts = [ev.amount_usd != null ? usd.format(ev.amount_usd) : '–'];
        if (ev.currency && ev.currency !== 'USD' && ev.amount != null) {
            parts.push(Number(ev.amount).toLocaleString(undefined, { maximumFractionDigits: 2 }) + ' ' + ev.currency);
        }
        return parts;
    }
    function matches(ev) {
        if (filter === 'ALL') return true;
        if (filter === 'SIM') return !!ev.simulated;
        return ev.decision === filter;
    }
    function setState(state, text) { statusEl.dataset.state = state; labelEl.textContent = text; }

    function rowFor(ev) {
        const tr = el('tr', 'ops-row' + (ev.simulated ? ' is-sim' : ''));
        tr.tabIndex = 0;
        tr.dataset.seq = ev.seq;
        const tdV = el('td'); tdV.appendChild(badge(ev));
        if (ev.type === 'review') tdV.appendChild(el('span', 'badge badge-neutral ops-tag', 'officer'));
        const tdW = el('td', 'ops-why-cell');
        tdW.appendChild(el('span', 'ops-why', ev.why || ''));
        const ai = aiByTx.get(ev.tx_id);
        if (ai) tdW.appendChild(el('span', 'ops-ai-inline', 'AI · advisory: ' + ai));
        const amt = amountText(ev);
        const tdA = el('td', 'num'); tdA.appendChild(el('span', 'num', amt[0]));
        if (amt[1]) tdA.appendChild(el('span', 'xsmall muted ops-orig', amt[1]));
        const tdR = el('td');
        const r = el('span', 'badge badge-' + (riskCls[ev.risk_level] || 'neutral'));
        r.appendChild(el('span', 'dot'));
        r.appendChild(document.createTextNode((ev.risk_level || '–') + (ev.risk_score != null ? ' ' + ev.risk_score : '')));
        tdR.appendChild(r);
        const tdC = el('td', 'ops-corridor', ev.corridor || '');
        if (ev.simulated) tdC.appendChild(el('span', 'badge badge-ai ops-tag', 'SIMULATED'));
        const tdT = el('td', 'xsmall muted font-mono', new Date(ev.ts).toLocaleTimeString());
        tr.append(tdV, tdW, tdA, tdR, tdC, tdT);
        tr.addEventListener('click', () => openTrace(ev.seq));
        tr.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); openTrace(ev.seq); } });
        return tr;
    }

    function redraw() {
        rowsEl.textContent = '';
        const list = Array.from(events.values()).filter(matches).sort((a, b) => b.seq - a.seq).slice(0, MAX_ROWS);
        if (!list.length) {
            const tr = el('tr', 'ops-empty-row'); const td = el('td', 'table-empty', 'No events match this filter yet.');
            td.colSpan = 6; tr.appendChild(td); rowsEl.appendChild(tr); return;
        }
        list.forEach((ev) => rowsEl.appendChild(rowFor(ev)));
    }

    function add(ev, live) {
        if (events.has(ev.seq)) return;
        events.set(ev.seq, ev);
        if (events.size > MAX_ROWS * 2) events.delete(Math.min.apply(null, Array.from(events.keys())));
        total += 1;
        totalEl.textContent = total + ' events in this session';
        if (ev.simulated) {
            simCounts[ev.decision] = (simCounts[ev.decision] || 0) + 1;
            const s = document.querySelector('[data-kpi-sim="' + ev.decision + '"]');
            if (s) s.textContent = '+' + simCounts[ev.decision] + ' simulated in this session';
        } else if (live) {
            if (ev.decision === 'HOLD' && ev.type === 'decision') addToQueue(ev);
            if (ev.type === 'review') removeFromQueue(ev.tx_id);
        }
        if (live) {
            const now = Date.now(); stamps.push(now);
            while (stamps.length && now - stamps[0] > 10000) stamps.shift();
            rateEl.textContent = (stamps.length / 10).toFixed(1) + ' events/s over the last 10 s';
        }
        if (!matches(ev)) return;
        const empty = rowsEl.querySelector('.ops-empty-row'); if (empty) empty.remove();
        const tr = rowFor(ev); if (live) tr.classList.add('is-new');
        rowsEl.prepend(tr);
        while (rowsEl.children.length > MAX_ROWS) rowsEl.lastElementChild.remove();
    }

    function onEvent(ev) {
        if (paused || hovering) { pending.push(ev); return; }
        add(ev, true);
    }
    function flush() { const p = pending; pending = []; p.forEach((ev) => add(ev, true)); }

    function onAI(ev) {
        if (!ev.tx_id || !ev.summary) return;
        aiByTx.set(ev.tx_id, ev.summary);
        const item = queueEl && queueEl.querySelector('[data-tx="' + CSS.escape(ev.tx_id) + '"] .ops-queue-link');
        if (item && !item.querySelector('.ops-ai')) item.appendChild(aiLine(ev.summary));
        events.forEach((e) => { if (e.tx_id === ev.tx_id) { const tr = rowsEl.querySelector('[data-seq="' + e.seq + '"]'); if (tr) tr.replaceWith(rowFor(e)); } });
    }
    function aiLine(text) {
        const s = el('span', 'ops-ai'); s.appendChild(svg('sparkles'));
        s.appendChild(el('span', 'ops-ai-label', 'AI · advisory'));
        s.appendChild(document.createTextNode(' '));
        s.appendChild(el('span', null, text));
        return s;
    }

    function addToQueue(ev) {
        if (!queueEl || queueEl.querySelector('[data-tx="' + CSS.escape(ev.tx_id) + '"]')) return;
        const empty = queueEl.querySelector('.ops-empty'); if (empty) empty.remove();
        const li = el('li', 'ops-queue-item is-new'); li.dataset.tx = ev.tx_id;
        const a = el('a', 'ops-queue-link'); a.href = root.dataset.reviewUrl.replace('__TX__', encodeURIComponent(ev.tx_id));
        a.appendChild(el('span', 'ops-amount num', ev.amount_usd != null ? usd.format(ev.amount_usd) : '–'));
        a.appendChild(el('span', 'ops-why', ev.why || 'On hold'));
        const amt = amountText(ev);
        a.appendChild(el('span', 'xsmall muted', (amt[1] ? amt[1] + ' · ' : '') + (ev.corridor || '')));
        if (aiByTx.has(ev.tx_id)) a.appendChild(aiLine(aiByTx.get(ev.tx_id)));
        li.appendChild(a); queueEl.prepend(li); updateQueueCount();
    }
    function removeFromQueue(txId) {
        const li = queueEl && queueEl.querySelector('[data-tx="' + CSS.escape(txId) + '"]');
        if (li) { li.remove(); updateQueueCount(); }
    }
    function updateQueueCount() {
        const n = queueEl.querySelectorAll('.ops-queue-item').length;
        document.getElementById('queue-count').textContent = n;
        if (!n && !queueEl.querySelector('.ops-empty')) queueEl.appendChild(el('li', 'ops-empty small', 'Nothing is waiting for a decision.'));
    }

    function openTrace(seq) {
        const ev = events.get(Number(seq));
        if (!ev || !dialog) return;
        const t = ev.trace || {};
        document.getElementById('trace-sub').textContent = (ev.simulated ? 'Simulated (dry run) · ' : '') + ev.tx_id +
            ' · ' + (ev.corridor || '') + (ev.latency_ms != null ? ' · ' + ev.latency_ms + ' ms' : '');
        const steps = document.getElementById('trace-steps'); steps.textContent = '';
        const step = (title, lines, tone) => {
            const li = el('li', 'ops-step' + (tone ? ' is-' + tone : ''));
            li.appendChild(el('strong', null, title));
            const ul = el('ul', 'ops-step-lines');
            lines.filter(Boolean).forEach((l) => ul.appendChild(el('li', null, l)));
            li.appendChild(ul); steps.appendChild(li);
        };
        if (ev.decision === 'DUPLICATE') {
            step('Ingress', ['Idempotency key already used: the second copy was stopped before any decision.'], 'warn');
        } else {
            step('KYC gate', [t.kyc === 'VERIFIED' ? 'KYC verified' : 'KYC ' + (t.kyc || 'unknown') + ': payment cannot settle'],
                t.kyc === 'VERIFIED' ? 'ok' : 'bad');
            const f = t.features || {};
            step('Server-side features', Object.keys(f).map((k) => k.replace(/_/g, ' ') + ': ' + f[k]));
            const inputs = t.inputs || {};
            if (inputs.input_guard_signals && inputs.input_guard_signals.length) {
                step('Input guard (payment note)', ['Signals: ' + inputs.input_guard_signals.join(', ')], 'warn');
            }
            step('Risk score', [(ev.risk_level || '–') + ' · score ' + (ev.risk_score != null ? ev.risk_score : '–') + ' · engine ' + (ev.engine || '–')]
                .concat((t.top_factors || []).map((x) => x.label + ' (' + (x.contribution > 0 ? '+' : '') + x.contribution + ')')));
            step('Policy (' + (ev.policy_id || 'risk_pol_v1') + ')', (t.reasons && t.reasons.length)
                ? t.reasons.map((r) => r.label + ' [' + r.code + ']') : ['No rule fired: within policy'],
                ev.decision === 'APPROVED' ? 'ok' : (ev.decision === 'HOLD' ? 'warn' : 'bad'));
        }
        step('Ledger', [t.ledger || (ev.block ? 'Block #' + ev.block : 'Not recorded')]);
        if (aiByTx.has(ev.tx_id)) step('AI · advisory', [aiByTx.get(ev.tx_id)], 'ai');
        const actions = document.getElementById('trace-actions'); actions.textContent = '';
        if (!ev.simulated) {
            const a = el('a', 'btn btn-secondary btn-sm', 'Open receipt');
            a.href = root.dataset.txUrl.replace('__TX__', encodeURIComponent(ev.tx_id)); actions.appendChild(a);
            if (ev.decision === 'HOLD') {
                const r = el('a', 'btn btn-primary btn-sm', 'Review now');
                r.href = root.dataset.reviewUrl.replace('__TX__', encodeURIComponent(ev.tx_id)); actions.appendChild(r);
            }
        }
        if (typeof dialog.showModal === 'function') dialog.showModal(); else dialog.setAttribute('open', '');
    }
    if (dialog) {
        dialog.querySelector('[data-close-trace]').addEventListener('click', () => dialog.close());
        dialog.addEventListener('click', (e) => { if (e.target === dialog) dialog.close(); });
    }

    function refreshStats() {
        fetch(root.dataset.stats, { credentials: 'same-origin' }).then((r) => (r.ok ? r.json() : null)).then((s) => {
            if (!s) return;
            const set = (k, v) => { const n = document.querySelector('[data-kpi="' + k + '"]'); if (n) n.textContent = v; };
            set('hold', s.hold); set('blocked', s.blocked); set('rejected', s.rejected);
            set('approval_rate', s.approval_rate != null ? s.approval_rate + '%' : '–');
            set('p95_ms', s.p95_ms != null ? s.p95_ms + ' ms' : (s.sim_p95_ms != null ? s.sim_p95_ms + ' ms' : '–'));
            const d = document.querySelector('[data-kpi-sub="decided"]'); if (d) d.textContent = 'of ' + s.decided + ' decided payments';
            const p = document.querySelector('[data-kpi-sub="p95"]');
            if (p) p.textContent = s.p95_ms != null ? 'real decisions, ' + s.p95_samples + ' samples'
                : (s.sim_p95_ms != null ? 'simulated only, ' + s.sim_p95_samples + ' samples' : 'no decisions measured yet');
        }).catch(() => {});
    }
    let statsTimer = null;
    const throttledStats = () => { if (statsTimer) return; statsTimer = setTimeout(() => { statsTimer = null; refreshStats(); }, 1500); };

    document.getElementById('ops-filters').addEventListener('click', (e) => {
        const b = e.target.closest('[data-filter]'); if (!b) return;
        filter = b.dataset.filter;
        document.querySelectorAll('#ops-filters [data-filter]').forEach((x) => x.setAttribute('aria-selected', x === b ? 'true' : 'false'));
        redraw();
    });
    const tableWrap = document.querySelector('.ops-table-wrap');
    tableWrap.addEventListener('mouseenter', () => { hovering = true; });
    tableWrap.addEventListener('mouseleave', () => { hovering = false; if (!paused) flush(); });
    const pauseBtn = document.getElementById('ops-pause');
    pauseBtn.addEventListener('click', () => {
        paused = !paused;
        pauseBtn.setAttribute('aria-pressed', paused ? 'true' : 'false');
        pauseBtn.querySelector('span').textContent = paused ? 'Resume stream (' + pending.length + ' waiting)' : 'Pause stream';
        if (!paused) flush();
    });

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
    const simUrl = root.dataset.sim;
    const simBtn = document.getElementById('sim-toggle');
    if (simUrl && simBtn) {
        const post = (body) => fetch(simUrl, {
            method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
        }).then((r) => r.json()).then(syncSim).catch(() => {});
        simBtn.addEventListener('click', () => {
            const running = simBtn.getAttribute('aria-pressed') === 'true';
            post({ running: !running, rate_per_sec: Number(document.getElementById('sim-rate').value) });
        });
        document.getElementById('sim-rate').addEventListener('change', (e) => post({ rate_per_sec: Number(e.target.value) }));
    }

    refreshStats();
    fetch(root.dataset.snapshot, { credentials: 'same-origin' }).then((r) => (r.ok ? r.json() : null)).then((data) => {
        if (!data) return;
        (data.events || []).forEach((e) => { if (e.type === 'ai') onAI(e); else add(e, false); });
        syncSim(data.simulator);
    }).catch(() => {});

    const source = new EventSource(root.dataset.events, { withCredentials: true });
    source.onopen = () => setState('live', 'Stream connected');
    source.onerror = () => setState(source.readyState === EventSource.CLOSED ? 'offline' : 'connecting',
        source.readyState === EventSource.CLOSED ? 'Offline' : 'Reconnecting…');
    ['decision', 'review'].forEach((t) => source.addEventListener(t, (m) => {
        try { onEvent(JSON.parse(m.data)); throttledStats(); } catch (e) { /* ignore malformed */ }
    }));
    source.addEventListener('ai', (m) => { try { onAI(JSON.parse(m.data)); } catch (e) { /* ignore */ } });
    window.addEventListener('pagehide', () => source.close());
})();
