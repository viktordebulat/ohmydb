import MindElixir from '/vendor/mind-elixir.js';

const clusterSel = document.getElementById('cluster');
const refreshBtn = document.getElementById('refresh');
const syncedAtEl = document.getElementById('synced-at');
const statusEl = document.getElementById('status');
const rowsEl = document.getElementById('rows');
const splitEl = document.getElementById('split');
const browsePaneEl = document.getElementById('browse-pane');
const splitHandleEl = document.getElementById('split-handle');
const relationsTitleEl = document.getElementById('relations-title');
const relationsCloseBtn = document.getElementById('relations-close');
const mindmapEl = document.getElementById('mindmap');
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
  const clusters = await (await fetch('/api/clusters')).json();
  clusterSel.innerHTML = clusters.map(c => `<option value="${c}">${c}</option>`).join('');
  if (clusters.length) await loadGraph(clusters[0]);
}

async function loadGraph(cluster) {
  statusEl.textContent = 'loading…';
  const payload = await (await fetch(`/api/graph/${encodeURIComponent(cluster)}`)).json();
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
  rowsEl.innerHTML = filtered.map(n => `
    <tr data-cluster="${n.cluster}" data-database="${n.database}" data-name="${n.name}">
      <td>${n.name}</td>
      <td>${n.database}</td>
      <td>${n.kind}</td>
      <td>${n.engine || ''}</td>
      <td>${n.refreshable ? 'yes' : ''}</td>
      <td>${Object.entries(n.labels).map(([k, v]) => `<span class="chip">${k}:${v}</span>`).join('')}</td>
    </tr>`).join('');
}

const ENTITY_PREFIX = 'e:';
const entityId = (cluster, database, name) => `${ENTITY_PREFIX}${cluster}::${database}::${name}`;
const parseEntityId = (id) => {
  const [cluster, database, name] = id.slice(ENTITY_PREFIX.length).split('::');
  return { cluster, database, name };
};
const nodeLabel = (e) => `${e.name}\n${e.database}${e.engine ? ' · ' + e.engine : ''}`;

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
      topic: nodeLabel(e),
    })),
  });
  return {
    nodeData: {
      id: entityId(cluster, database, name),
      topic: nodeLabel(rel.entity),
      children: [
        branch('Upstream', rel.upstream, 'upstream'),
        branch('Downstream', rel.downstream, 'downstream'),
      ],
    },
  };
}

async function showRelations(cluster, database, name) {
  splitEl.classList.add('relations-open');
  relationsTitleEl.textContent = `loading relations for ${cluster}/${database}/${name}…`;
  const res = await fetch(
    `/api/entities/${encodeURIComponent(cluster)}/${encodeURIComponent(database)}/${encodeURIComponent(name)}/relations?direct=true`
  );
  if (!res.ok) {
    relationsTitleEl.textContent = `no relations found for ${cluster}/${database}/${name}`;
    return;
  }
  const rel = await res.json();
  relationsTitleEl.textContent =
    `${cluster}/${database}/${name} — direct relations (click a node to re-center)`;

  const data = relationsToMindData(cluster, database, name, rel);
  if (!mind) {
    mind = new MindElixir({
      el: mindmapEl,
      direction: MindElixir.SIDE,
      theme: mindTheme(),
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
  }
  // toCenter() runs during init/refresh, but el's layout box isn't reliably
  // final until after the next paint (freshly un-hidden container, or a
  // resize from the previous tree/split drag) — recenter once more post-layout.
  requestAnimationFrame(() => mind.toCenter());
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
refreshBtn.addEventListener('click', () => loadGraph(clusterSel.value));
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
  if (mind) mind.changeTheme(mindTheme());
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
