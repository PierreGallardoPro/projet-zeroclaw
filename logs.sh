#!/usr/bin/env bash
# =============================================================
# logs.sh — Gestion centralisée des logs — projet-zeroclaw
# =============================================================
# Usage :
#   ./logs.sh                        → suivi live de tous les services
#   ./logs.sh <service>              → suivi live d'un service
#   ./logs.sh export                 → export de tous les logs
#   ./logs.sh export <service>       → export d'un service
#   ./logs.sh tail <service> [n]     → dernières n lignes (défaut: 100)
#   ./logs.sh errors [service]       → uniquement les lignes d'erreur
#   ./logs.sh status                 → état et taille des logs par conteneur
#   ./logs.sh clean                  → supprime les exports de plus de 14 jours
# =============================================================

set -euo pipefail

# ── Configuration ────────────────────────────────────────────
SERVICES=("omniroute" "zeroclaw" "mail-agent" "mail-agent-gmail")
EXPORT_DIR="/var/log/zeroclaw"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# ── Couleurs terminal ─────────────────────────────────────────
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

# ── Helpers ───────────────────────────────────────────────────
log_info()  { echo -e "${GREEN}[INFO]${RESET}  $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
log_error() { echo -e "${RED}[ERROR]${RESET} $*"; }
log_title() { echo -e "\n${BOLD}${CYAN}══ $* ══${RESET}\n"; }

ensure_export_dir() {
    if [[ ! -d "$EXPORT_DIR" ]]; then
        log_info "Création du dossier d'export : $EXPORT_DIR"
        mkdir -p "$EXPORT_DIR"
        chmod 750 "$EXPORT_DIR"
    fi
}

# ── Commandes ─────────────────────────────────────────────────

# Suivi live (tous les services ou un seul)
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

# Export vers fichier texte
cmd_export() {
    local service="${1:-}"
    ensure_export_dir

    if [[ -n "$service" ]]; then
        local outfile="${EXPORT_DIR}/${service}_${TIMESTAMP}.log"
        log_info "Export de '$service' → $outfile"
        docker compose logs --no-color "$service" > "$outfile"
        log_info "Terminé. $(wc -l < "$outfile") lignes exportées."
    else
        log_title "Export de tous les services"
        for svc in "${SERVICES[@]}"; do
            local outfile="${EXPORT_DIR}/${svc}_${TIMESTAMP}.log"
            log_info "  → $svc : $outfile"
            docker compose logs --no-color "$svc" > "$outfile" 2>/dev/null || log_warn "  $svc introuvable, ignoré."
        done
        log_info "Export terminé dans $EXPORT_DIR"
    fi
}

# Dernières N lignes d'un service
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

# Filtrage des erreurs
cmd_errors() {
    local service="${1:-}"
    log_title "Lignes d'erreur${service:+ — $service}"

    if [[ -n "$service" ]]; then
        docker compose logs --no-color "$service" | grep -iE "(error|erreur|✗|exception|critical|traceback)" || echo "Aucune erreur trouvée."
    else
        for svc in "${SERVICES[@]}"; do
            local found
            found=$(docker compose logs --no-color "$svc" 2>/dev/null | grep -iE "(error|erreur|✗|exception|critical|traceback)" || true)
            if [[ -n "$found" ]]; then
                echo -e "${YELLOW}[$svc]${RESET}"
                echo "$found"
                echo
            fi
        done
    fi
}

# Statut et taille des logs par conteneur
cmd_status() {
    log_title "Statut des conteneurs & taille des logs"

    printf "%-25s %-12s %s\n" "CONTENEUR" "ÉTAT" "TAILLE LOG"
    printf "%-25s %-12s %s\n" "─────────────────────────" "────────────" "──────────"

    for svc in "${SERVICES[@]}"; do
        # Trouver l'ID du conteneur
        local cid
        cid=$(docker compose ps -q "$svc" 2>/dev/null || true)

        if [[ -z "$cid" ]]; then
            printf "%-25s %-12s %s\n" "$svc" "absent" "-"
            continue
        fi

        local state
        state=$(docker inspect --format='{{.State.Status}}' "$cid" 2>/dev/null || echo "inconnu")

        local log_path
        log_path=$(docker inspect --format='{{.LogPath}}' "$cid" 2>/dev/null || true)

        local size="-"
        if [[ -n "$log_path" && -f "$log_path" ]]; then
            size=$(du -sh "$log_path" 2>/dev/null | cut -f1 || echo "-")
        fi

        printf "%-25s %-12s %s\n" "$svc" "$state" "$size"
    done

    echo
    if [[ -d "$EXPORT_DIR" ]]; then
        log_info "Exports dans $EXPORT_DIR : $(find "$EXPORT_DIR" -name '*.log' | wc -l) fichier(s)"
    fi
}

# Nettoyage des exports anciens
cmd_clean() {
    ensure_export_dir
    log_info "Suppression des exports de plus de 14 jours dans $EXPORT_DIR..."
    local count
    count=$(find "$EXPORT_DIR" -name "*.log" -mtime +14 | wc -l)
    find "$EXPORT_DIR" -name "*.log" -mtime +14 -delete
    log_info "$count fichier(s) supprimé(s)."
}

# ── Aide ──────────────────────────────────────────────────────
cmd_help() {
    echo -e "${BOLD}logs.sh — Gestion des logs — projet-zeroclaw${RESET}"
    echo
    echo "  ./logs.sh                        Suivi live de tous les services"
    echo "  ./logs.sh <service>              Suivi live d'un service"
    echo "  ./logs.sh export                 Export de tous les services"
    echo "  ./logs.sh export <service>       Export d'un service"
    echo "  ./logs.sh tail <service> [n]     Dernières n lignes (défaut: 100)"
    echo "  ./logs.sh errors [service]       Lignes d'erreur uniquement"
    echo "  ./logs.sh status                 État et taille des logs"
    echo "  ./logs.sh clean                  Supprime les exports > 14 jours"
    echo
    echo -e "${CYAN}Services disponibles :${RESET} ${SERVICES[*]}"
}

# ── Dispatch ──────────────────────────────────────────────────
case "${1:-}" in
    "")           cmd_follow ;;
    export)       cmd_export  "${2:-}" ;;
    tail)         cmd_tail    "${2:-}" "${3:-100}" ;;
    errors)       cmd_errors  "${2:-}" ;;
    status)       cmd_status ;;
    clean)        cmd_clean ;;
    help|--help)  cmd_help ;;
    *)            cmd_follow  "${1}" ;;
esac
