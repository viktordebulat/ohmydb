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
const legendEl = document.getElementById('legend');
const themeSwitchEl = document.getElementById('theme-switch');

const fDatabase = document.getElementById('f-database');
const fName = document.getElementById('f-name');
const fKind = document.getElementById('f-kind');
const fEngine = document.getElementById('f-engine');
const fRefreshable = document.getElementById('f-refreshable');
const labelRowsEl = document.getElementById('label-rows');
const labelAddBtn = document.getElementById('label-add');

let nodes = [];
let labelFilters = []; // [{key: input, value: input}]

async function loadClusters() {
  const clusters = await (await fetch('api/clusters')).json();
  clusterSel.innerHTML = clusters.map(c => `<option value="${c}">${c}</option>`).join('');
  if (clusters.length) await loadGraph(clusters[0]);
}

async function loadGraph(cluster) {
  statusEl.textContent = 'loading…';
  const payload = await (await fetch(`api/graph/${encodeURIComponent(cluster)}`)).json();
  nodes = payload.nodes;
  syncedAtEl.textContent = payload.synced_at ? `synced ${payload.synced_at}` : 'never synced';
  populateDistinct(fDatabase, nodes.map(n => n.database));
  populateDistinct(fKind, nodes.map(n => n.kind));
  populateDistinct(fEngine, nodes.map(n => n.engine).filter(Boolean));
  render();
}

function populateDistinct(select, values) {
  const current = select.value;
  const distinct = [...new Set(values)].sort();
  select.innerHTML = '<option value="">all</option>' +
    distinct.map(v => `<option value="${v}">${v}</option>`).join('');
  if (distinct.includes(current)) select.value = current;
}

function addLabelRow() {
  const row = document.createElement('div');
  row.className = 'label-row';
  row.innerHTML = `
    <input type="text" placeholder="key">
    <input type="text" placeholder="value">
    <button type="button">×</button>`;
  const [keyInput, valueInput] = row.querySelectorAll('input');
  row.querySelector('button').addEventListener('click', () => {
    row.remove();
    labelFilters = labelFilters.filter(r => r !== entry);
    render();
  });
  keyInput.addEventListener('input', render);
  valueInput.addEventListener('input', render);
  const entry = { key: keyInput, value: valueInput };
  labelFilters.push(entry);
  labelRowsEl.appendChild(row);
}

const HTML_ESCAPES = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
const escapeHtml = (s) => String(s).replace(/[&<>"']/g, (c) => HTML_ESCAPES[c]);

function matches(node) {
  if (fDatabase.value && node.database !== fDatabase.value) return false;
  if (fName.value && !node.name.toLowerCase().includes(fName.value.toLowerCase())) return false;
  if (fKind.value && node.kind !== fKind.value) return false;
  if (fEngine.value && node.engine !== fEngine.value) return false;
  if (fRefreshable.value && String(node.refreshable) !== fRefreshable.value) return false;
  for (const { key, value } of labelFilters) {
    const k = key.value.trim();
    if (!k) continue;
    if (node.labels[k] !== value.value) return false;
  }
  return true;
}

function render() {
  // Always renders the full filtered set (no pagination/limit) — browse-pane
  // scrolls independently so nothing found is ever hidden.
  const filtered = nodes.filter(matches);
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
      if (id && id.startsWith(ENTITY_PREFIX) && id !== mind.nodeData.id) {
        const { cluster, database, name } = parseEntityId(id);
        showRelations(cluster, database, name);
      }
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
  const res = await fetch(
    `api/entities/${encodeURIComponent(cluster)}/${encodeURIComponent(database)}/${encodeURIComponent(name)}/relations?direct=true`
  );
  if (!res.ok) {
    relationsTitleEl.textContent = `no relations found for ${cluster}/${database}/${name}`;
    return;
  }
  const rel = await res.json();
  relationsTitleEl.textContent =
    `${cluster}/${database}/${name} — direct relations (click a node to re-center)`;
  renderTree(cluster, database, name, rel);
}

function closeRelations() {
  splitEl.classList.remove('relations-open');
  browsePaneEl.style.flex = ''; // next open starts from an even split again
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

rowsEl.addEventListener('click', (e) => {
  const tr = e.target.closest('tr');
  if (!tr) return;
  rowsEl.querySelectorAll('tr.selected').forEach(r => r.classList.remove('selected'));
  tr.classList.add('selected');
  const { cluster, database, name } = tr.dataset;
  showRelations(cluster, database, name);
});

relationsCloseBtn.addEventListener('click', closeRelations);
clusterSel.addEventListener('change', () => loadGraph(clusterSel.value));
reloadBtn.addEventListener('click', () => loadGraph(clusterSel.value));
[fDatabase, fName, fKind, fEngine, fRefreshable].forEach(el =>
  el.addEventListener('input', render));
labelAddBtn.addEventListener('click', addLabelRow);

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

applyTheme(localStorage.getItem(THEME_KEY) || 'auto');

loadClusters();
