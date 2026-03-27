"""
Log viewer minimaliste — stdlib uniquement, zéro dépendance.
Sert une page HTML sur le port 8080, accessible via tunnel SSH.
"""
import os, json
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from datetime import datetime, timezone

LOG_FILE = os.getenv("LOG_FILE", "/app/logs/agents.jsonl")

HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Logs — ZeroClaw</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:#0d1117;color:#e6edf3;font:13px/1.5 'JetBrains Mono',monospace}
  header{padding:12px 20px;background:#161b22;border-bottom:1px solid #30363d;display:flex;align-items:center;gap:10px;position:sticky;top:0;z-index:10}
  h1{font-size:14px;font-weight:600;color:#fff;letter-spacing:.3px}
  .dot{width:7px;height:7px;border-radius:50%;background:#3fb950;box-shadow:0 0 5px #3fb950;animation:pulse 2s infinite;flex-shrink:0}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
  .live{color:#3fb950;font-size:11px}
  #count{color:#484f58;font-size:11px;margin-left:auto}
  #controls{padding:8px 20px;background:#161b22;border-bottom:1px solid #21262d;display:flex;gap:8px;align-items:center;flex-wrap:wrap;position:sticky;top:41px;z-index:9}
  select,input[type=text]{background:#0d1117;border:1px solid #30363d;border-radius:5px;color:#e6edf3;font:12px monospace;padding:4px 8px;outline:none}
  select:focus,input:focus{border-color:#388bfd}
  .sep{width:1px;height:20px;background:#30363d;flex-shrink:0}
  .btn{padding:4px 12px;border-radius:5px;border:1px solid #30363d;background:#21262d;color:#c9d1d9;font:12px monospace;cursor:pointer}
  .btn:hover{background:#30363d}
  .btn.active{border-color:#388bfd;color:#388bfd}
  .btn.danger{border-color:#6e2828;color:#f85149}
  .btn.danger:hover{background:#2d1c1c}
  #log{padding:0 0 40px}
  .row{display:grid;grid-template-columns:148px 52px 110px 1fr;gap:0 10px;padding:5px 20px;border-bottom:1px solid #161b22;align-items:start}
  .row:hover{background:#161b22}
  .ts{color:#484f58;font-size:11px;padding-top:1px;white-space:nowrap}
  .lvl{font-size:10px;font-weight:600;letter-spacing:.5px;padding-top:2px;white-space:nowrap}
  .info{color:#388bfd}.warn{color:#d29922}.error{color:#f85149}.debug{color:#bc8cff}
  .agent-col{font-size:11px;color:#3fb950;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;padding-top:1px}
  .msg-col{display:flex;flex-direction:column;gap:4px;min-width:0}
  .msg-text{font-size:12px;color:#e6edf3;word-break:break-word}
  .extras{display:flex;flex-wrap:wrap;gap:4px;margin-top:2px}
  .tag{font-size:10px;padding:1px 6px;border-radius:3px;background:#21262d;border:1px solid #30363d;color:#8b949e;white-space:nowrap}
  .tag.file{background:#0d2637;border-color:#1f4b6b;color:#79c0ff}
  .tag.bytes{background:#0f2a1e;border-color:#196038;color:#56d364}
  .tag.lang{background:#1e1a2e;border-color:#3d2f6e;color:#bc8cff}
  .tag.err{background:#2d1c1c;border-color:#6e2828;color:#f85149}
  #stats{position:fixed;bottom:0;left:0;right:0;padding:6px 20px;background:#161b22;border-top:1px solid #30363d;display:flex;gap:16px;align-items:center;font-size:11px;color:#484f58}
  #stats span{color:#8b949e}
  #stats .s-info{color:#388bfd}
  #stats .s-warn{color:#d29922}
  #stats .s-error{color:#f85149}
  #stats .s-total{color:#e6edf3;font-weight:600}
  /* Modal de confirmation */
  #modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:100;align-items:center;justify-content:center}
  #modal-overlay.show{display:flex}
  #modal{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:24px;min-width:300px;max-width:400px}
  #modal h2{font-size:14px;font-weight:600;color:#fff;margin-bottom:8px}
  #modal p{font-size:12px;color:#8b949e;margin-bottom:20px;line-height:1.6}
  #modal .modal-btns{display:flex;gap:8px;justify-content:flex-end}
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
  <button class="btn danger" onclick="showClearModal()">🗑 Vider les logs</button>
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

<!-- Modal confirmation -->
<div id="modal-overlay">
  <div id="modal">
    <h2>Vider les logs ?</h2>
    <p>Cette action efface définitivement tous les logs du fichier sur le serveur. Les agents continueront de fonctionner normalement.</p>
    <div class="modal-btns">
      <button class="btn" onclick="hideClearModal()">Annuler</button>
      <button class="btn danger" onclick="confirmClear()">Vider</button>
    </div>
  </div>
</div>

<script>
const logDiv = document.getElementById('log');
const knownAgents = new Set();
let rows = [];
let paused = false;

function fmtTs(iso) {
  try {
    const d = new Date(iso);
    return d.toLocaleString('fr-FR', {day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit'}).replace(',', '');
  } catch { return iso; }
}
function esc(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

function tagClass(key, val) {
  if (key === 'fichiers' || key === 'fichier' || String(val).includes('/')) return 'file';
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
    if (Array.isArray(v)) return v.map(item => `<span class="tag ${cls}">${esc(item)}</span>`).join('');
    return `<span class="tag ${cls}">${esc(k)}: ${esc(v)}</span>`;
  }).join('');
  return `<div class="extras">${tags}</div>`;
}

function renderRow(e) {
  return `<div class="row">
    <div class="ts">${fmtTs(e.ts)}</div>
    <div class="lvl ${e.level||''}">${(e.level||'—').toUpperCase()}</div>
    <div class="agent-col">${esc(e.agent||'—')}</div>
    <div class="msg-col">
      <div class="msg-text">${esc(e.msg||JSON.stringify(e))}</div>
      ${renderExtras(e)}
    </div>
  </div>`;
}

function activeFilters() {
  return {
    lvl:    document.getElementById('f-level').value,
    ag:     document.getElementById('f-agent').value,
    search: document.getElementById('f-search').value.toLowerCase(),
  };
}

function render(data) {
  const f = activeFilters();
  const filtered = data.filter(e =>
    (!f.lvl    || e.level === f.lvl) &&
    (!f.ag     || e.agent === f.ag) &&
    (!f.search || JSON.stringify(e).toLowerCase().includes(f.search))
  );
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

function addAgentOption(agent) {
  if (!agent || knownAgents.has(agent)) return;
  knownAgents.add(agent);
  const opt = document.createElement('option');
  opt.value = opt.textContent = agent;
  document.getElementById('f-agent').appendChild(opt);
}

async function poll() {
  if (paused) return;
  try {
    const r = await fetch('/logs');
    rows = await r.json();
    rows.forEach(e => addAgentOption(e.agent));
    render(rows);
  } catch {}
}

function togglePause() {
  paused = !paused;
  const btn = document.getElementById('btn-pause');
  btn.textContent = paused ? '▶ Reprendre' : '⏸ Pause';
  btn.classList.toggle('active', paused);
}

// ── Modal clear ────────────────────────────────────────────────────────────
function showClearModal() {
  document.getElementById('modal-overlay').classList.add('show');
}
function hideClearModal() {
  document.getElementById('modal-overlay').classList.remove('show');
}
async function confirmClear() {
  hideClearModal();
  try {
    const r = await fetch('/clear', { method: 'POST' });
    if (r.ok) {
      rows = [];
      knownAgents.clear();
      // Réinitialiser le dropdown agents
      const sel = document.getElementById('f-agent');
      sel.innerHTML = '<option value="">Tous agents</option>';
      logDiv.innerHTML = '';
      updateStats([]);
      document.getElementById('count').textContent = '0 lignes';
    }
  } catch {}
}

// Fermer le modal en cliquant hors
document.getElementById('modal-overlay').addEventListener('click', function(e) {
  if (e.target === this) hideClearModal();
});

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

    def do_POST(self):
        if self.path == "/clear":
            self._clear_logs()
        else:
            self._send(404, "text/plain", b"404")

    def _clear_logs(self):
        try:
            p = Path(LOG_FILE)
            if p.exists():
                p.write_text("", encoding="utf-8")
            # Écrire une entrée de traçabilité
            entry = {
                "ts":    __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
                "agent": "log-viewer",
                "level": "warn",
                "msg":   "Logs vidés manuellement via l'interface.",
            }
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(__import__('json').dumps(entry, ensure_ascii=False) + "\n")
            self._send(200, "application/json", b'{"ok":true}')
        except Exception as e:
            self._send(500, "application/json", f'{{"error":"{e}"}}'.encode())

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
                entries.append(__import__('json').loads(line))
            except Exception:
                pass
        return __import__('json').dumps(entries[-2000:], ensure_ascii=False).encode()


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    print(f"[log-viewer] http://0.0.0.0:{port}", flush=True)
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()