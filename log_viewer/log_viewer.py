"""
Log viewer minimaliste — stdlib uniquement, zéro dépendance.
Sert une page HTML sur le port 8080, accessible via tunnel SSH.
"""
import os, json, time
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

LOG_FILE = os.getenv("LOG_FILE", "/app/logs/agents.jsonl")

HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Logs — ZeroClaw</title>
<style>
  body{margin:0;background:#0d1117;color:#e6edf3;font:13px/1.6 'JetBrains Mono',monospace}
  header{padding:14px 20px;background:#161b22;border-bottom:1px solid #30363d;display:flex;align-items:center;gap:12px}
  h1{font-size:15px;font-weight:600;margin:0;color:#fff}
  .dot{width:8px;height:8px;border-radius:50%;background:#3fb950;box-shadow:0 0 6px #3fb950;animation:p 2s infinite}
  @keyframes p{0%,100%{opacity:1}50%{opacity:.3}}
  .live{color:#3fb950;font-size:11px;margin-left:auto}
  #controls{padding:10px 20px;background:#161b22;border-bottom:1px solid #30363d;display:flex;gap:8px;align-items:center}
  select,input{background:#0d1117;border:1px solid #30363d;border-radius:5px;color:#e6edf3;font:12px monospace;padding:4px 8px;outline:none}
  select:focus,input:focus{border-color:#58a6ff}
  #log{padding:12px 20px;overflow-y:auto;height:calc(100vh - 100px)}
  .row{display:grid;grid-template-columns:160px 60px 130px 1fr;gap:8px;padding:3px 0;border-bottom:1px solid #161b22}
  .row:hover{background:#161b22}
  .ts{color:#484f58;font-size:11px}
  .info{color:#58a6ff}.warn{color:#d29922}.error{color:#f85149}.debug{color:#bc8cff}
  .agent{color:#39d353;font-size:11px}
  .msg{word-break:break-all;font-size:12px}
  #count{color:#484f58;font-size:11px;margin-left:auto}
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
  <select id="f-level"><option value="">Tous niveaux</option><option>info</option><option>warn</option><option>error</option><option>debug</option></select>
  <select id="f-agent"><option value="">Tous agents</option></select>
  <input id="f-search" placeholder="Rechercher…" style="width:200px">
</div>
<div id="log"></div>
<script>
const logDiv = document.getElementById('log');
const agents = new Set();
let rows = [];

function fmt(iso){
  try{const d=new Date(iso);return d.toLocaleString('fr-FR',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit'}).replace(',',' ')}catch{return iso}
}
function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;')}

function render(){
  const lvl=document.getElementById('f-level').value;
  const ag=document.getElementById('f-agent').value;
  const q=document.getElementById('f-search').value.toLowerCase();
  const filtered=rows.filter(e=>
    (!lvl||e.level===lvl)&&(!ag||e.agent===ag)&&(!q||JSON.stringify(e).toLowerCase().includes(q))
  );
  logDiv.innerHTML=filtered.map(e=>`<div class="row">
    <div class="ts">${fmt(e.ts)}</div>
    <div class="${e.level||''}">${(e.level||'—').toUpperCase()}</div>
    <div class="agent">${esc(e.agent||'—')}</div>
    <div class="msg">${esc(e.msg||JSON.stringify(e))}</div>
  </div>`).join('');
  document.getElementById('count').textContent=filtered.length+' lignes';
  logDiv.scrollTop=logDiv.scrollHeight;
}

['f-level','f-agent','f-search'].forEach(id=>document.getElementById(id).addEventListener('input',render));

// Poll toutes les 3s
async function poll(){
  const r=await fetch('/logs');
  const data=await r.json();
  rows=data;
  data.forEach(e=>{if(e.agent&&!agents.has(e.agent)){agents.add(e.agent);const o=document.createElement('option');o.value=o.textContent=e.agent;document.getElementById('f-agent').appendChild(o)}});
  render();
}
poll();setInterval(poll,3000);
</script>
</body>
</html>"""

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_): pass  # silence access logs

    def do_GET(self):
        if self.path == "/":
            self.send(200, "text/html", HTML.encode())
        elif self.path == "/logs":
            data = self._read_logs()
            self.send(200, "application/json", data)
        else:
            self.send(404, "text/plain", b"404")

    def send(self, code, ct, body):
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
        # Dernières 2000 lignes max
        return json.dumps(entries[-2000:], ensure_ascii=False).encode()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    print(f"[log-viewer] http://0.0.0.0:{port}", flush=True)
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()