#!/usr/bin/env bash
# =============================================================
# logs.sh — Consultation des logs — projet-zeroclaw
# =============================================================
# Usage :
#   ./logs.sh                        → dernières 50 entrées (tous agents)
#   ./logs.sh tail [n]               → dernières n lignes (défaut: 100)
#   ./logs.sh follow                 → suivi live du fichier JSON
#   ./logs.sh errors                 → uniquement les erreurs
#   ./logs.sh agent <nom>            → logs d'un agent spécifique
#   ./logs.sh since <durée>          → logs depuis N minutes/heures (ex: 30m, 2h)
#   ./logs.sh status                 → état des conteneurs
# =============================================================

set -euo pipefail

SERVICES=("omniroute" "zeroclaw" "mail-agent" "mail-agent-gmail")
LOG_VOLUME="projet-zeroclaw_agents-logs"
LOG_FILE="/app/logs/agents.jsonl"

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

log_error() { echo -e "${RED}[ERROR]${RESET} $*"; }
log_title() { echo -e "\n${BOLD}${CYAN}══ $* ══${RESET}\n"; }

# Formate une ligne JSONL en affichage lisible
fmt() {
    while IFS= read -r line; do
        [[ -z "$line" ]] && continue
        ts=$(echo "$line"    | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(d.get('ts','')[:19].replace('T',' '))" 2>/dev/null || echo "")
        agent=$(echo "$line" | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(d.get('agent','?'))" 2>/dev/null || echo "?")
        level=$(echo "$line" | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(d.get('level','INFO'))" 2>/dev/null || echo "INFO")
        msg=$(echo "$line"   | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(d.get('msg',''))" 2>/dev/null || echo "$line")

        case "$level" in
            ERROR) color="$RED" ;;
            WARN)  color="$YELLOW" ;;
            *)     color="$GREEN" ;;
        esac

        printf "${color}%-5s${RESET}  \033[2m%s\033[0m  ${CYAN}%-18s${RESET}  %s\n" \
            "$level" "$ts" "$agent" "$msg"
    done
}

# Lit le fichier de log via docker run sur le volume
read_log() {
    docker run --rm \
        -v "${LOG_VOLUME}:/app/logs:ro" \
        alpine:latest \
        cat "$LOG_FILE" 2>/dev/null || true
}

cmd_default() {
    log_title "Dernières 50 entrées — tous agents"
    read_log | tail -50 | fmt
}

cmd_tail() {
    local n="${1:-100}"
    log_title "Dernières $n entrées — tous agents"
    read_log | tail -"$n" | fmt
}

cmd_follow() {
    log_title "Suivi live des logs"
    echo -e "\033[2m(Ctrl+C pour quitter)\033[0m\n"
    # Affiche d'abord les 20 dernières lignes, puis suit les nouvelles
    docker run --rm \
        -v "${LOG_VOLUME}:/app/logs:ro" \
        alpine:latest \
        sh -c "tail -20 $LOG_FILE; tail -f $LOG_FILE" 2>/dev/null | fmt
}

cmd_errors() {
    log_title "Erreurs uniquement"
    read_log | python3 -c "
import sys, json
for line in sys.stdin:
    line = line.strip()
    if not line: continue
    try:
        d = json.loads(line)
        if d.get('level') in ('ERROR', 'WARN'):
            print(line)
    except: pass
" | fmt
}

cmd_agent() {
    local agent="${1:-}"
    if [[ -z "$agent" ]]; then
        log_error "Usage : $0 agent <nom>  (ex: mail-agent, mail-agent-gmail)"
        exit 1
    fi
    log_title "Logs — $agent"
    read_log | python3 -c "
import sys, json
name = sys.argv[1]
for line in sys.stdin:
    line = line.strip()
    if not line: continue
    try:
        d = json.loads(line)
        if d.get('agent') == name:
            print(line)
    except: pass
" "$agent" | fmt
}

cmd_since() {
    local duration="${1:-}"
    if [[ -z "$duration" ]]; then
        log_error "Usage : $0 since <durée>  (ex: 30m, 2h, 1h30m)"
        exit 1
    fi
    log_title "Logs depuis $duration"
    read_log | python3 -c "
import sys, json, re
from datetime import datetime, timezone, timedelta

dur = sys.argv[1]
total = 0
for val, unit in re.findall(r'(\d+)(h|m)', dur):
    total += int(val) * (60 if unit == 'h' else 1)

since = datetime.now(timezone.utc) - timedelta(minutes=total)

for line in sys.stdin:
    line = line.strip()
    if not line: continue
    try:
        d = json.loads(line)
        ts = datetime.fromisoformat(d.get('ts','').replace('Z','+00:00'))
        if ts >= since:
            print(line)
    except: pass
" "$duration" | fmt
}

cmd_status() {
    log_title "Statut des conteneurs"
    printf "%-25s %-12s\n" "CONTENEUR" "ÉTAT"
    printf "%-25s %-12s\n" "─────────────────────────" "────────────"
    for svc in "${SERVICES[@]}"; do
        local cid state
        cid=$(docker compose ps -q "$svc" 2>/dev/null || true)
        if [[ -z "$cid" ]]; then
            printf "%-25s %-12s\n" "$svc" "absent"
        else
            state=$(docker inspect --format='{{.State.Status}}' "$cid" 2>/dev/null || echo "inconnu")
            printf "%-25s %-12s\n" "$svc" "$state"
        fi
    done
    echo
    # Taille du fichier de log
    local size
    size=$(docker run --rm -v "${LOG_VOLUME}:/app/logs:ro" alpine:latest \
        sh -c "du -sh /app/logs/agents.jsonl 2>/dev/null | cut -f1 || echo '0'" 2>/dev/null || echo "?")
    echo -e "Fichier de log : ${CYAN}agents.jsonl${RESET} — ${size}"
}

cmd_help() {
    echo -e "${BOLD}logs.sh — projet-zeroclaw${RESET}"
    echo
    echo "  ./logs.sh                  Dernières 50 entrées (tous agents)"
    echo "  ./logs.sh tail [n]         Dernières n entrées (défaut: 100)"
    echo "  ./logs.sh follow           Suivi live"
    echo "  ./logs.sh errors           Erreurs et warnings uniquement"
    echo "  ./logs.sh agent <nom>      Logs d'un agent spécifique"
    echo "  ./logs.sh since <durée>    Logs depuis une durée (30m, 2h…)"
    echo "  ./logs.sh status           État des conteneurs + taille du log"
    echo
    echo -e "${CYAN}Agents :${RESET} mail-agent  mail-agent-gmail"
}

case "${1:-}" in
    "")        cmd_default ;;
    tail)      cmd_tail    "${2:-100}" ;;
    follow)    cmd_follow ;;
    errors)    cmd_errors ;;
    agent)     cmd_agent   "${2:-}" ;;
    since)     cmd_since   "${2:-}" ;;
    status)    cmd_status ;;
    help|--help) cmd_help ;;
    *) log_error "Commande inconnue : $1. Lance './logs.sh help'."; exit 1 ;;
esac