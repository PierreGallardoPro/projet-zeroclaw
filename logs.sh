#!/usr/bin/env bash
# =============================================================
# logs.sh — Consultation des logs — projet-zeroclaw
# =============================================================
# Usage :
#   ./logs.sh                        → suivi live de tous les services
#   ./logs.sh <service>              → suivi live d'un service
#   ./logs.sh tail <service> [n]     → dernières n lignes (défaut: 100)
#   ./logs.sh errors [service]       → uniquement les lignes d'erreur
#   ./logs.sh status                 → état des conteneurs
#   ./logs.sh since <service> <dur>  → logs depuis une durée (ex: 1h, 30m)
# =============================================================

set -euo pipefail

SERVICES=("omniroute" "zeroclaw" "mail_agent" "mail_agent_gmail")

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${RESET}  $*"; }
log_error() { echo -e "${RED}[ERROR]${RESET} $*"; }
log_title() { echo -e "\n${BOLD}${CYAN}══ $* ══${RESET}\n"; }

cmd_follow() {
    local service="${1:-}"
    if [[ -n "$service" ]]; then
        log_title "Logs live — $service"
        docker compose logs -f --tail=50 "$service"
    else
        log_title "Logs live — tous les services"
        docker compose logs -f --tail=50
    fi
}

cmd_tail() {
    local service="${1:-}"
    local lines="${2:-100}"
    if [[ -z "$service" ]]; then
        log_error "Usage : $0 tail <service> [n]"
        exit 1
    fi
    log_title "Dernières $lines lignes — $service"
    docker compose logs --tail="$lines" "$service"
}

cmd_errors() {
    local service="${1:-}"
    log_title "Lignes d'erreur${service:+ — $service}"
    if [[ -n "$service" ]]; then
        docker compose logs --no-color "$service" \
            | grep -iE "(error|erreur|✗|exception|critical|traceback)" \
            || echo "Aucune erreur trouvée."
    else
        for svc in "${SERVICES[@]}"; do
            local found
            found=$(docker compose logs --no-color "$svc" 2>/dev/null \
                | grep -iE "(error|erreur|✗|exception|critical|traceback)" || true)
            if [[ -n "$found" ]]; then
                echo -e "${YELLOW}[$svc]${RESET}"
                echo "$found"
                echo
            fi
        done
    fi
}

cmd_since() {
    local service="${1:-}"
    local duration="${2:-}"
    if [[ -z "$service" || -z "$duration" ]]; then
        log_error "Usage : $0 since <service> <durée>  (ex: 1h, 30m, 2h30m)"
        exit 1
    fi
    log_title "Logs des dernières $duration — $service"
    docker compose logs --since="$duration" "$service"
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
}

cmd_help() {
    echo -e "${BOLD}logs.sh — projet-zeroclaw${RESET}"
    echo
    echo "  ./logs.sh                        Suivi live de tous les services"
    echo "  ./logs.sh <service>              Suivi live d'un service"
    echo "  ./logs.sh tail <service> [n]     Dernières n lignes (défaut: 100)"
    echo "  ./logs.sh errors [service]       Lignes d'erreur uniquement"
    echo "  ./logs.sh since <service> <dur>  Logs depuis une durée (1h, 30m…)"
    echo "  ./logs.sh status                 État des conteneurs"
    echo
    echo -e "${CYAN}Services :${RESET} ${SERVICES[*]}"
}

case "${1:-}" in
    "")           cmd_follow ;;
    tail)         cmd_tail   "${2:-}" "${3:-100}" ;;
    errors)       cmd_errors "${2:-}" ;;
    since)        cmd_since  "${2:-}" "${3:-}" ;;
    status)       cmd_status ;;
    help|--help)  cmd_help ;;
    *)            cmd_follow "${1}" ;;
esac