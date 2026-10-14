/* Simba Data Lake Admin Portal — front end.
 * Data arrives from /api/snapshot once, then live via Server-Sent Events (/api/stream).
 * All dynamic text is inserted with textContent (see h()), never innerHTML.
 */
(() => {
  'use strict';

  const state = {
    config: null,
    content: null,
    sections: {},
    meta: null,
    version: 0,
    route: 'home',
    page: null,
    transport: 'connecting', // connecting | stream | polling | expired
    ui: {
      layerSchema: 'all', layerSearch: '', selectedTable: null,
      sampleTable: null, sampleCache: {},
      topicSearch: '', topicStatus: '',
      lineageTable: null, lineageSearch: '', columnLineage: {},
      grantSearch: '', grantType: '', grantSecurable: '', grantPrivilege: '', grantPath: '',
      dictSearch: '', dictSchema: 'all',
    },
  };

  // ------------------------------------------------------------------ icons
  const ICON_PATHS = {
    home: 'M3 11l9-8 9 8v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z',
    arch: 'M4 6h6v5H4zM14 6h6v5h-6zM9 15h6v5H9zM7 11v2h10v-2M12 13v2',
    layers: 'M12 3l9 5-9 5-9-5zM3 13l9 5 9-5M3 17l9 5 9-5',
    table: 'M3 5h18v14H3zM3 10h18M3 15h18M9 5v14',
    kafka: 'M13 2L4 14h7l-1 8 9-12h-7z',
    lineage: 'M6 6m-2 0a2 2 0 1 0 4 0a2 2 0 1 0-4 0M18 6m-2 0a2 2 0 1 0 4 0a2 2 0 1 0-4 0M18 18m-2 0a2 2 0 1 0 4 0a2 2 0 1 0-4 0M8 6h8M7 8l9 8',
    shield: 'M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z M9 12l2 2 4-4',
    book: 'M4 4h7a3 3 0 0 1 3 3v13a2 2 0 0 0-2-2H4zM20 4h-5a3 3 0 0 0-3 3v13a2 2 0 0 1 2-2h6z',
    road: 'M4 7h10l3 3-3 3H4zM10 13v8M10 3v4',
    request: 'M8 11V7a4 4 0 0 1 8 0v4M5 11h14v10H5zM12 15v2',
    help: 'M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0-18 0M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6V14M12 17h.01',
    chart: 'M4 20V10M10 20V4M16 20v-7M22 20H2',
    bolt: 'M13 2L4 14h7l-1 8 9-12h-7z',
    users: 'M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM2 21v-1a6 6 0 0 1 12 0v1M16 3.5a4 4 0 0 1 0 7.5M18 21v-1a6 6 0 0 0-3-5.2',
    database: 'M12 3c4.4 0 8 1.3 8 3s-3.6 3-8 3-8-1.3-8-3 3.6-3 8-3zM4 6v6c0 1.7 3.6 3 8 3s8-1.3 8-3V6M4 12v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6',
    spark: 'M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9zM19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z',
    trend: 'M3 17l6-6 4 4 8-8M15 7h6v6',
    arrow: 'M5 12h14M13 6l6 6-6 6',
  };

  // Focused navigation requested for the SIMBA POC. Sample preview is opened from Data Layers.
  const PAGES = [
    { id: 'home', label: 'Overview', icon: 'home', group: 'Workspace' },
    { id: 'architecture', label: 'Architecture', icon: 'arch', group: 'Workspace' },
    { id: 'layers', label: 'Data Layers', icon: 'layers', group: 'Data platform' },
    { id: 'kafka', label: 'Kafka Events', icon: 'kafka' },
    { id: 'governance', label: 'Security & Governance', icon: 'shield', group: 'Governance' },
    { id: 'talk-data', label: 'Talk to Data', icon: 'chart', group: 'Workspace' },
  ];

  // ------------------------------------------------------------------ DOM helpers
  function h(tag, attrs, ...kids) {
    const el = document.createElement(tag);
    if (attrs) {
      for (const [k, v] of Object.entries(attrs)) {
        if (v === null || v === undefined || v === false) continue;
        if (k === 'class') el.className = v;
        else if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2), v);
        else if (k === 'value') el.value = v;
        else el.setAttribute(k, v === true ? '' : String(v));
      }
    }
    for (const kid of kids.flat(Infinity)) {
      if (kid === null || kid === undefined || kid === false) continue;
      el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
    }
    return el;
  }

  function icon(name) {
    const NS = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('aria-hidden', 'true');
    const path = document.createElementNS(NS, 'path');
    path.setAttribute('d', ICON_PATHS[name] || ICON_PATHS.help);
    svg.append(path);
    return svg;
  }

  const pill = (text, kind) => h('span', { class: `pill ${kind || ''}` }, text);
  const NA = '—';

  function fmtNum(n) {
    if (n === null || n === undefined || Number.isNaN(Number(n))) return NA;
    return Number(n).toLocaleString();
  }
  function fmtTime(iso) {
    if (!iso) return NA;
    const d = new Date(iso);
    return Number.isNaN(d.getTime()) ? String(iso) : d.toLocaleString();
  }
  function ago(iso) {
    if (!iso) return NA;
    const t = new Date(iso).getTime();
    if (Number.isNaN(t)) return String(iso);
    const s = Math.max(0, Math.round((Date.now() - t) / 1000));
    if (s < 60) return `${s}s ago`;
    if (s < 3600) return `${Math.round(s / 60)} min ago`;
    if (s < 86400) return `${Math.round(s / 3600)} h ago`;
    return `${Math.round(s / 86400)} d ago`;
  }
  function ageSeconds(iso) {
    const t = iso ? new Date(iso).getTime() : NaN;
    return Number.isNaN(t) ? Infinity : (Date.now() - t) / 1000;
  }
  function safeUrl(url) {
    try {
      const u = new URL(url, window.location.href);
      return ['http:', 'https:', 'mailto:'].includes(u.protocol) ? u.href : null;
    } catch { return null; }
  }
  const shortName = (full) => (full || '').split('.').slice(1).join('.') || full;
  const contains = (hay, q) => !q || String(hay).toLowerCase().includes(q.toLowerCase());

  // ------------------------------------------------------------------ data accessors
  const sec = (name) => state.sections[name] || null;
  const tables = () => (sec('layers') && sec('layers').tables) || [];
  const topics = () => (sec('kafka') && sec('kafka').topics) || [];
  const edges = () => (sec('lineage') && sec('lineage').edges) || [];
  const grants = () => (sec('governance') && sec('governance').grants) || [];

  function sectionNotice(name, label) {
    const meta = state.meta && state.meta.sections && state.meta.sections[name];
    if (!meta) return null;
    if (meta.ok === false) {
      const hasData = !!sec(name);
      return h('div', { class: hasData ? 'stale' : 'error-box' },
        hasData
          ? `Could not refresh ${label} (${meta.error}). Showing values last updated ${ago(meta.updated_at)}.`
          : `Could not load ${label}: ${meta.error}`);
    }
    if (meta.ok === null) return h('div', { class: 'stale' }, `Loading ${label}…`);
    return null;
  }

  function layerStats(schema) {
    const list = tables().filter((t) => t.schema === schema);
    const counted = list.filter((t) => t.row_count !== null && t.row_count !== undefined);
    return {
      tables: list.length,
      rows: counted.length ? counted.reduce((a, t) => a + Number(t.row_count), 0) : null,
    };
  }

  // ------------------------------------------------------------------ shared widgets
  // SIMBA count-up animation v1
  function animateMetricValue(node, value) {
    const raw = String(value ?? '');
    const match = raw.match(/^([\s]*)([\d,]+)(.*)$/);
    if (!match || window.matchMedia('(prefers-reduced-motion: reduce)').matches) { node.textContent = raw; return; }
    const prefix = match[1], target = Number(match[2].replace(/,/g, '')), suffix = match[3];
    if (!Number.isFinite(target) || target > 1000000000) { node.textContent = raw; return; }
    const start = performance.now(), duration = 650;
    node.textContent = prefix + '0' + suffix;
    function frame(now) {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      node.textContent = prefix + Math.round(target * eased).toLocaleString() + suffix;
      if (t < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }

  function metric(label, value, hint, key) {
    const num = h('div', { class: 'num' }, '');
    animateMetricValue(num, value);
    const el = h('div', { class: 'metric' }, h('div', { class: 'label' }, label), num, hint ? h('div', { class: 'hint' }, hint) : null);
    if (key) {
      const prev = metric.prev[key];
      if (prev !== undefined && prev !== value) el.classList.add('flash');
      metric.prev[key] = value;
    }
    return el;
  }
  metric.prev = {};

  function head(title, desc, ...right) {
    return h('div', { class: 'head' }, h('div', null, h('h1', null, title), desc ? h('p', null, desc) : null), right.length ? h('div', { class: 'actions' }, right) : null);
  }

  function panel(title, sub, right, ...body) {
    return h('section', { class: 'panel' },
      h('div', { class: 'panelhead' }, h('div', null, h('h2', null, title), sub ? h('div', { class: 'sub' }, sub) : null), right || null),
      body);
  }

  function dataTable(columns, rows, emptyText, onRow) {
    const thead = h('thead', null, h('tr', null, columns.map((c) => h('th', { class: c.num ? 'num' : null }, c.label))));
    const tbody = h('tbody');
    if (!rows.length) {
      tbody.append(h('tr', null, h('td', { colspan: columns.length, class: 'empty' }, emptyText || 'No records')));
    } else {
      for (const row of rows) {
        const tr = h('tr', onRow ? { class: 'clickable', tabindex: 0, onclick: () => onRow(row), onkeydown: (e) => { if (e.key === 'Enter') onRow(row); } } : null,
          columns.map((c) => {
            const v = c.render ? c.render(row) : row[c.key];
            return h('td', { class: c.num ? 'num' : null }, v === null || v === undefined || v === '' ? NA : v);
          }));
        tbody.append(tr);
      }
    }
    return h('div', { class: 'tablewrap' }, h('table', null, thead, tbody));
  }

  function select(options, value, onChange, label) {
    const el = h('select', { class: 'field', 'aria-label': label, onchange: (e) => onChange(e.target.value) },
      options.map(([v, text]) => h('option', { value: v }, text)));
    el.value = value;
    return el;
  }

  function search(placeholder, value, onInput) {
    return h('input', { class: 'field search', type: 'search', placeholder, value, 'aria-label': placeholder, oninput: (e) => onInput(e.target.value) });
  }

  /** A page region that re-renders on data updates while controls above it keep focus. */
  function region(renderFn) {
    const el = h('div');
    const update = (force) => {
      // Don't rebuild under the user's cursor (e.g. an open <select>); the next update catches up.
      const active = document.activeElement;
      if (!force && active && el.contains(active) && /^(INPUT|SELECT|TEXTAREA)$/.test(active.tagName)) return;
      el.replaceChildren(...[renderFn()].flat(Infinity).filter(Boolean));
    };
    return { el, update };
  }

  function requestButtons(compact) {
    const links = (state.config && state.config.links) || {};
    const mail = links.support_email ? `mailto:${links.support_email}` : null;
    const items = [
      ['Request access', links.request_access, true],
      ['Request dataset', links.request_dataset, false],
      ['Contact data team', mail, false],
    ];
    if (!compact) items.push(['UBA service portal', links.service_portal, false]);
    return h('div', { class: 'cta' }, items.map(([label, url, primary]) => {
      const href = url ? safeUrl(url) : null;
      return href
        ? h('a', { class: `btn ${primary ? 'primary' : ''}`, href, target: href.startsWith('mailto:') ? null : '_blank', rel: 'noopener noreferrer' }, label)
        : h('span', { class: 'btn', 'aria-disabled': 'true', title: 'Link not configured yet' }, label);
    }));
  }

  function topicStatus(t) {
    if ((t.events_24h || 0) > 0) return pill('Active · 24h', 'good');
    if (ageSeconds(t.last_event_at) < 7 * 86400) return pill('Idle < 7d', 'warn');
    return pill('Idle', '');
  }

  function runPill(run) {
    if (run.result_state === 'SUCCESS') return pill('Succeeded', 'good');
    if (run.result_state) return pill(run.result_state.toLowerCase().replace(/_/g, ' '), 'bad');
    if (run.life_cycle_state === 'RUNNING') return pill('Running', 'good');
    return pill((run.life_cycle_state || 'Unknown').toLowerCase(), 'warn');
  }

  // ------------------------------------------------------------------ pages
  const Pages = {};


  Pages.home = () => {
    const c = state.content;
    const about = c.about;
    const hero = h('section', { class: 'ov-hero' },
      h('div', { class: 'ov-hero-copy' },
        h('span', { class: 'ov-kicker' }, about.kicker),
        h('h1', null, about.tagline),
        h('p', null, about.body),
        h('div', { class: 'ov-actions' },
          h('a', { class: 'ov-btn primary', href: '#/architecture' }, 'Explore the architecture', icon('arrow')),
          h('a', { class: 'ov-btn', href: '#/layers' }, 'Browse data layers'))),
      h('blockquote', { class: 'ov-quote' }, h('p', null, `“${about.quote}”`), h('cite', null, about.quote_by)),
      h('span', { class: 'ov-credit' }, 'Photo: NASA · Unsplash'));

    const benefits = h('section', { class: 'ov-benefits' },
      h('div', { class: 'ov-section-head' }, h('h2', null, c.benefits.heading), h('p', null, c.benefits.summary)),
      h('div', { class: 'ov-benefit-grid' }, c.benefits.items.map((b) => h('article', { class: 'ov-benefit' },
        h('span', { class: 'ov-benefit-icon' }, icon(b.icon)),
        h('h3', null, b.title),
        h('p', null, b.body)))));

    const kpis = region(() => {
      const k = sec('kafka');
      const allRows = state.config.layer_schemas.map(layerStats).map((s) => s.rows).filter((r) => r !== null);
      const tp = topics();
      return h('div', { class: 'grid g4' },
        metric('Datasets in catalog', sec('layers') ? fmtNum(tables().length) : NA, `${state.config.catalog} · ${state.config.layer_schemas.join(' / ')}`, 'datasets'),
        metric('Rows across layers', allRows.length ? fmtNum(allRows.reduce((a, b) => a + b, 0)) : NA, 'COUNT(*) on tables (views excluded)', 'rows'),
        metric('Kafka events · 24h', k ? fmtNum(tp.reduce((a, t) => a + (t.events_24h || 0), 0)) : NA, k ? `${tp.filter((t) => t.events_24h > 0).length} of ${tp.length} topics active` : 'Kafka table not loaded', 'events'),
        metric('Last event received', k ? ago(k.last_event_at) : NA, k ? `Ingested ${ago(k.last_ingested_at)}` : '', null));
    });
const layersRegion = region(() => layerCards(true));
    const layersPanel = panel('Data layers', 'A medallion architecture to ensure data quality, governance and trust.', h('a', { class: 'linkbtn', href: '#/layers' }, 'Browse layers →'), layersRegion.el);

    const activityPanel = panel('Kafka events', 'Explore the Plumery topic inventory and ingestion activity.',
      h('a', { class: 'linkbtn', href: '#/kafka' }, 'Explore events →'),
      h('div', { class: 'feature-summary' }, h('span', { class: 'feature-summary-icon' }, '↯'), h('div', null,
        h('b', null, 'Event activity at a glance'), h('p', null, 'Review topics, event volume and the latest activity available in the Bronze events table.'))));
    const governancePanel = panel('Security & Governance', 'Keep data access visible and controlled.',
      h('a', { class: 'linkbtn', href: '#/governance' }, 'Review governance →'),
      h('div', { class: 'feature-summary' }, h('span', { class: 'feature-summary-icon' }, '◇'), h('div', null,
        h('b', null, 'Access with accountability'), h('p', null, 'Review verified catalog grants and approved identity access when the live adapter is configured.'))));

    const el = h('div', null, hero, kpis.el, benefits,
      h('div', { class: 'grid' }, layersPanel),
      h('div', { class: 'grid g2' }, activityPanel, governancePanel));
    return { el, update: () => { kpis.update(); layersRegion.update(); } };
  };

  function architectureFlow(compact) {
    const stages = state.content.architecture.stages;
    return h('div', { class: 'flow' }, stages.map((stage, i) => {
      const isLake = i === 2;
      const items = stage.items.map((it) => h('div', { class: 'stage-item' },
        h('b', null, it.name), h('span', null, it.detail),
        !compact && it.status ? h('div', null, pill(it.status, it.status === 'Planned' ? '' : 'warn')) : null));
      return h('div', { class: 'stage' }, h('h3', null, stage.name), isLake ? h('div', { class: 'lake-layers' }, items) : items);
    }));
  }

  function layerCards(clickable) {
    return h('div', { class: 'grid g3' }, state.content.layers.map((l) => {
      const s = layerStats(l.schema);
      const stat = sec('layers') ? `${fmtNum(s.tables)} dataset${s.tables === 1 ? '' : 's'} · ${s.rows === null ? 'rows n/a' : `${fmtNum(s.rows)} rows`}` : 'Inventory not loaded';
      return h('div', {
        class: `layer ${clickable ? 'clickable' : ''}`,
        onclick: clickable ? () => { state.ui.layerSchema = l.schema; location.hash = '#/layers'; } : null,
      },
      h('div', { class: 'layer-head' }, h('span', { class: `layer-icon ${l.schema}` }), h('div', null, h('h3', null, l.name))),
      h('div', { class: 'stat' }, stat));
    }));
  }

  function roadmapList(items) {
    return h('ol', { class: 'timeline' }, items.map((r, i) => h('li', null,
      h('span', { class: 'step' }, i + 1),
      h('div', null, h('b', null, r.title), h('span', { class: 'muted' }, r.detail)),
      h('div', null, pill(r.status, r.status === 'In progress' ? 'warn' : r.status === 'Done' ? 'good' : ''), r.target ? h('div', { class: 'muted' }, `Target: ${r.target}`) : null))));
  }

  Pages.architecture = () => {
    const status = region(() => {
      const k = sec('kafka');
      const p = sec('pipelines');
      const anyOk = state.meta && Object.values(state.meta.sections).some((m) => m.ok);
      const lag = k ? ageSeconds(k.last_ingested_at) : Infinity;
      return [
        h('div', { class: 'statusrow' }, h('span', null, h('b', null, 'Databricks SQL Warehouse'), h('div', { class: 'muted' }, state.meta && state.meta.mode === 'demo' ? 'Sample data — not connected' : 'Queried by the portal server')),
          state.meta && state.meta.mode === 'demo' ? pill('Sample data', 'warn') : pill(anyOk ? 'Connected' : 'Not connected', anyOk ? 'good' : 'bad')),
        h('div', { class: 'statusrow' }, h('span', null, h('b', null, 'Kafka → Bronze stream'), h('div', { class: 'muted' }, k ? `Last ingested ${ago(k.last_ingested_at)} into ${k.source_table}` : 'Kafka events table not available')),
          k ? pill(lag < 600 ? 'Flowing' : lag < 86400 ? 'Delayed' : 'Stalled', lag < 600 ? 'good' : lag < 86400 ? 'warn' : 'bad') : pill('Unknown')),
        sectionNotice('pipelines', 'job runs'),
        p && p.runs && p.runs.length
          ? p.runs.map((r) => h('div', { class: 'statusrow' }, h('span', null, h('b', null, r.run_name || `Job ${r.job_id}`), h('div', { class: 'muted' }, `Started ${fmtTime(r.start_time)}`)), runPill(r)))
          : h('div', { class: 'muted' }, (p && p.note) || 'No job runs to show.'),
      ];
    });
    const diagramSrc = '/static/images/simba-architecture.png';
    const diagram = h('figure', { class: 'architecture-figure' },
      h('a', { href: diagramSrc, target: '_blank', rel: 'noopener', title: 'Open full-size diagram' },
        h('img', { src: diagramSrc, width: 1571, height: 545, alt: 'SIMBA architecture: RedApp PostgreSQL, Plumery PostgreSQL and Kafka events are ingested through a Kafka connector, JDBC and Databricks Workflows into Databricks Bronze, Silver and Gold layers. Unity Catalog provides governance, access control, lineage and audit. Data is served through Databricks SQL to Power BI semantic models, KPIs, reports and dashboards.' })),
      h('figcaption', null, 'Target reference architecture. Unity Catalog spans the lakehouse for governance, access control, lineage and audit. Select the diagram to open it full size.'));
    const el = h('div', { class: 'architecture-page' },
      head('SIMBA data platform architecture', 'End-to-end flow from source systems to governed analytics across DEV, UAT and PROD.'),
      panel('Architecture diagram', 'Source systems → ingestion → lakehouse → analytics and reporting.', null, diagram),
      panel('End-to-end data flow', 'Component stages and statuses are maintained by the project team in content/portal.json.', null, architectureFlow(false)),
      panel('Live platform status', 'Connectivity and job status are reported separately from the target architecture.', null, status.el));
    return { el, update: status.update };
  };

  Pages.layers = () => {
    const ui = state.ui;
    const schemas = ['all'].concat(state.config.layer_schemas);
    const tabs = h('div', { class: 'tabs', role: 'tablist' }, schemas.map((s) => h('button', {
      class: `tab ${ui.layerSchema === s ? 'active' : ''}`, role: 'tab', 'aria-selected': ui.layerSchema === s ? 'true' : 'false',
      onclick: (e) => { ui.layerSchema = s; tabs.querySelectorAll('.tab').forEach((b) => { b.classList.remove('active'); b.setAttribute('aria-selected', 'false'); }); e.currentTarget.classList.add('active'); e.currentTarget.setAttribute('aria-selected', 'true'); list.update(); },
    }, s === 'all' ? 'All layers' : s[0].toUpperCase() + s.slice(1))));

    const cards = region(() => layerCards(false));
    const list = region(() => {
      const rows = tables().filter((t) => (ui.layerSchema === 'all' || t.schema === ui.layerSchema)
        && contains(`${t.full_name} ${t.comment || ''} ${t.columns.map((c) => c.name).join(' ')}`, ui.layerSearch));
      return [
        sectionNotice('layers', 'table inventory'),
        dataTable([
          { label: 'Dataset', render: (t) => h('div', null, h('b', null, t.name), t.comment ? h('div', { class: 'muted' }, t.comment) : null) },
          { label: 'Layer', key: 'schema' },
          { label: 'Type', render: (t) => `${t.type || ''}${t.format ? ` · ${t.format}` : ''}` },
          { label: 'Rows', num: true, render: (t) => fmtNum(t.row_count) },
          { label: 'Last write', render: (t) => (t.last_write ? ago(t.last_write.timestamp) : ago(t.last_altered_at)) },
          { label: 'Downstream', num: true, render: (t) => fmtNum(edges().filter((e) => e.source === t.full_name).length) },
        ], rows, sec('layers') ? 'No matching datasets' : 'Inventory not loaded yet', (t) => { ui.selectedTable = t.full_name; detail.update(); detail.el.scrollIntoView({ behavior: 'smooth', block: 'start' }); }),
        h('div', { class: 'footnote' }, 'Row counts come from COUNT(*) and last write from DESCRIBE HISTORY, refreshed every few minutes. Click a dataset for its schema and consumers.'),
      ];
    });

    const detail = region(() => {
      const t = tables().find((x) => x.full_name === ui.selectedTable);
      if (!t) return null;
      const up = edges().filter((e) => e.target === t.full_name);
      const down = edges().filter((e) => e.source === t.full_name);
      const canSample = state.config.sample_tables.includes(t.full_name);
      return panel(t.full_name, t.comment || 'No description in Unity Catalog', h('div', { class: 'actions' },
        canSample ? h('button', { class: 'btn primary', onclick: () => { ui.sampleTable = t.full_name; location.hash = '#/sample'; } }, 'Preview sample rows ↗') : h('span', { class: 'muted' }, 'Sample preview is available only for approved tables.'),
        h('button', { class: 'btn', onclick: () => { ui.selectedTable = null; detail.update(); } }, 'Close')),
      h('div', { class: 'kv' },
        h('div', null, h('b', null, fmtNum(t.row_count)), h('span', null, 'Rows')),
        h('div', null, h('b', null, t.last_write ? fmtTime(t.last_write.timestamp) : fmtTime(t.last_altered_at)), h('span', null, t.last_write ? `Last ${t.last_write.operation || 'write'}` : 'Last altered')),
        h('div', null, h('b', null, t.columns.length), h('span', null, 'Columns')),
        h('div', null, h('b', null, t.owner || NA), h('span', null, 'Owner'))),
      h('div', { class: 'grid g2' },
        h('div', null, h('h3', null, 'Schema'), dataTable([
          { label: 'Column', render: (c) => h('code', null, c.name) },
          { label: 'Type', key: 'type' },
          { label: 'Nullable', render: (c) => (c.nullable ? 'Yes' : 'No') },
          { label: 'Comment', key: 'comment' },
        ], t.columns, 'No columns visible')),
        h('div', null,
          h('h3', null, 'Upstream sources'), up.length ? up.map((e) => h('div', { class: 'node' }, shortName(e.source), h('small', null, e.entity_type))) : h('div', { class: 'muted' }, 'None recorded'),
          h('h3', null, 'Downstream consumers'), down.length ? down.map((e) => h('div', { class: 'node' }, shortName(e.target || '') || e.entity_type, h('small', null, e.entity_type))) : h('div', { class: 'muted' }, 'None recorded'))));
    });

    const el = h('div', null,
      head('Data layers', 'Inspect Bronze, Silver and Gold datasets, their schemas, row counts, last processing and downstream consumers.'),
      cards.el,
      panel('Datasets', `Unity Catalog · ${state.config.catalog}`, null,
        h('div', { class: 'toolbar' }, tabs, search('Search dataset or column…', ui.layerSearch, (v) => { ui.layerSearch = v; list.update(); })),
        list.el),
      detail.el);
    return { el, update: () => { cards.update(); list.update(); detail.update(); } };
  };

  Pages.sample = () => {
    const ui = state.ui;
    const options = state.config.sample_tables;
    if (!ui.sampleTable && options.length) ui.sampleTable = options[0];
    const body = h('div');

    async function load(table) {
      ui.sampleTable = table;
      if (!table) return;
      if (!ui.sampleCache[table]) {
        body.replaceChildren(h('div', { class: 'empty' }, 'Loading sample…'));
        try {
          ui.sampleCache[table] = await api(`/api/sample?table=${encodeURIComponent(table)}`);
        } catch (err) {
          body.replaceChildren(h('div', { class: 'error-box' }, err.message));
          return;
        }
      }
      const data = ui.sampleCache[table];
      body.replaceChildren(
        data.masked_columns && data.masked_columns.length ? h('div', { class: 'stale' }, `Masked by the portal: ${data.masked_columns.join(', ')}`) : null,
        dataTable(data.columns.map((c) => ({ label: c, render: (r) => (r[c] === null || r[c] === undefined ? NA : String(r[c])) })), data.rows, 'The table is empty'),
        h('div', { class: 'footnote' }, `Showing up to ${state.config.sample_row_limit} rows. Sample tables should be approved, masked Unity Catalog views.`));
    }

    const el = h('div', null,
      head('Sample data explorer', 'A small preview of approved datasets to understand structure and values.'),
      options.length
        ? panel('Sample records', 'Only tables on the approved allowlist (SIMBA_SAMPLE_TABLES) can be previewed.',
          select(options.map((t) => [t, shortName(t)]), ui.sampleTable, load, 'Sample table'), body)
        : panel('Sample records', null, null, h('div', { class: 'empty' }, 'No sample tables are approved yet. Add masked views to SIMBA_SAMPLE_TABLES on the server.')),
      panel('Datasets awaiting ingestion', 'Requested from source teams; not yet available.', null,
        dataTable([{ label: 'Dataset', key: 'name' }, { label: 'Source', key: 'source' }, { label: 'Status', render: (d) => pill(d.status, 'warn') }], state.content.planned_datasets)));
    load(ui.sampleTable);
    return { el, update: () => {} };
  };

  Pages.kafka = () => {
    const ui = state.ui;
    const kpis = region(() => {
      const k = sec('kafka');
      const tp = topics();
      return h('div', { class: 'grid g4' },
        metric('Topics with events', k ? fmtNum(tp.length) : NA, 'Seen in the Bronze events table', 'k-topics'),
        metric('Active in last 24h', k ? fmtNum(tp.filter((t) => t.events_24h > 0).length) : NA, null, 'k-active'),
        metric('Events · 24h', k ? fmtNum(tp.reduce((a, t) => a + (t.events_24h || 0), 0)) : NA, null, 'k-events'),
        metric('Last ingested', k ? ago(k.last_ingested_at) : NA, k ? `Latest event ${ago(k.last_event_at)}` : null, null));
    });
    const list = region(() => {
      const rows = topics().filter((t) => contains(t.topic, ui.topicSearch)
        && (!ui.topicStatus || (ui.topicStatus === 'active' ? t.events_24h > 0 : !(t.events_24h > 0))));
      const k = sec('kafka');
      return [
        sectionNotice('kafka', 'Kafka activity'),
        dataTable([
          { label: 'Category', render: (t) => t.topic.split('.')[0] },
          { label: 'Topic', render: (t) => h('code', null, t.topic) },
          { label: 'Events 24h', num: true, render: (t) => fmtNum(t.events_24h) },
          { label: 'Events total', num: true, render: (t) => fmtNum(t.events_total) },
          { label: 'Partitions', num: true, render: (t) => fmtNum(t.partitions) },
          { label: 'Last event', render: (t) => ago(t.last_event_at) },
          { label: 'Status', render: topicStatus },
        ], rows, k ? 'No matching topics' : 'Kafka events table not loaded'),
        h('div', { class: 'footnote' }, `${rows.length} of ${topics().length} topics shown. ${k ? k.note : ''} Source: ${k ? k.source_table : state.config.kafka_events_table}.`),
      ];
    });
    const el = h('div', null,
      head('Kafka events', `Live activity of Plumery Kafka topics as landed in Bronze. Updates automatically every ~${state.config.fast_refresh_seconds}s.`),
      kpis.el,
      panel('Topic activity', null, null,
        h('div', { class: 'toolbar' },
          search('Search topic…', ui.topicSearch, (v) => { ui.topicSearch = v; list.update(); }),
          select([['', 'All statuses'], ['active', 'Active in 24h'], ['idle', 'Idle in 24h']], ui.topicStatus, (v) => { ui.topicStatus = v; list.update(); }, 'Topic status')),
        list.el));
    return { el, update: () => { kpis.update(); list.update(); } };
  };

  Pages.lineage = () => {
    const ui = state.ui;
    const allTables = () => {
      const names = new Set(tables().map((t) => t.full_name));
      edges().forEach((e) => { if (e.source) names.add(e.source); if (e.target) names.add(e.target); });
      return [...names].sort();
    };
    const graph = region(() => {
      const names = allTables();
      if (!ui.lineageTable || !names.includes(ui.lineageTable)) ui.lineageTable = names[0] || null;
      if (!ui.lineageTable) return h('div', { class: 'empty' }, 'No tables or lineage available yet.');
      const center = ui.lineageTable;
      const up = edges().filter((e) => e.target === center);
      const down = edges().filter((e) => e.source === center);
      const node = (name, sub) => h('button', { class: 'node', onclick: () => { if (name) { ui.lineageTable = name; graph.update(); colRegion.update(); } } }, shortName(name || '') || sub, h('small', null, sub));
      return [
        h('div', { class: 'toolbar' }, select(names.map((n) => [n, shortName(n)]), center, (v) => { ui.lineageTable = v; graph.update(true); colRegion.update(true); }, 'Table')),
        h('div', { class: 'lineage-flow' },
          h('div', { class: 'lineage-col' }, h('h4', null, 'Source tables'), up.length ? up.map((e) => node(e.source, e.entity_type)) : h('div', { class: 'muted' }, 'None recorded')),
          h('span', { class: 'arrow' }, '→'),
          h('div', { class: 'lineage-col' }, h('h4', null, 'Selected'), h('div', { class: 'node center' }, shortName(center), h('small', null, center))),
          h('span', { class: 'arrow' }, '→'),
          h('div', { class: 'lineage-col' }, h('h4', null, 'Targets / consumers'), down.length ? down.map((e) => node(e.target, e.entity_type)) : h('div', { class: 'muted' }, 'None recorded'))),
      ];
    });

    const colRegion = region(() => {
      const t = ui.lineageTable;
      if (!t) return null;
      const data = ui.columnLineage[t];
      if (!data) return h('button', { class: 'btn', onclick: () => loadColumns(t) }, 'Load column-level lineage');
      if (data.error) return h('div', { class: 'error-box' }, data.error);
      return dataTable([
        { label: 'Source column', render: (r) => h('code', null, `${shortName(r.source_table_full_name)}.${r.source_column_name}`) },
        { label: 'Target column', render: (r) => h('code', null, `${shortName(r.target_table_full_name)}.${r.target_column_name}`) },
        { label: 'Last seen', render: (r) => ago(r.last_seen) },
      ], data.columns, 'No column lineage recorded for this table');
    });
    async function loadColumns(t) {
      try { ui.columnLineage[t] = await api(`/api/lineage/columns?table=${encodeURIComponent(t)}`); } catch (err) { ui.columnLineage[t] = { error: err.message }; }
      colRegion.update();
    }

    const list = region(() => {
      const rows = edges().filter((e) => contains(`${e.source} ${e.target} ${e.entity_type}`, ui.lineageSearch));
      return [
        sectionNotice('lineage', 'lineage'),
        dataTable([
          { label: 'Source', render: (e) => h('code', null, e.source) },
          { label: 'Target', render: (e) => (e.target ? h('code', null, e.target) : NA) },
          { label: 'Via', key: 'entity_type' },
          { label: 'Last seen', render: (e) => ago(e.last_seen) },
        ], rows.slice(0, 500), sec('lineage') ? 'No lineage edges' : 'Lineage not loaded'),
        h('div', { class: 'footnote' }, `From system.access.table_lineage over the last ${(sec('lineage') && sec('lineage').lookback_days) || NA} days.`),
      ];
    });

    const el = h('div', null,
      head('Lineage explorer', 'Trace where each table and column was derived from, using Unity Catalog lineage.'),
      panel('Table lineage', 'Click a node to move along the chain.', null, graph.el),
      panel('Column-level derivation', 'Loaded on demand from system.access.column_lineage.', null, colRegion.el),
      panel('All lineage edges', null, null, h('div', { class: 'toolbar' }, search('Search table or entity…', ui.lineageSearch, (v) => { ui.lineageSearch = v; list.update(); })), list.el));
    return { el, update: () => { graph.update(); colRegion.update(); list.update(); } };
  };

  // SIMBA_INPLACE_TALK_TO_DATA_PATCH: local demo chat; no live AI/backend integration claimed.
  Pages['talk-data'] = () => {
    const prompts = [
      ['Kafka & Plumery', 'How does Plumery Kafka data reach Bronze?', '↯'],
      ['Medallion layers', 'Explain the Bronze, Silver and Gold layers', '◈'],
      ['Security', 'How is customer data governed?', '◇'],
      ['Analytics', 'Which tables support transaction analytics?', '▤'],
      ['Power BI', 'How does Power BI consume Gold data?', '▥'],
      ['Data quality', 'What checks should run before data reaches Gold?', '✓']
    ];

    const answerFor = (q) => {
      const t = q.toLowerCase();
      if (t.includes('kafka') || t.includes('plumery') || t.includes('bronze')) return 'Plumery events are expected to be consumed from Amazon MSK/Kafka by a Databricks Structured Streaming job and written to a Bronze Delta table. Validate broker connectivity, topic permissions, schema and replay/retention before treating this flow as live.';
      if (t.includes('layer') || t.includes('silver') || t.includes('gold') || t.includes('quality')) return 'Bronze stores raw source data, Silver applies validation, deduplication and standardisation, and Gold contains business-ready models for reporting and analytics. Data quality checks should cover required fields, duplicates, schema drift and business rules. These are the intended SIMBA design layers; pipeline execution is not verified by this demo.';
      if (t.includes('govern') || t.includes('customer data') || t.includes('access') || t.includes('security')) return 'Unity Catalog is the intended governance layer for catalog/schema/table permissions, ownership, lineage and audit. Request access through the approved process; this demo cannot grant or verify permissions.';
      if (t.includes('power bi') || t.includes('report') || t.includes('transaction') || t.includes('analytic')) return 'The intended reporting path is Power BI → Databricks SQL → curated Gold tables/views. Candidate domains include customer, transaction, transfer, payment and beneficiary analytics. Confirm final columns and table availability with the data owner.';
      return 'This is the SIMBA reference demo, not a live AI or database connection. I can explain the planned architecture and workflows, but I cannot run live queries or verify current permissions. Try a suggested topic to explore the platform.';
    };

    const transcript = h('div', { class: 'talk-transcript', 'aria-live': 'polite', 'aria-label': 'Conversation' });
    const addMessage = (who, text, isUser) => {
      const message = h('article', { class: `talk-msg ${isUser ? 'user' : 'assistant'}` },
        h('div', { class: 'talk-msg-meta' },
          h('span', { class: 'talk-msg-avatar' }, isUser ? 'You' : 'S'),
          h('b', null, who),
          h('span', { class: 'talk-msg-tag' }, isUser ? 'QUESTION' : 'SIMBA DEMO')),
        h('p', null, text));
      transcript.append(message);
      transcript.scrollTop = transcript.scrollHeight;
    };
    addMessage('SIMBA Data Assistant', 'Hi! I can help you explore the SIMBA data platform. Choose a topic below or ask a question about ingestion, lakehouse layers, governance or analytics.', false);

    const input = h('textarea', { class: 'talk-input', rows: '1', placeholder: 'Ask about Kafka, data layers, governance…', 'aria-label': 'Ask SIMBA Data Assistant' });
    const send = (question) => {
      const q = String(question || input.value || '').trim();
      if (!q) return;
      addMessage('You', q, true);
      addMessage('SIMBA Data Assistant', answerFor(q), false);
      input.value = '';
      input.style.height = 'auto';
      counter.textContent = '0 / 500';
      transcript.scrollTop = transcript.scrollHeight;
    };
    const counter = h('span', { class: 'talk-counter' }, '0 / 500');
    input.maxLength = 500;
    input.addEventListener('input', () => {
      input.style.height = 'auto';
      input.style.height = Math.min(input.scrollHeight, 130) + 'px';
      counter.textContent = `${input.value.length} / 500`;
    });
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
    });

    const sendButton = h('button', { class: 'btn primary talk-send', type: 'submit' }, 'Ask SIMBA', h('span', null, '↗'));
    const form = h('form', { class: 'talk-form', onsubmit: (e) => { e.preventDefault(); send(); } },
      h('div', { class: 'talk-composer-field' }, input,
        h('div', { class: 'talk-composer-foot' }, h('span', null, 'Enter to send · Shift + Enter for a new line'), counter)),
      sendButton);
    const suggestions = h('div', { class: 'talk-prompts' }, prompts.map(([label, question, glyph]) =>
      h('button', { class: 'talk-topic', type: 'button', onclick: () => send(question) },
        h('span', { class: 'talk-topic-icon' }, glyph),
        h('span', { class: 'talk-topic-copy' }, h('b', null, label), h('span', null, question)),
        h('span', { class: 'talk-topic-arrow' }, '↗'))));

    const el = h('div', { class: 'talk-page' },
      h('section', { class: 'talk-hero' },
        h('div', { class: 'talk-hero-copy' },
          h('div', { class: 'talk-eyebrow' }, h('span', { class: 'talk-eyebrow-dot' }), 'SIMBA KNOWLEDGE ASSISTANT'),
          h('h1', null, 'Talk to your data.'),
          h('p', null, 'Explore the SIMBA platform, from Plumery events to trusted analytics — all in one place.'),
          h('div', { class: 'talk-hero-tags' }, h('span', null, 'Kafka & ingestion'), h('span', null, 'Lakehouse'), h('span', null, 'Governance'), h('span', null, 'Analytics'))),
        h('div', { class: 'talk-hero-art', 'aria-hidden': 'true' },
          h('div', { class: 'talk-orbit talk-orbit-one' }),
          h('div', { class: 'talk-orbit talk-orbit-two' }),
          h('div', { class: 'talk-orbit talk-orbit-three' }),
          h('div', { class: 'talk-art-core' }, 'S'),
          h('span', { class: 'talk-art-chip chip-one' }, 'ASK'),
          h('span', { class: 'talk-art-chip chip-two' }, 'DATA'),
          h('span', { class: 'talk-art-chip chip-three' }, 'AI · DEMO'))),
      h('div', { class: 'talk-demo-note' }, 'Demo mode: answers are predefined reference guidance. No live AI, database query or Databricks connection is used.'),
      h('section', { class: 'talk-workspace' },
        h('div', { class: 'talk-workspace-heading' },
          h('div', null, h('div', { class: 'talk-section-kicker' }, 'GET STARTED'), h('h2', null, 'What would you like to explore?')),
          h('span', { class: 'talk-prompt-count' }, '6 TOPICS')),
        suggestions,
        h('section', { class: 'talk-chat-card' },
          h('div', { class: 'talk-chat-head' },
            h('div', { class: 'talk-chat-brand' }, h('span', { class: 'talk-chat-logo' }, 'S'),
              h('div', null, h('b', null, 'SIMBA Data Assistant'), h('span', null, 'Platform guide · Demo mode'))),
            h('span', { class: 'talk-status-pill' }, h('span', { class: 'talk-status-dot' }), 'READY')),
          transcript,
          form)));
    return { el, update: () => {} };
  };

  Pages.governance = () => {
    const ui = state.ui;
    const g = state.content.governance;
    const uniq = (key) => [...new Set(grants().map((x) => x[key]).filter(Boolean))].sort();
    const filters = region(() => h('div', { class: 'toolbar' },
      search('Search user, group, resource or privilege…', ui.grantSearch, (v) => { ui.grantSearch = v; list.update(); }),
      select([['', 'All identity types']].concat(uniq('grantee_type').map((v) => [v, v])), ui.grantType, (v) => { ui.grantType = v; list.update(); }, 'Identity type'),
      select([['', 'All resource types']].concat(uniq('securable_type').map((v) => [v, v])), ui.grantSecurable, (v) => { ui.grantSecurable = v; list.update(); }, 'Resource type'),
      select([['', 'All privileges']].concat(uniq('privilege').map((v) => [v, v])), ui.grantPrivilege, (v) => { ui.grantPrivilege = v; list.update(); }, 'Privilege'),
      select([['', 'Direct & inherited'], ['direct', 'Direct grants'], ['inherited', 'Inherited']], ui.grantPath, (v) => { ui.grantPath = v; list.update(); }, 'Access path')));
    const list = region(() => {
      const gov = sec('governance');
      const sourceGrants = grants();
      const illustrative = [
        { grantee: 'demo-analytics-team', grantee_type: 'GROUP', securable: 'simba_catalog.gold.customer_360', securable_type: 'TABLE', privilege: 'SELECT', path: 'Direct grant', grantor: 'sample-admin' },
        { grantee: 'demo-data-engineers', grantee_type: 'GROUP', securable: 'simba_catalog.bronze.kafka_events', securable_type: 'TABLE', privilege: 'SELECT', path: 'Direct grant', grantor: 'sample-admin' },
        { grantee: 'demo-platform-admins', grantee_type: 'GROUP', securable: 'simba_catalog', securable_type: 'CATALOG', privilege: 'USE CATALOG', path: 'Direct grant', grantor: 'sample-admin' },
        { grantee: 'demo-powerbi-service', grantee_type: 'SERVICE PRINCIPAL', securable: 'simba_catalog.gold.transaction_summary', securable_type: 'TABLE', privilege: 'SELECT', path: 'Inherited', grantor: 'sample-admin' },
        { grantee: 'demo-risk-analysts', grantee_type: 'GROUP', securable: 'simba_catalog.silver.customer_profile', securable_type: 'TABLE', privilege: 'SELECT', path: 'Direct grant', grantor: 'sample-admin' },
        { grantee: 'demo-data-quality', grantee_type: 'GROUP', securable: 'simba_catalog.silver.transaction', securable_type: 'TABLE', privilege: 'SELECT', path: 'Inherited', grantor: 'sample-admin' },
        { grantee: 'demo-operations', grantee_type: 'GROUP', securable: 'simba_catalog.gold.daily_kpis', securable_type: 'VIEW', privilege: 'SELECT', path: 'Direct grant', grantor: 'sample-admin' },
        { grantee: 'demo-ml-team', grantee_type: 'GROUP', securable: 'simba_catalog.gold.customer_features', securable_type: 'TABLE', privilege: 'SELECT', path: 'Inherited', grantor: 'sample-admin' },
      ];
      const displayGrants = sourceGrants.length ? sourceGrants : illustrative;
      const rows = displayGrants.filter((x) => contains(`${x.grantee} ${x.securable} ${x.privilege}`, ui.grantSearch)
        && (!ui.grantType || x.grantee_type === ui.grantType)
        && (!ui.grantSecurable || x.securable_type === ui.grantSecurable)
        && (!ui.grantPrivilege || x.privilege === ui.grantPrivilege)
        && (!ui.grantPath || (ui.grantPath === 'direct' ? x.path === 'Direct grant' : x.path !== 'Direct grant')));
      const errs = gov && gov.errors && Object.keys(gov.errors).length ? h('div', { class: 'stale' }, `Some grant views could not be read: ${Object.entries(gov.errors).map(([k, v]) => `${k} (${v})`).join(', ')}`) : null;
      return [
        sectionNotice('governance', 'access grants'), errs,
        dataTable([
          { label: 'User / group / identity', render: (x) => h('b', null, x.grantee) },
          { label: 'Identity type', render: (x) => h('span', { title: 'Inferred from the name format' }, x.grantee_type) },
          { label: 'Resource', render: (x) => h('div', null, h('code', null, x.securable), h('div', { class: 'muted' }, x.securable_type)) },
          { label: 'Privilege', render: (x) => pill(x.privilege, x.privilege === 'ALL PRIVILEGES' || x.privilege === 'MANAGE' ? 'bad' : '') },
          { label: 'Access path', key: 'path' },
          { label: 'Granted by', key: 'grantor' },
        ], rows.slice(0, 1000), gov ? (grants().length ? 'No grants match these filters' : 'No grants visible to the portal service principal') : 'Grants not loaded'),
        h('div', { class: 'footnote' }, gov ? gov.note : ''),
      ];
    });
    const el = h('div', null,
      head('Security & governance', g.summary),
      h('div', { class: 'grid g4' }, g.principles.map((p) => h('div', { class: 'principle' }, h('b', null, p.name), h('span', null, p.detail)))),
      panel('Who can access what?', grants().length ? 'Read from Unity Catalog information_schema. One row per grant.' : 'ILLUSTRATIVE SAMPLE DATA — not live Unity Catalog permissions.', null, filters.el, list.el));
    return { el, update: () => { filters.update(); list.update(); } };
  };

  Pages.dictionary = () => {
    const ui = state.ui;
    const list = region(() => {
      const rows = [];
      for (const t of tables()) {
        if (ui.dictSchema !== 'all' && t.schema !== ui.dictSchema) continue;
        for (const c of t.columns) {
          if (contains(`${t.full_name} ${c.name} ${c.type} ${c.comment || ''}`, ui.dictSearch)) rows.push({ table: t, col: c });
        }
      }
      return [
        sectionNotice('layers', 'catalog metadata'),
        dataTable([
          { label: 'Dataset', render: (r) => shortName(r.table.full_name) },
          { label: 'Column', render: (r) => h('code', null, r.col.name) },
          { label: 'Type', render: (r) => r.col.type },
          { label: 'Nullable', render: (r) => (r.col.nullable ? 'Yes' : 'No') },
          { label: 'Description', render: (r) => r.col.comment || h('span', { class: 'muted' }, 'No comment in Unity Catalog') },
        ], rows.slice(0, 800), 'No matching columns'),
        h('div', { class: 'footnote' }, `${rows.length} column${rows.length === 1 ? '' : 's'}${rows.length > 800 ? ' (first 800 shown)' : ''}. Descriptions come from Unity Catalog column comments — add them with COMMENT ON COLUMN.`),
      ];
    });
    const el = h('div', null,
      head('Data dictionary', 'Every column in the lakehouse, with types and business descriptions from Unity Catalog.'),
      panel('Columns', null, null,
        h('div', { class: 'toolbar' },
          select([['all', 'All layers']].concat(state.config.layer_schemas.map((s) => [s, s])), ui.dictSchema, (v) => { ui.dictSchema = v; list.update(); }, 'Layer'),
          search('Search column, type or description…', ui.dictSearch, (v) => { ui.dictSearch = v; list.update(); })),
        list.el));
    return { el, update: list.update };
  };

  Pages.roadmap = () => ({
    el: h('div', null,
      head("Roadmap / what's next", 'Milestones for the POC and beyond. Maintained by the project team.'),
      panel('Milestones', null, null, roadmapList(state.content.roadmap))),
    update: () => {},
  });

  Pages.request = () => ({
    el: h('div', null,
      head('Request access', 'Request dataset access, ask for a new dataset, or contact the data team.'),
      panel('Raise a request', 'Requests are handled through the approved UBA service process.', null, requestButtons(false),
        state.config.links && Object.values(state.config.links).some(Boolean) ? null : h('div', { class: 'footnote' }, 'Request links have not been configured yet (SIMBA_LINK_* settings).')),
      panel('How access is granted', null, null, h('ol', { class: 'process' }, state.content.request_process.map((s) => h('li', null, s))))),
    update: () => {},
  });

  Pages.help = () => {
    const links = state.config.links || {};
    const about = region(() => {
      const m = state.meta;
      return dataTable([
        { label: 'Section', key: 'name' },
        { label: 'Status', render: (r) => (r.ok === true ? pill('OK', 'good') : r.ok === false ? pill('Failing', 'bad') : pill('Pending', 'warn')) },
        { label: 'Last checked', render: (r) => ago(r.checked_at) },
        { label: 'Data last changed', render: (r) => ago(r.updated_at) },
      ], m ? Object.entries(m.sections).map(([name, v]) => ({ name, ...v })) : [], 'No status yet');
    });
    const el = h('div', null,
      head('Help & support', 'Answers to common questions and how to reach the data team.'),
      h('div', { class: 'grid g2' },
        panel('Contact', null, null,
          links.support_email ? h('p', null, 'Email ', h('a', { href: `mailto:${links.support_email}` }, links.support_email)) : h('p', { class: 'muted' }, 'Support email not configured yet (SIMBA_SUPPORT_EMAIL).'),
          requestButtons(true)),
        panel('Portal data status', `Mode: ${state.config.demo_mode ? 'sample data' : 'live'} · catalog ${state.config.catalog}`, null, about.el)),
      panel('Frequently asked questions', null, null, state.content.help.faq.map((f) => h('details', { class: 'faq' }, h('summary', null, f.q), h('p', null, f.a)))));
    return { el, update: about.update };
  };

  // ------------------------------------------------------------------ routing
  function buildNav() {
    const nav = document.getElementById('nav');
    nav.replaceChildren(...PAGES.flatMap((p) => [
      p.group ? h('div', { class: 'nav-group' }, p.group) : null,
      h('a', { class: 'nav', href: `#/${p.id}`, 'data-page': p.id }, icon(p.icon), p.label),
    ].filter(Boolean)));
  }

  function route() {
    const id = (location.hash.replace(/^#\/?/, '') || 'home').split('?')[0];
    const hiddenPage = id === 'sample' ? { id: 'sample', label: 'Sample preview' } : null;
    const page = PAGES.find((p) => p.id === id) || hiddenPage || PAGES[0];
    state.route = page.id;
    document.querySelectorAll('.nav').forEach((n) => n.classList.toggle('active', n.dataset.page === page.id || (page.id === 'sample' && n.dataset.page === 'layers')));
    document.getElementById('crumb').textContent = page.label;
    document.title = `${page.label} | Simba Data Lake`;
    state.page = Pages[page.id]();
    const view = document.getElementById('view');
    view.replaceChildren(state.page.el);
    state.page.update();
    view.focus({ preventScroll: true });
    window.scrollTo(0, 0);
  }

  function refreshPage() {
    if (state.page) state.page.update();
    renderLive();
  }

  // ------------------------------------------------------------------ live status
  function renderLive() {
    const el = document.getElementById('live');
    const text = document.getElementById('live-text');
    el.classList.remove('ok', 'warn', 'bad');
    const m = state.meta;
    const failing = m ? Object.values(m.sections).filter((s) => s.ok === false).length : 0;
    const checked = m ? Object.values(m.sections).map((s) => s.checked_at).filter(Boolean).sort().pop() : null;
    let label;
    if (state.transport === 'expired') { el.classList.add('bad'); label = 'Session expired — reload'; }
    else if (state.transport === 'connecting') { el.classList.add('warn'); label = 'Connecting…'; }
    else {
      const how = state.transport === 'stream' ? 'Live' : 'Polling';
      const mode = m && m.mode === 'demo' ? ' (sample data)' : '';
      el.classList.add(failing ? 'warn' : 'ok');
      label = `${how}${mode} · checked ${ago(checked)}${failing ? ` · ${failing} failing` : ''}`;
    }
    text.textContent = label;
  }

  function applySnapshot(payload) {
    if (payload.sections) Object.assign(state.sections, payload.sections);
    if (payload.meta) state.meta = payload.meta;
    if (typeof payload.version === 'number') state.version = payload.version;
  }

  // ------------------------------------------------------------------ network
  async function api(path) {
    const res = await fetch(path, { credentials: 'same-origin', redirect: 'manual', headers: { Accept: 'application/json' } });
    if (res.type === 'opaqueredirect' || res.status === 401) {
      state.transport = 'expired';
      renderLive();
      throw new Error('Your session has expired. Reload the page to sign in again.');
    }
    let body = null;
    try { body = await res.json(); } catch { /* non-JSON */ }
    if (!res.ok) throw new Error((body && body.error) || `Request failed (${res.status})`);
    return body;
  }

  let pollTimer = null;
  function startPolling() {
    state.transport = 'polling';
    renderLive();
    clearInterval(pollTimer);
    pollTimer = setInterval(async () => {
      try { applySnapshot(await api('/api/snapshot')); refreshPage(); } catch { renderLive(); }
    }, Math.max(15, state.config.fast_refresh_seconds) * 1000);
  }

  function connectStream() {
    if (!('EventSource' in window) || state.config.live_stream === false) { startPolling(); return; }
    let failures = 0;
    const es = new EventSource(`/api/stream?since=${state.version}`);
    es.addEventListener('open', () => { failures = 0; state.transport = 'stream'; renderLive(); });
    es.addEventListener('update', (e) => {
      failures = 0;
      state.transport = 'stream';
      applySnapshot(JSON.parse(e.data));
      refreshPage();
    });
    es.addEventListener('heartbeat', (e) => {
      failures = 0;
      state.transport = 'stream';
      applySnapshot(JSON.parse(e.data));
      refreshPage(); // keeps "x min ago" labels current
    });
    es.addEventListener('error', () => {
      failures += 1;
      if (failures >= 3) { es.close(); startPolling(); } else { state.transport = 'connecting'; renderLive(); }
    });
  }

  // ------------------------------------------------------------------ boot
  async function boot() {
    try {
      state.config = await api('/api/config');
      state.content = state.config.content;
      buildNav();
      applySnapshot(await api('/api/snapshot'));
    } catch (err) {
      document.getElementById('view').replaceChildren(h('div', { class: 'error-box' }, `The portal could not load: ${err.message}`));
      return;
    }
    window.addEventListener('hashchange', route);
    route();
    renderLive();
    connectStream();
  }

  document.addEventListener('DOMContentLoaded', boot);
})();


/* SIMBA route entrance animation v1 */
(() => {
  const replay = () => {
    const content = document.querySelector('.content');
    if (!content) return;
    content.classList.remove('simba-route-enter');
    void content.offsetWidth;
    content.classList.add('simba-route-enter');
  };
  window.addEventListener('hashchange', () => window.setTimeout(replay, 40));
  window.addEventListener('DOMContentLoaded', () => window.setTimeout(replay, 80));

  // Environment selector is a visual workspace label only; backend endpoints are unchanged.
  document.addEventListener('DOMContentLoaded', () => {
    const picker = document.getElementById('environment-select');
    if (!picker) return;
    const stored = sessionStorage.getItem('simba-ui-environment');
    if (stored && ['DEV', 'UAT', 'PROD'].includes(stored)) picker.value = stored;
    picker.addEventListener('change', () => sessionStorage.setItem('simba-ui-environment', picker.value));
  });

})();


/* SIMBA polish: hide obsolete demo banners,
   and animate numeric KPI values when views render. Does not alter data or authentication. */
(function simbaFinalPolish(){
  if (window.__simbaFinalPolishInstalled) return;
  window.__simbaFinalPolishInstalled = true;
  const bannerPhrases = [
    'Demo sign-in is enabled',
    'Demo mode. All figures on this page are simulated',
    'SIMULATED DEMO DATA',
    'Authentication is disabled (SIMBA_AUTH_MODE=none)'
  ];
  const clean = () => {
    // Remove banner containers by their distinctive copy, without removing page content.
    document.querySelectorAll('body *').forEach(el => {
      if (el.children.length > 3) return;
      const t = (el.innerText || el.textContent || '').trim();
      if (!t || t.length > 420) return;
      if (bannerPhrases.some(p => t.includes(p))) {
        const target = el.closest('[role="alert"], .alert, .banner, .notice, .warning, .callout') || el;
        target.style.display = 'none';
      }
    });
    // Count-up for standalone KPI/stat numbers. Mark each element once per displayed value.
    document.querySelectorAll('h1,h2,h3,h4,[class*="metric"],[class*="stat"],[class*="kpi"],[class*="count"]').forEach(el => {
      if (el.children.length || el.dataset.simbaCounted === '1') return;
      const raw = (el.textContent || '').trim();
      if (!/^\d[\d,]*(?:\.\d+)?%?$/.test(raw)) return;
      const finalValue = Number(raw.replace(/,/g, '').replace('%',''));
      if (!Number.isFinite(finalValue) || finalValue <= 0 || finalValue > 1e9) return;
      el.dataset.simbaCounted = '1';
      const suffix = raw.endsWith('%') ? '%' : '';
      const start = performance.now(), duration = 850;
      const fmt = n => Math.round(n).toLocaleString('en-US') + suffix;
      const tick = now => {
        const p = Math.min(1, (now - start) / duration);
        const eased = 1 - Math.pow(1 - p, 3);
        el.textContent = fmt(finalValue * eased);
        if (p < 1) requestAnimationFrame(tick);
      };
      el.classList.add('simba-number-animate');
      requestAnimationFrame(tick);
    });
  };
  const run = () => { try { clean(); } catch (e) { console.debug('SIMBA polish skipped', e); } };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', run, {once:true}); else run();
  new MutationObserver(() => run()).observe(document.documentElement, {childList:true,subtree:true});
})();

/* SIMBA_INPLACE_TALK_TO_DATA_PATCH styles */
(function(){
 if(document.getElementById('simba-talk-data-style')) return;
 const st=document.createElement('style'); st.id='simba-talk-data-style'; st.textContent=`
 .talk-demo-note{padding:12px 14px;margin:0 0 16px;border:1px solid #e7c989;background:#fff8e8;color:#77551a;border-radius:10px;font-size:13px;font-weight:650}
 .talk-prompts{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px}.talk-prompts .btn{white-space:normal;text-align:left;max-width:100%}
 .talk-transcript{display:flex;flex-direction:column;gap:10px;max-height:390px;overflow:auto;padding:14px;background:var(--surface-2,#f7f8fa);border:1px solid var(--border,#e2e6eb);border-radius:12px;margin:10px 0}
 .talk-msg{max-width:90%;padding:10px 13px;border-radius:10px;background:white;border:1px solid #e2e6eb}.talk-msg p{margin:5px 0 0;line-height:1.5}.talk-msg.user{align-self:flex-end;background:#eaf2ff;border-color:#c9dcff}.talk-msg.assistant{align-self:flex-start}
 .talk-form{display:flex;gap:8px}.talk-input{flex:1;min-width:0;padding:11px 13px;border:1px solid #cfd6df;border-radius:9px;font:inherit}
 `; document.head.appendChild(st);
})();


/* SIMBA_TALK_AESTHETIC_POLISH — visual-only styling for the existing Talk to Data page */
(function () {
  if (document.getElementById('simba-talk-aesthetic-polish')) return;
  const style = document.createElement('style');
  style.id = 'simba-talk-aesthetic-polish';
  style.textContent = `
    .talk-demo-note {
      display:flex !important; align-items:center; gap:10px; max-width:1040px;
      margin:0 auto 18px !important; padding:11px 16px !important;
      border:1px solid #f2d7a0 !important; border-radius:12px !important;
      background:linear-gradient(100deg,#fff8e9,#fffdf8) !important;
      color:#815b1b !important; font-size:12px !important; line-height:1.55;
      box-shadow:0 4px 14px rgba(130,91,27,.05);
    }
    .talk-demo-note:before { content:'✦'; display:grid; place-items:center; flex:0 0 25px; height:25px; border-radius:8px; background:#ffedc4; color:#8a5b06; font-size:14px; }
    .talk-demo-note:after { content:'DEMO'; margin-left:auto; flex:0 0 auto; font-size:9px; letter-spacing:.12em; font-weight:800; opacity:.75; }
    .talk-prompts { display:grid !important; grid-template-columns:repeat(auto-fit,minmax(185px,1fr)); gap:10px !important; margin:16px 0 20px !important; }
    .talk-prompts .btn { display:flex; align-items:center; justify-content:flex-start; gap:10px; min-height:62px; width:100%; padding:13px 14px !important; white-space:normal; text-align:left; line-height:1.4; border:1px solid #e2e7ef !important; border-radius:13px !important; background:#fff !important; color:#26334a !important; box-shadow:0 3px 12px rgba(24,39,75,.035); transition:transform .18s ease, box-shadow .18s ease, border-color .18s ease; }
    .talk-prompts .btn:before { content:'↗'; display:grid; place-items:center; flex:0 0 28px; height:28px; border-radius:9px; background:#eef3ff; color:#4263c7; font-weight:800; }
    .talk-prompts .btn:hover { transform:translateY(-2px); border-color:#b9c9f6 !important; box-shadow:0 9px 22px rgba(43,69,135,.09); }
    .talk-transcript { max-width:100%; min-height:250px; max-height:430px !important; gap:14px !important; padding:22px !important; margin:0 0 14px !important; border:1px solid #e5eaf2 !important; border-radius:18px !important; background:radial-gradient(ellipse at top left,rgba(230,237,255,.58),transparent 42%),linear-gradient(180deg,#fbfcff,#f7f9fc) !important; box-shadow:inset 0 1px 0 #fff; scroll-behavior:smooth; }
    .talk-msg { position:relative; max-width:min(82%,720px) !important; padding:14px 16px !important; border:1px solid #e4e9f1 !important; border-radius:15px !important; background:#fff !important; box-shadow:0 5px 16px rgba(24,39,75,.045); color:#283348; }
    .talk-msg b { display:flex; align-items:center; gap:7px; color:#26334a; font-size:12px; letter-spacing:.01em; }
    .talk-msg.assistant b:before { content:'S'; display:grid; place-items:center; width:23px; height:23px; border-radius:8px; background:linear-gradient(145deg,#e52b42,#b60e28); color:white; font-size:11px; box-shadow:0 3px 8px rgba(215,25,45,.18); }
    .talk-msg.user { align-self:flex-end; border-color:#d3e1ff !important; border-bottom-right-radius:5px !important; background:linear-gradient(135deg,#edf4ff,#e7efff) !important; }
    .talk-msg.assistant { align-self:flex-start; border-bottom-left-radius:5px !important; }
    .talk-msg p { margin:8px 0 0 !important; font-size:13px; line-height:1.7 !important; color:#4d596d; }
    .talk-form { position:relative; display:flex; align-items:center; gap:10px !important; padding:8px; border:1px solid #dfe5ee; border-radius:15px; background:#fff; box-shadow:0 8px 24px rgba(24,39,75,.07); }
    .talk-input { width:100%; padding:13px 14px !important; border:0 !important; outline:none; background:transparent; color:#202b3e; font-size:13px !important; box-shadow:none !important; }
    .talk-input:focus { outline:none; }
    .talk-form .btn { flex:0 0 auto; min-height:42px; padding:0 19px !important; border:0 !important; border-radius:10px !important; background:linear-gradient(135deg,#dc243b,#b50d29) !important; color:#fff !important; box-shadow:0 5px 12px rgba(190,20,45,.2); }
    .talk-form .btn:hover { filter:brightness(1.05); transform:translateY(-1px); }
    @media(max-width:640px) { .talk-transcript{padding:13px!important;min-height:220px}.talk-msg{max-width:94%!important}.talk-prompts{grid-template-columns:1fr}.talk-demo-note{align-items:flex-start}.talk-demo-note:after{display:none}.talk-form{gap:5px!important;padding:5px}.talk-form .btn{padding:0 12px!important} }
    @media(prefers-reduced-motion:reduce) { .talk-prompts .btn,.talk-transcript{transition:none!important;scroll-behavior:auto!important} }
  `;
  document.head.appendChild(style);
})();



/* SIMBA_TALK_DATA_PREMIUM_V2 */
(function () {
  if (document.getElementById('simba-talk-premium-v2')) return;
  const s = document.createElement('style');
  s.id = 'simba-talk-premium-v2';
  s.textContent = `
    .talk-page{max-width:1180px;margin:0 auto;animation:talkPageIn .42s ease both}
    @keyframes talkPageIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
    .talk-hero{position:relative;display:flex;align-items:center;justify-content:space-between;gap:24px;min-height:225px;overflow:hidden;padding:30px 34px;margin:0 0 18px;border:1px solid #f0cbd1;border-radius:20px;background:radial-gradient(circle at 85% 20%,rgba(255,255,255,.18),transparent 27%),linear-gradient(118deg,#24151e 0%,#761729 52%,#d7192d 100%);color:#fff;box-shadow:0 16px 36px rgba(110,17,39,.12)}
    .talk-hero-copy{position:relative;z-index:1;max-width:690px}
    .talk-eyebrow{display:flex;align-items:center;gap:8px;margin-bottom:13px;color:#ffd8df;font-size:10px;font-weight:800;letter-spacing:.16em}
    .talk-eyebrow-dot{width:7px;height:7px;border-radius:50%;background:#ffb8c5;box-shadow:0 0 0 4px rgba(255,184,197,.13)}
    .talk-hero h1{margin:0 0 10px;font-size:clamp(28px,3vw,40px);line-height:1.1;letter-spacing:-.045em;color:#fff}
    .talk-hero p{max-width:600px;margin:0;color:rgba(255,255,255,.82);font-size:14px;line-height:1.75}
    .talk-hero-tags{display:flex;flex-wrap:wrap;gap:7px;margin-top:20px}
    .talk-hero-tags span{padding:6px 10px;border:1px solid rgba(255,255,255,.2);border-radius:20px;background:rgba(255,255,255,.08);color:#fff;font-size:11px}
    .talk-hero-art{position:relative;flex:0 0 190px;width:190px;height:170px}
    .talk-orbit{position:absolute;border:1px solid rgba(255,255,255,.2);border-radius:50%;inset:9px 13px;transform:rotate(-25deg)}
    .talk-orbit-two{inset:28px 0;transform:rotate(38deg);border-color:rgba(255,255,255,.25)}
    .talk-orbit-three{inset:0 37px;transform:rotate(55deg);border-color:rgba(255,255,255,.15)}
    .talk-art-core{position:absolute;left:50%;top:50%;display:grid;place-items:center;width:66px;height:66px;transform:translate(-50%,-50%);border:1px solid rgba(255,255,255,.55);border-radius:20px;background:linear-gradient(145deg,#fff,#ffe9ed);color:#bd1730;font-size:28px;font-weight:900;box-shadow:0 12px 35px rgba(25,0,7,.2)}
    .talk-art-chip{position:absolute;padding:5px 8px;border:1px solid rgba(255,255,255,.28);border-radius:7px;background:rgba(39,7,17,.55);color:#fff;font-size:8px;font-weight:800;letter-spacing:.1em}
    .chip-one{top:6px;left:2px}.chip-two{right:0;top:52px}.chip-three{bottom:5px;left:30px}
    .talk-demo-note{display:flex;align-items:center;gap:10px;padding:11px 14px;margin:0 0 24px;border:1px solid #f1dfb7;border-radius:11px;background:#fffaf0;color:#7a5a21;font-size:11px;line-height:1.6}
    .talk-demo-note:before{content:'i';display:grid;place-items:center;flex:none;width:21px;height:21px;border-radius:50%;background:#f5e5bf;color:#79561b;font-weight:800}
    .talk-workspace{padding:0 2px}
    .talk-workspace-heading{display:flex;align-items:end;justify-content:space-between;gap:12px;margin-bottom:13px}
    .talk-section-kicker{margin-bottom:4px;color:#d7192d;font-size:9px;font-weight:850;letter-spacing:.16em}
    .talk-workspace-heading h2{margin:0;font-size:19px;letter-spacing:-.025em}
    .talk-prompt-count{padding:5px 8px;border:1px solid #e5e9f0;border-radius:7px;color:#758198;font-size:9px;font-weight:800;letter-spacing:.08em}
    .talk-prompts{display:grid!important;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px!important;margin:0 0 20px!important}
    .talk-topic{display:flex;align-items:center;gap:11px;min-width:0;min-height:91px;padding:13px!important;border:1px solid #e4e8f0!important;border-radius:13px!important;background:linear-gradient(145deg,#fff,#fbfcfe)!important;color:#243047!important;text-align:left;box-shadow:0 3px 12px rgba(23,32,51,.025);transition:transform .18s ease,border-color .18s ease,box-shadow .18s ease}
    .talk-topic:hover{transform:translateY(-3px);border-color:#e8a7b1!important;box-shadow:0 10px 24px rgba(45,30,50,.075)}
    .talk-topic-icon{display:grid;place-items:center;flex:none;width:37px;height:37px;border:1px solid #f5d7dc;border-radius:11px;background:#fff1f3;color:#c81932;font-size:18px}
    .talk-topic-copy{display:grid;gap:5px;min-width:0;flex:1}
    .talk-topic-copy b{font-size:12px;color:#202b40}
    .talk-topic-copy>span{color:#718096;font-size:10px;line-height:1.5}
    .talk-topic-arrow{align-self:flex-start;color:#a1aabd;font-size:15px}
    .talk-chat-card{overflow:hidden;border:1px solid #e3e8f0;border-radius:17px;background:#fff;box-shadow:0 8px 26px rgba(23,32,51,.045)}
    .talk-chat-head{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:15px 18px;border-bottom:1px solid #edf0f5;background:linear-gradient(90deg,#fff,#fcfcfe)}
    .talk-chat-brand{display:flex;align-items:center;gap:10px}
    .talk-chat-logo{display:grid;place-items:center;width:35px;height:35px;border-radius:11px;background:linear-gradient(145deg,#e52b42,#a90c27);color:#fff;font-size:15px;font-weight:900;box-shadow:0 4px 10px rgba(190,20,45,.16)}
    .talk-chat-brand b{display:block;font-size:12px;color:#253148}
    .talk-chat-brand div span{display:block;margin-top:2px;color:#8390a4;font-size:10px}
    .talk-status-pill{display:inline-flex;align-items:center;gap:6px;padding:5px 8px;border:1px solid #dcefe5;border-radius:20px;background:#f3fbf6;color:#26734c;font-size:9px;font-weight:800;letter-spacing:.08em}
    .talk-status-dot{width:6px;height:6px;border-radius:50%;background:#2a9a63}
    .talk-transcript{display:flex;flex-direction:column;gap:13px;min-height:220px;max-height:390px;overflow:auto;padding:22px!important;margin:0!important;border:0!important;border-radius:0!important;background:radial-gradient(ellipse at top left,#f7f9ff 0%,#fff 58%)!important;scroll-behavior:smooth}
    .talk-msg{max-width:min(83%,720px)!important;padding:12px 14px!important;border:1px solid #e7ebf2!important;border-radius:14px!important;background:#fff!important;box-shadow:0 4px 13px rgba(30,41,59,.035);color:#29364c}
    .talk-msg.assistant{align-self:flex-start;border-bottom-left-radius:4px!important}
    .talk-msg.user{align-self:flex-end;border-color:#d8e4ff!important;border-bottom-right-radius:4px!important;background:linear-gradient(140deg,#f0f5ff,#e8efff)!important}
    .talk-msg-meta{display:flex;align-items:center;gap:7px}
    .talk-msg-avatar{display:grid;place-items:center;width:23px;height:23px;border-radius:7px;background:#fff0f2;color:#c71932;font-size:9px;font-weight:850}
    .talk-msg.user .talk-msg-avatar{background:#dce7ff;color:#315bb2}
    .talk-msg-meta b{font-size:11px;color:#29364c}
    .talk-msg-tag{margin-left:auto;color:#9aa4b4;font-size:8px;font-weight:800;letter-spacing:.08em}
    .talk-msg p{margin:8px 0 0!important;color:#58667b;font-size:12px;line-height:1.75!important;white-space:pre-wrap;overflow-wrap:anywhere}
    .talk-form{display:flex;align-items:stretch;gap:10px!important;padding:14px 16px 12px!important;border-top:1px solid #edf0f5;background:#fff}
    .talk-composer-field{flex:1;min-width:0;padding:9px 12px 7px;border:1px solid #dfe5ee;border-radius:12px;background:#fbfcfe;transition:border-color .18s,box-shadow .18s}
    .talk-composer-field:focus-within{border-color:#d7192d;box-shadow:0 0 0 3px rgba(215,25,45,.07)}
    .talk-input{display:block;width:100%;min-height:28px;max-height:130px;resize:none;padding:3px 0!important;border:0!important;outline:0!important;background:transparent!important;color:#253148;font:inherit;font-size:12px!important;box-shadow:none!important}
    .talk-input:focus{outline:none!important}
    .talk-composer-foot{display:flex;justify-content:space-between;gap:10px;margin-top:4px;color:#99a3b3;font-size:9px}
    .talk-counter{white-space:nowrap}
    .talk-send{align-self:center;min-height:43px;padding:0 15px!important;border:0!important;border-radius:11px!important;background:linear-gradient(135deg,#df263d,#b90e2a)!important;color:#fff!important;box-shadow:0 6px 14px rgba(190,20,45,.17)}
    .talk-send span{font-size:16px}
    @media(max-width:900px){.talk-hero{padding:25px}.talk-hero-art{flex-basis:145px;width:145px}.talk-prompts{grid-template-columns:repeat(2,minmax(0,1fr))!important}}
    @media(max-width:620px){.talk-hero{padding:22px;min-height:0}.talk-hero-art{display:none}.talk-hero h1{font-size:29px}.talk-prompts{grid-template-columns:1fr!important}.talk-topic{min-height:72px}.talk-transcript{padding:14px!important}.talk-msg{max-width:96%!important}.talk-form{padding:10px!important;gap:7px!important}.talk-composer-foot span:first-child{max-width:190px}.talk-send{padding:0 10px!important}.talk-workspace-heading h2{font-size:17px}}
    @media(prefers-reduced-motion:reduce){.talk-page,.talk-topic{animation:none!important;transition:none!important}.talk-transcript{scroll-behavior:auto}}
  `;
  document.head.appendChild(s);
})();

