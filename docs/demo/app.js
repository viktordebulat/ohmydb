import MindElixir from './vendor/mind-elixir.js';

const clusterSel = document.getElementById('cluster');
const reloadBtn = document.getElementById('reload');
const syncedAtEl = document.getElementById('synced-at');
const statusEl = document.getElementById('status');
const rowsEl = document.getElementById('rows');
const splitEl = document.getElementById('split');
const browsePaneEl = document.getElementById('browse-pane');
const splitHandleEl = document.getElementById('split-handle');
const relationsTitleEl = document.getElementById('relations-title');
const relationsCloseBtn = document.getElementById('relations-close');
const mindmapEl = document.getElementById('mindmap');
const mindmapAreaEl = document.getElementById('mindmap-area');
const legendEl = document.getElementById('legend');
const schemaTitleEl = document.getElementById('schema-title');
const schemaBodyEl = document.getElementById('schema-body');
const schemaCopyBtn = document.getElementById('schema-copy');
const schemaCloseBtn = document.getElementById('schema-close');
const schemaHandleEl = document.getElementById('schema-handle');
const schemaPaneEl = document.getElementById('schema-pane');
const themeSwitchEl = document.getElementById('theme-switch');
const infoBtn = document.getElementById('info-btn');
const infoOverlayEl = document.getElementById('info-overlay');
const infoCloseBtn = document.getElementById('info-close');

const fDatabase = document.getElementById('f-database');
const fName = document.getElementById('f-name');
const fKind = document.getElementById('f-kind');
const fEngine = document.getElementById('f-engine');
const fRefreshable = document.getElementById('f-refreshable');
const labelRowsEl = document.getElementById('label-rows');
const labelAddBtn = document.getElementById('label-add');
const filtersClearBtn = document.getElementById('filters-clear');

let nodes = [];
let labelFilters = []; // [{keySelect, valueInput, datalist}]
let sortKey = null;
let sortDir = 1; // 1 = asc, -1 = desc

async function fetchJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url}: HTTP ${res.status}`);
  return res.json();
}

// A failed initial load used to die as an unhandled rejection, leaving an
// empty page with no hint — surface it in the status line instead; the
// reload button retries from whichever step failed.
async function loadClusters() {
  try {
    const clusters = await fetchJson('api/clusters');
    clusterSel.innerHTML = clusters.map(c => `<option value="${c}">${c}</option>`).join('');
  } catch (e) {
    statusEl.textContent = `failed to load clusters (${e.message}) — press reload`;
    return;
  }
  if (clusterSel.value) await loadGraph(clusterSel.value);
}

async function loadGraph(cluster) {
  statusEl.textContent = 'loading…';
  let payload;
  try {
    payload = await fetchJson(`api/graph/${encodeURIComponent(cluster)}`);
  } catch (e) {
    statusEl.textContent = `failed to load catalog (${e.message}) — press reload`;
    return;
  }
  nodes = payload.nodes;
  syncedAtEl.textContent = payload.synced_at ? `synced ${payload.synced_at}` : 'never synced';
  populateDistinct(fDatabase, nodes.map(n => n.database));
  refreshLabelKeyOptions();
  labelFilters.forEach(updateLabelValueOptions);
  render(); // also (re)populates fKind/fEngine, cross-filtered by the other fields
}

// placeholder is itself trusted (call-site literal), only `values` needs escaping.
function populateDistinct(select, values, placeholder = 'all') {
  const current = select.value;
  const distinct = [...new Set(values)].sort();
  select.innerHTML = `<option value="">${placeholder}</option>` +
    distinct.map(v => `<option value="${escapeHtml(v)}">${escapeHtml(v)}</option>`).join('');
  if (distinct.includes(current)) select.value = current;
}

// kind/engine options narrow to what's actually reachable given every OTHER
// active filter (including each other and the label rows) — `exclude` skips
// that one field's own check in matches() so its dropdown still offers its
// own current selection as a choice, not just what it already lets through.
function updateFacetOptions() {
  populateDistinct(fKind, nodes.filter(n => matches(n, 'kind')).map(n => n.kind));
  populateDistinct(fEngine, nodes.filter(n => matches(n, 'engine')).map(n => n.engine).filter(Boolean));
}

let labelRowSeq = 0;

function addLabelRow() {
  const row = document.createElement('div');
  row.className = 'label-row';
  const datalistId = `label-values-${labelRowSeq++}`;
  row.innerHTML = `
    <select title="Label key to filter by (options come from labels seen on this cluster).">
      <option value="">key</option>
    </select>
    <input type="text" list="${datalistId}" placeholder="value1|value2"
      title="Optional. Matches if the label's value equals any of these, separated by | (exact, case-insensitive) — e.g. vector|data-pipelines. Leave empty to match any value for this key. Pick a suggestion or type your own.">
    <datalist id="${datalistId}"></datalist>
    <button type="button" title="remove this label filter">×</button>`;
  const keySelect = row.querySelector('select');
  const valueInput = row.querySelector('input');
  const datalist = row.querySelector('datalist');
  const entry = { keySelect, valueInput, datalist };
  keySelect.addEventListener('change', () => {
    updateLabelValueOptions(entry);
    render();
  });
  valueInput.addEventListener('input', render);
  row.querySelector('button').addEventListener('click', () => {
    row.remove();
    labelFilters = labelFilters.filter(r => r !== entry);
    render();
  });
  labelFilters.push(entry);
  labelRowsEl.appendChild(row);
  refreshLabelKeyOptions();
  updateLabelValueOptions(entry);
}

function refreshLabelKeyOptions() {
  const keys = [...new Set(nodes.flatMap(n => Object.keys(n.labels || {})))].sort();
  for (const entry of labelFilters) populateDistinct(entry.keySelect, keys, 'key');
}

function updateLabelValueOptions(entry) {
  const k = entry.keySelect.value;
  const values = k ? [...new Set(nodes.map(n => n.labels[k]).filter(v => v !== undefined))].sort() : [];
  entry.datalist.innerHTML = values.map(v => `<option value="${escapeHtml(v)}"></option>`).join('');
}

const HTML_ESCAPES = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
const escapeHtml = (s) => String(s).replace(/[&<>"']/g, (c) => HTML_ESCAPES[c]);

// `exclude` lets a facet's own dropdown compute its options against every
// OTHER filter without also filtering on itself (see updateFacetOptions).
function matches(node, exclude) {
  if (fDatabase.value && node.database !== fDatabase.value) return false;
  if (fName.value && !node.name.toLowerCase().includes(fName.value.toLowerCase())) return false;
  if (exclude !== 'kind' && fKind.value && node.kind !== fKind.value) return false;
  if (exclude !== 'engine' && fEngine.value && node.engine !== fEngine.value) return false;
  if (fRefreshable.value && String(node.refreshable) !== fRefreshable.value) return false;
  for (const { keySelect, valueInput } of labelFilters) {
    const k = keySelect.value;
    if (!k) continue;
    const labelValue = node.labels[k];
    if (labelValue === undefined) return false; // key chosen, entity doesn't have it
    const wanted = valueInput.value.trim().split('|').map(s => s.trim().toLowerCase()).filter(Boolean);
    if (wanted.length && !wanted.includes(labelValue.toLowerCase())) return false;
  }
  return true;
}

function sortValue(n, key) {
  if (key === 'refreshable') return n.refreshable ? 1 : 0;
  return (n[key] || '').toString().toLowerCase();
}

function render() {
  updateFacetOptions();
  // Always renders the full filtered set (no pagination/limit) — browse-pane
  // scrolls independently so nothing found is ever hidden.
  const filtered = nodes.filter(n => matches(n));
  if (sortKey) {
    filtered.sort((a, b) => {
      const av = sortValue(a, sortKey);
      const bv = sortValue(b, sortKey);
      if (av < bv) return -1 * sortDir;
      if (av > bv) return 1 * sortDir;
      return 0;
    });
  }
  statusEl.textContent = `${filtered.length} / ${nodes.length} entities`;
  // Entity identity and label key/value are all attacker-reachable (label
  // values via PUT /api/labels, names/databases via whatever synced from the
  // source DB) — escape everything going into innerHTML.
  rowsEl.innerHTML = filtered.map(n => `
    <tr data-cluster="${escapeHtml(n.cluster)}" data-database="${escapeHtml(n.database)}" data-name="${escapeHtml(n.name)}">
      <td>${escapeHtml(n.name)}</td>
      <td>${escapeHtml(n.database)}</td>
      <td>${escapeHtml(n.kind)}</td>
      <td>${escapeHtml(n.engine || '')}</td>
      <td>${n.refreshable ? 'yes' : ''}</td>
      <td>${Object.entries(n.labels).map(([k, v]) => `<span class="chip">${escapeHtml(k)}:${escapeHtml(v)}</span>`).join('')}</td>
    </tr>`).join('');
}

const entityApiUrl = (cluster, database, name) =>
  `api/entities/${encodeURIComponent(cluster)}/${encodeURIComponent(database)}/${encodeURIComponent(name)}`;

const ENTITY_PREFIX = 'e:';
const entityId = (cluster, database, name) => `${ENTITY_PREFIX}${cluster}::${database}::${name}`;
const parseEntityId = (id) => {
  const [cluster, database, name] = id.slice(ENTITY_PREFIX.length).split('::');
  return { cluster, database, name };
};

// Validated default categorical palette (see the dataviz skill's
// references/palette.md) — same slots this page's own light/dark surface
// colors come from. Fixed order, assigned to label keys in first-seen order
// and never reassigned for the session; only cycles past the 8th distinct
// key, which the project's label cardinality (service/team/source/...)
// isn't expected to hit.
const LABEL_PALETTE = [
  { light: '#2a78d6', dark: '#3987e5' }, // blue
  { light: '#eb6834', dark: '#d95926' }, // orange
  { light: '#1baf7a', dark: '#199e70' }, // aqua
  { light: '#eda100', dark: '#c98500' }, // yellow
  { light: '#e87ba4', dark: '#d55181' }, // magenta
  { light: '#008300', dark: '#008300' }, // green
  { light: '#4a3aa7', dark: '#9085e9' }, // violet
  { light: '#e34948', dark: '#e66767' }, // red
];
const labelKeyOrder = [];

function labelColor(key) {
  let idx = labelKeyOrder.indexOf(key);
  if (idx === -1) {
    idx = labelKeyOrder.length;
    labelKeyOrder.push(key);
  }
  const slot = LABEL_PALETTE[idx % LABEL_PALETTE.length];
  return isDarkActive() ? slot.dark : slot.light;
}

// Identity is carried by the swatch, not by coloring the text itself (text
// stays in normal ink) — keeps label rows legible for colorblind readers.
function nodeTopicHtml(e) {
  const lines = [
    `<div>${escapeHtml(e.name)}</div>`,
    `<div class="tpc-sub">${escapeHtml(e.database)}${e.engine ? ' · ' + escapeHtml(e.engine) : ''}</div>`,
  ];
  // Key isn't repeated here — the swatch color is the key (see the legend);
  // the node only needs to show the value.
  for (const [k, v] of Object.entries(e.labels || {})) {
    lines.push(
      `<div class="tpc-label" title="${escapeHtml(k)}"><span class="tpc-swatch" style="background:${labelColor(k)}"></span>${escapeHtml(v)}</div>`
    );
  }
  return lines.join('');
}

function renderLegend(rel) {
  const keys = new Set();
  [rel.entity, ...rel.upstream, ...rel.downstream].forEach(e =>
    Object.keys(e.labels || {}).forEach(k => keys.add(k)));
  legendEl.innerHTML = [...keys].map(k => `
    <span class="legend-item">
      <span class="legend-swatch" style="background:${labelColor(k)}"></span>${escapeHtml(k)}
    </span>`).join('');
  legendEl.style.display = keys.size ? 'flex' : 'none';
}

let mind = null;

// mind-elixir renders into its own `.map-container`, styled via its own
// theme object (bgcolor/color per node) — it doesn't inherit our page's
// CSS custom properties, so switching #theme-switch has to also push a
// matching MindElixir.THEME/DARK_THEME into the mind instance explicitly.
const prefersDark = window.matchMedia('(prefers-color-scheme: dark)');
let currentTheme = 'auto';
const isDarkActive = () => currentTheme === 'dark' || (currentTheme === 'auto' && prefersDark.matches);
const mindTheme = () => (isDarkActive() ? MindElixir.DARK_THEME : MindElixir.THEME);

function relationsToMindData(cluster, database, name, rel) {
  const branch = (title, entries, idPrefix) => ({
    id: `g:${idPrefix}`,
    topic: `${title} (${entries.length})`,
    children: entries.map(e => ({
      id: entityId(e.cluster, e.database, e.name),
      topic: nodeTopicHtml(e),
    })),
  });
  return {
    nodeData: {
      id: entityId(cluster, database, name),
      topic: nodeTopicHtml(rel.entity),
      children: [
        branch('Upstream', rel.upstream, 'upstream'),
        branch('Downstream', rel.downstream, 'downstream'),
      ],
    },
  };
}

// Cache of the last successfully rendered tree — lets a theme switch
// rebuild topics/legend with the right light/dark swatch colors without a
// refetch (labelColor() depends on isDarkActive()).
let lastRel = null;

function renderTree(cluster, database, name, rel) {
  lastRel = { cluster, database, name, rel };
  renderLegend(rel);
  const data = relationsToMindData(cluster, database, name, rel);
  if (!mind) {
    mind = new MindElixir({
      el: mindmapEl,
      direction: MindElixir.SIDE,
      theme: mindTheme(),
      markdown: (text) => text, // topics are pre-escaped HTML (nodeTopicHtml) so labels can carry a color swatch
      editable: false,
      toolBar: false,
      contextMenu: false,
      keypress: false,
    });
    mind.init(data);
    mind.bus.addListener('selectNodes', (selected) => {
      const id = selected?.[0]?.id;
      if (!id || !id.startsWith(ENTITY_PREFIX)) return;
      const { cluster, database, name } = parseEntityId(id);
      showSchema(cluster, database, name);
      if (id !== mind.nodeData.id) showRelations(cluster, database, name);
    });
  } else {
    mind.refresh(data);
    mind.changeTheme(mindTheme()); // refresh() alone doesn't push a theme change
  }
  // toCenter() runs during init/refresh, but el's layout box isn't reliably
  // final until after the next paint (freshly un-hidden container, or a
  // resize from the previous tree/split drag) — recenter once more post-layout.
  requestAnimationFrame(() => mind.toCenter());
}

async function showRelations(cluster, database, name) {
  splitEl.classList.add('relations-open');
  relationsTitleEl.textContent = `loading relations for ${cluster}/${database}/${name}…`;
  const entityUrl = entityApiUrl(cluster, database, name);
  const res = await fetch(`${entityUrl}/relations?direct=true`);
  if (!res.ok) {
    relationsTitleEl.textContent = `no relations found for ${cluster}/${database}/${name}`;
    return;
  }
  const rel = await res.json();
  relationsTitleEl.innerHTML =
    `${escapeHtml(cluster)}/${escapeHtml(database)}/${escapeHtml(name)} — ` +
    `<a href="${entityUrl}" target="_blank" rel="noopener">API table</a> · ` +
    `<a href="${entityUrl}/relations?direct=true" target="_blank" rel="noopener">relations</a> ` +
    `(click a node to re-center)`;
  renderTree(cluster, database, name, rel);
}

let lastSchemaDdl = '';

async function showSchema(cluster, database, name) {
  mindmapAreaEl.classList.add('schema-open');
  schemaTitleEl.textContent = `${cluster}/${database}/${name}`;
  schemaBodyEl.innerHTML = '<div class="sub">loading…</div>';
  lastSchemaDdl = '';
  schemaCopyBtn.disabled = true;
  const res = await fetch(entityApiUrl(cluster, database, name));
  if (!res.ok) {
    schemaBodyEl.innerHTML = '<div class="sub">not found</div>';
    return;
  }
  const e = await res.json();
  lastSchemaDdl = e.ddl || '';
  schemaCopyBtn.disabled = !lastSchemaDdl;
  const meta = [
    ['kind', e.kind],
    ['engine', e.engine_full || e.engine || ''],
    ['primary key', e.primary_key || ''],
    ['sorting key', e.sorting_key || ''],
  ].filter(([, v]) => v);
  const metaRows = meta.map(([k, v]) => `<tr><th>${escapeHtml(k)}</th><td>${escapeHtml(v)}</td></tr>`).join('');
  const colRows = (e.columns || []).map(c => `
    <tr><td>${escapeHtml(c.name)}</td><td>${escapeHtml(c.type)}</td><td>${escapeHtml(c.comment || '')}</td></tr>`).join('');
  schemaBodyEl.innerHTML = `
    <table class="meta-table"><tbody>${metaRows}</tbody></table>
    <table><thead><tr><th>column</th><th>type</th><th>comment</th></tr></thead><tbody>${colRows}</tbody></table>`;
}

function closeRelations() {
  splitEl.classList.remove('relations-open');
  browsePaneEl.style.flex = ''; // next open starts from an even split again
  mindmapAreaEl.classList.remove('schema-open');
  schemaPaneEl.style.flex = '';
  lastSchemaDdl = '';
  schemaCopyBtn.disabled = true;
  rowsEl.querySelectorAll('tr.selected').forEach(r => r.classList.remove('selected'));
}

let dragging = false;
splitHandleEl.addEventListener('pointerdown', (e) => {
  dragging = true;
  splitHandleEl.setPointerCapture(e.pointerId);
  splitHandleEl.classList.add('dragging');
});
splitHandleEl.addEventListener('pointermove', (e) => {
  if (!dragging) return;
  const containerRect = splitEl.getBoundingClientRect();
  const handleHeight = splitHandleEl.getBoundingClientRect().height;
  const min = 60;
  const max = containerRect.height - min - handleHeight;
  const height = Math.max(min, Math.min(max, e.clientY - containerRect.top));
  browsePaneEl.style.flex = `0 0 ${height}px`;
});
['pointerup', 'pointercancel'].forEach(evt => splitHandleEl.addEventListener(evt, () => {
  dragging = false;
  splitHandleEl.classList.remove('dragging');
}));

let schemaDragging = false;
schemaHandleEl.addEventListener('pointerdown', (e) => {
  schemaDragging = true;
  schemaHandleEl.setPointerCapture(e.pointerId);
  schemaHandleEl.classList.add('dragging');
});
schemaHandleEl.addEventListener('pointermove', (e) => {
  if (!schemaDragging) return;
  const containerRect = mindmapAreaEl.getBoundingClientRect();
  const handleWidth = schemaHandleEl.getBoundingClientRect().width;
  const min = 180;
  const max = containerRect.width - min - handleWidth;
  const width = Math.max(min, Math.min(max, containerRect.right - e.clientX));
  schemaPaneEl.style.flex = `0 0 ${width}px`;
});
['pointerup', 'pointercancel'].forEach(evt => schemaHandleEl.addEventListener(evt, () => {
  schemaDragging = false;
  schemaHandleEl.classList.remove('dragging');
}));
schemaCloseBtn.addEventListener('click', () => {
  mindmapAreaEl.classList.remove('schema-open');
  schemaPaneEl.style.flex = '';
});
schemaCopyBtn.addEventListener('click', async () => {
  if (!lastSchemaDdl) return;
  await navigator.clipboard.writeText(lastSchemaDdl);
  const original = schemaCopyBtn.textContent;
  schemaCopyBtn.textContent = 'copied';
  setTimeout(() => { schemaCopyBtn.textContent = original; }, 1200);
});

document.querySelectorAll('th[data-sort]').forEach(th => {
  th.addEventListener('click', () => {
    const key = th.dataset.sort;
    sortDir = sortKey === key ? -sortDir : 1;
    sortKey = key;
    document.querySelectorAll('th[data-sort]').forEach(t => t.classList.remove('sort-asc', 'sort-desc'));
    th.classList.add(sortDir === 1 ? 'sort-asc' : 'sort-desc');
    render();
  });
});

rowsEl.addEventListener('click', (e) => {
  const tr = e.target.closest('tr');
  if (!tr) return;
  rowsEl.querySelectorAll('tr.selected').forEach(r => r.classList.remove('selected'));
  tr.classList.add('selected');
  const { cluster, database, name } = tr.dataset;
  mindmapAreaEl.classList.remove('schema-open'); // new browse target — stale schema pane no longer applies
  showRelations(cluster, database, name);
});

relationsCloseBtn.addEventListener('click', closeRelations);
clusterSel.addEventListener('change', () => loadGraph(clusterSel.value));
reloadBtn.addEventListener('click', () => (clusterSel.value ? loadGraph(clusterSel.value) : loadClusters()));
[fDatabase, fName, fKind, fEngine, fRefreshable].forEach(el =>
  el.addEventListener('input', render));
labelAddBtn.addEventListener('click', addLabelRow);
filtersClearBtn.addEventListener('click', () => {
  fDatabase.value = '';
  fName.value = '';
  fKind.value = '';
  fEngine.value = '';
  fRefreshable.value = '';
  labelRowsEl.innerHTML = '';
  labelFilters = [];
  render();
});

// Key must match the inline anti-FOUC script in index.html's <head>.
const THEME_KEY = 'oh-my-db-theme';

function applyTheme(theme) {
  currentTheme = theme;
  if (theme === 'auto') {
    delete document.documentElement.dataset.theme;
  } else {
    document.documentElement.dataset.theme = theme;
  }
  themeSwitchEl.querySelectorAll('button').forEach(b =>
    b.classList.toggle('active', b.dataset.themeChoice === theme));
  // Rebuilds from the cached rel (no refetch) so both the mind-elixir theme
  // and the label swatch colors (labelColor() reads isDarkActive()) follow
  // the switch immediately, not just on the next row click.
  if (lastRel) renderTree(lastRel.cluster, lastRel.database, lastRel.name, lastRel.rel);
}

themeSwitchEl.addEventListener('click', (e) => {
  const btn = e.target.closest('button');
  if (!btn) return;
  const theme = btn.dataset.themeChoice;
  localStorage.setItem(THEME_KEY, theme);
  applyTheme(theme);
});

// Only matters in "auto": OS preference can change without a page reload.
prefersDark.addEventListener('change', () => {
  if (currentTheme === 'auto') applyTheme('auto');
});

function closeInfo() { infoOverlayEl.classList.remove('open'); }
infoBtn.addEventListener('click', () => infoOverlayEl.classList.add('open'));
infoCloseBtn.addEventListener('click', closeInfo);
infoOverlayEl.addEventListener('click', (e) => { if (e.target === infoOverlayEl) closeInfo(); });
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && infoOverlayEl.classList.contains('open')) closeInfo();
});

applyTheme(localStorage.getItem(THEME_KEY) || 'auto');

loadClusters();
