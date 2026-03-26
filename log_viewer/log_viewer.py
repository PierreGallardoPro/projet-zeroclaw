"""
Log viewer minimaliste — stdlib uniquement, zéro dépendance.
Sert une page HTML sur le port 8080, accessible via tunnel SSH.
"""
import os, json
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

LOG_FILE = os.getenv("LOG_FILE", "/app/logs/agents.jsonl")

HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Logs — ZeroClaw</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:#0d1117;color:#e6edf3;font:13px/1.5 'JetBrains Mono',monospace}

  header{
    padding:12px 20px;background:#161b22;border-bottom:1px solid #30363d;
    display:flex;align-items:center;gap:10px;position:sticky;top:0;z-index:10
  }
  h1{font-size:14px;font-weight:600;color:#fff;letter-spacing:.3px}
  .dot{width:7px;height:7px;border-radius:50%;background:#3fb950;box-shadow:0 0 5px #3fb950;animation:pulse 2s infinite;flex-shrink:0}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
  .live{color:#3fb950;font-size:11px}
  #count{color:#484f58;font-size:11px;margin-left:auto}

  #controls{
    padding:8px 20px;background:#161b22;border-bottom:1px solid #21262d;
    display:flex;gap:8px;align-items:center;flex-wrap:wrap;
    position:sticky;top:41px;z-index:9
  }
  select,input[type=text]{
    background:#0d1117;border:1px solid #30363d;border-radius:5px;
    color:#e6edf3;font:12px monospace;padding:4px 8px;outline:none
  }
  select:focus,input:focus{border-color:#388bfd}
  .sep{width:1px;height:20px;background:#30363d;flex-shrink:0}
  .btn{
    padding:4px 12px;border-radius:5px;border:1px solid #30363d;
    background:#21262d;color:#c9d1d9;font:12px monospace;cursor:pointer
  }
  .btn:hover{background:#30363d}
  .btn.active{border-color:#388bfd;color:#388bfd}

  #log{padding:0 0 40px}

  /* ── Ligne de log ── */
  .row{
    display:grid;
    grid-template-columns:148px 52px 110px 1fr;
    gap:0 10px;
    padding:5px 20px;
    border-bottom:1px solid #161b22;
    align-items:start;
    cursor:default;
    transition:background .1s
  }
  .row:hover{background:#161b22}
  .row.expanded{background:#161b22}

  .ts{color:#484f58;font-size:11px;padding-top:1px;white-space:nowrap}

  .lvl{font-size:10px;font-weight:600;letter-spacing:.5px;padding-top:2px;white-space:nowrap}
  .info{color:#388bfd}.warn{color:#d29922}.error{color:#f85149}.debug{color:#bc8cff}

  .agent-col{font-size:11px;color:#3fb950;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;padding-top:1px}

  .msg-col{display:flex;flex-direction:column;gap:4px;min-width:0}
  .msg-text{font-size:12px;color:#e6edf3;word-break:break-word}

  /* ── Champs extra (fichiers, bytes, etc.) ── */
  .extras{display:flex;flex-wrap:wrap;gap:4px;margin-top:2px}
  .tag{
    font-size:10px;padding:1px 6px;border-radius:3px;
    background:#21262d;border:1px solid #30363d;color:#8b949e;
    white-space:nowrap
  }
  .tag.file{background:#0d2637;border-color:#1f4b6b;color:#79c0ff}
  .tag.bytes{background:#0f2a1e;border-color:#196038;color:#56d364}
  .tag.lang{background:#1e1a2e;border-color:#3d2f6e;color:#bc8cff}
  .tag.err{background:#2d1c1c;border-color:#6e2828;color:#f85149}

  /* ── Indicateurs agent ── */
  .agent-badge{
    display:inline-block;font-size:9px;padding:1px 5px;border-radius:3px;
    background:#1c2128;border:1px solid #30363d;color:#8b949e;margin-left:4px
  }
  .badge-code{border-color:#3d2f6e;color:#bc8cff;background:#1e1a2e}
  .badge-mail{border-color:#1f4b6b;color:#79c0ff;background:#0d2637}

  /* ── Barre de stats ── */
  #stats{
    position:fixed;bottom:0;left:0;right:0;
    padding:6px 20px;background:#161b22;border-top:1px solid #30363d;
    display:flex;gap:16px;align-items:center;font-size:11px;color:#484f58
  }
  #stats span{color:#8b949e}
  #stats .s-info{color:#388bfd}
  #stats .s-warn{color:#d29922}
  #stats .s-error{color:#f85149}
  #stats .s-total{color:#e6edf3;font-weight:600}
</style>
</head>
<body>

<header>
  <h1>ZeroClaw Logs</h1>
  <div class="dot"></div>
  <span class="live">live</span>
  <span id="count">0 lignes</span>
</header>

<div id="controls">
  <select id="f-level">
    <option value="">Tous niveaux</option>
    <option>info</option><option>warn</option><option>error</option><option>debug</option>
  </select>
  <select id="f-agent"><option value="">Tous agents</option></select>
  <input id="f-search" type="text" placeholder="Rechercher…" style="width:200px">
  <div class="sep"></div>
  <button class="btn" id="btn-pause" onclick="togglePause()">⏸ Pause</button>
  <button class="btn" onclick="clearView()">✕ Vider</button>
</div>

<div id="log"></div>

<div id="stats">
  Total <span class="s-total" id="st-total">0</span>
  &nbsp;·&nbsp;
  INFO <span class="s-info" id="st-info">0</span>
  &nbsp;·&nbsp;
  WARN <span class="s-warn" id="st-warn">0</span>
  &nbsp;·&nbsp;
  ERROR <span class="s-error" id="st-error">0</span>
</div>

<script>
const logDiv = document.getElementById('log');
const knownAgents = new Set();
let rows = [];
let paused = false;

// ── Formatage ──────────────────────────────────────────────────────────────

function fmtTs(iso) {
  try {
    const d = new Date(iso);
    return d.toLocaleString('fr-FR', {
      day:'2-digit', month:'2-digit', hour:'2-digit',
      minute:'2-digit', second:'2-digit'
    }).replace(',', '');
  } catch { return iso; }
}

function esc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// Choisit le style de tag selon la clé
function tagClass(key, val) {
  if (key === 'fichiers' || key === 'fichier' || String(val).includes('/') || String(val).endsWith('.py') || String(val).endsWith('.js') || String(val).endsWith('.html')) return 'file';
  if (key === 'bytes' || key === 'longueur' || key === 'caracteres') return 'bytes';
  if (key === 'lang' || key === 'langage') return 'lang';
  if (key === 'erreur') return 'err';
  return '';
}

function renderExtras(entry) {
  const skip = new Set(['ts','epoch','agent','level','msg']);
  const extra = Object.entries(entry).filter(([k]) => !skip.has(k));
  if (!extra.length) return '';

  const tags = extra.map(([k, v]) => {
    const cls = tagClass(k, v);
    // Si la valeur est un tableau (ex: fichiers écrits)
    if (Array.isArray(v)) {
      return v.map(item => `<span class="tag ${cls}">${esc(k === 'fichiers' ? '' : k+':')}${esc(item)}</span>`).join('');
    }
    return `<span class="tag ${cls}">${esc(k)}: ${esc(v)}</span>`;
  }).join('');

  return `<div class="extras">${tags}</div>`;
}

function agentBadgeClass(agent) {
  if (!agent) return '';
  if (agent.includes('code')) return 'badge-code';
  if (agent.includes('mail')) return 'badge-mail';
  return '';
}

function renderRow(e) {
  const extras = renderExtras(e);
  return `<div class="row">
    <div class="ts">${fmtTs(e.ts)}</div>
    <div class="lvl ${e.level||''}">${(e.level||'—').toUpperCase()}</div>
    <div class="agent-col">${esc(e.agent||'—')}</div>
    <div class="msg-col">
      <div class="msg-text">${esc(e.msg||JSON.stringify(e))}</div>
      ${extras}
    </div>
  </div>`;
}

// ── Rendu ──────────────────────────────────────────────────────────────────

function activeFilters() {
  return {
    lvl:    document.getElementById('f-level').value,
    ag:     document.getElementById('f-agent').value,
    search: document.getElementById('f-search').value.toLowerCase(),
  };
}

function matchesFilter(e, f) {
  if (f.lvl    && e.level !== f.lvl)  return false;
  if (f.ag     && e.agent !== f.ag)   return false;
  if (f.search && !JSON.stringify(e).toLowerCase().includes(f.search)) return false;
  return true;
}

function render(data) {
  const f = activeFilters();
  const filtered = data.filter(e => matchesFilter(e, f));
  logDiv.innerHTML = filtered.map(renderRow).join('');
  document.getElementById('count').textContent = filtered.length + ' lignes';
  updateStats(data);
  logDiv.scrollTop = logDiv.scrollHeight;
}

function updateStats(data) {
  document.getElementById('st-total').textContent = data.length;
  document.getElementById('st-info').textContent  = data.filter(e => e.level === 'info').length;
  document.getElementById('st-warn').textContent  = data.filter(e => e.level === 'warn').length;
  document.getElementById('st-error').textContent = data.filter(e => e.level === 'error').length;
}

// ── Agents dropdown ────────────────────────────────────────────────────────

function addAgentOption(agent) {
  if (!agent || knownAgents.has(agent)) return;
  knownAgents.add(agent);
  const sel = document.getElementById('f-agent');
  const opt = document.createElement('option');
  opt.value = opt.textContent = agent;
  sel.appendChild(opt);
}

// ── Poll ───────────────────────────────────────────────────────────────────

async function poll() {
  if (paused) return;
  try {
    const r = await fetch('/logs');
    rows = await r.json();
    rows.forEach(e => addAgentOption(e.agent));
    render(rows);
  } catch {}
}

// ── Contrôles ──────────────────────────────────────────────────────────────

function togglePause() {
  paused = !paused;
  const btn = document.getElementById('btn-pause');
  btn.textContent = paused ? '▶ Reprendre' : '⏸ Pause';
  btn.classList.toggle('active', paused);
}

function clearView() {
  rows = [];
  logDiv.innerHTML = '';
  updateStats([]);
  document.getElementById('count').textContent = '0 lignes';
}

['f-level','f-agent','f-search'].forEach(id =>
  document.getElementById(id).addEventListener('input', () => render(rows))
);

poll();
setInterval(poll, 3000);
</script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_): pass

    def do_GET(self):
        if self.path == "/":
            self._send(200, "text/html; charset=utf-8", HTML.encode())
        elif self.path == "/logs":
            self._send(200, "application/json", self._read_logs())
        else:
            self._send(404, "text/plain", b"404")

    def _send(self, code, ct, body):
        self.send_response(code)
        self.send_header("Content-Type", ct)
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _read_logs(self):
        p = Path(LOG_FILE)
        if not p.exists():
            return b"[]"
        entries = []
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except Exception:
                pass
        return json.dumps(entries[-2000:], ensure_ascii=False).encode()


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    print(f"[log-viewer] http://0.0.0.0:{port}", flush=True)
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()