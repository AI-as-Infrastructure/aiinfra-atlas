#!/bin/bash

# ATLAS Production Health Check Script
# Monitors system health, services, logs, and resources
# Usage: ./health_check.sh [--verbose] [--json] [--critical-only]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname $(dirname "$SCRIPT_DIR"))"
LOG_DIR="/var/log"
APP_DIR="/opt/atlas"
VERBOSE=false
JSON_OUTPUT=false
CRITICAL_ONLY=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --json|-j)
            JSON_OUTPUT=true
            shift
            ;;
        --critical-only|-c)
            CRITICAL_ONLY=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [--verbose] [--json] [--critical-only]"
            echo "  --verbose, -v      Show detailed output"
            echo "  --json, -j         Output in JSON format"
            echo "  --critical-only, -c Show only critical issues"
            exit 0
            ;;
        *)
            echo "Unknown option $1"
            exit 1
            ;;
    esac
done

# Health check results
declare -A health_results
declare -a critical_issues
declare -a warnings
declare -a info_messages

# Utility functions
log_info() {
    if [[ "$JSON_OUTPUT" != "true" ]]; then
        echo -e "${BLUE}ℹ${NC} $1"
    fi
    info_messages+=("$1")
}

log_success() {
    if [[ "$JSON_OUTPUT" != "true" ]]; then
        echo -e "${GREEN}✅${NC} $1"
    fi
    health_results["$1"]="OK"
}

log_warning() {
    if [[ "$JSON_OUTPUT" != "true" ]]; then
        echo -e "${YELLOW}⚠️${NC} $1"
    fi
    health_results["$1"]="WARNING"
    warnings+=("$1")
}

log_critical() {
    if [[ "$JSON_OUTPUT" != "true" ]]; then
        echo -e "${RED}❌${NC} $1"
    fi
    health_results["$1"]="CRITICAL"
    critical_issues+=("$1")
}

log_verbose() {
    if [[ "$VERBOSE" == "true" && "$JSON_OUTPUT" != "true" ]]; then
        echo -e "  ${NC}$1"
    fi
}

print_header() {
    if [[ "$JSON_OUTPUT" != "true" ]]; then
        echo -e "\n${BOLD}${BLUE}=== $1 ===${NC}"
    fi
}

# Check if running as appropriate user
check_permissions() {
    print_header "Permission Check"
    
    if [[ $EUID -eq 0 ]]; then
        log_info "Running as root - full system access available"
    elif groups | grep -q "atlas_deploy\|sudo"; then
        log_success "Running with appropriate permissions (atlas_deploy/sudo group)"
    else
        log_warning "Limited permissions - some checks may not be available"
    fi
}

# Check disk space
check_disk_space() {
    print_header "Disk Space"
    
    # Check root filesystem
    root_usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [[ $root_usage -gt 90 ]]; then
        log_critical "Root filesystem usage critical: ${root_usage}%"
    elif [[ $root_usage -gt 80 ]]; then
        log_warning "Root filesystem usage high: ${root_usage}%"
    else
        log_success "Root filesystem usage OK: ${root_usage}%"
    fi
    
    # Check /opt/atlas if it exists
    if [[ -d "$APP_DIR" ]]; then
        app_usage=$(df "$APP_DIR" | awk 'NR==2 {print $5}' | sed 's/%//')
        if [[ $app_usage -gt 90 ]]; then
            log_critical "Application filesystem usage critical: ${app_usage}%"
        elif [[ $app_usage -gt 80 ]]; then
            log_warning "Application filesystem usage high: ${app_usage}%"
        else
            log_success "Application filesystem usage OK: ${app_usage}%"
        fi
        
        # Check application directory size
        if command -v du >/dev/null 2>&1; then
            app_size=$(du -sh "$APP_DIR" 2>/dev/null | awk '{print $1}')
            log_verbose "Application directory size: $app_size"
        fi
    fi
    
    # Check for large log files
    if [[ -d "$LOG_DIR" ]]; then
        large_logs=$(find "$LOG_DIR" -name "*.log" -size +100M 2>/dev/null | head -5)
        if [[ -n "$large_logs" ]]; then
            log_warning "Large log files detected (>100MB)"
            if [[ "$VERBOSE" == "true" ]]; then
                echo "$large_logs" | while read -r logfile; do
                    size=$(du -h "$logfile" | awk '{print $1}')
                    log_verbose "$logfile: $size"
                done
            fi
        else
            log_success "No large log files detected"
        fi
    fi
}

# Check memory usage
check_memory() {
    print_header "Memory Usage"
    
    # Get memory info
    if command -v free >/dev/null 2>&1; then
        mem_info=$(free -m)
        total_mem=$(echo "$mem_info" | awk 'NR==2 {print $2}')
        used_mem=$(echo "$mem_info" | awk 'NR==2 {print $3}')
        available_mem=$(echo "$mem_info" | awk 'NR==2 {print $7}')
        
        if [[ -n "$available_mem" && -n "$total_mem" ]]; then
            mem_usage=$((100 * (total_mem - available_mem) / total_mem))
            
            if [[ $mem_usage -gt 90 ]]; then
                log_critical "Memory usage critical: ${mem_usage}% (${available_mem}MB available)"
            elif [[ $mem_usage -gt 80 ]]; then
                log_warning "Memory usage high: ${mem_usage}% (${available_mem}MB available)"
            else
                log_success "Memory usage OK: ${mem_usage}% (${available_mem}MB available)"
            fi
            
            log_verbose "Total: ${total_mem}MB, Used: ${used_mem}MB, Available: ${available_mem}MB"
        fi
    else
        log_warning "Cannot check memory usage - 'free' command not available"
    fi
}

# Check system services
check_services() {
    print_header "System Services"
    
    # Services to check
    services=("nginx" "gunicorn" "redis-server" "llm-worker")
    
    for service in "${services[@]}"; do
        if systemctl is-active --quiet "$service" 2>/dev/null; then
            log_success "$service is running"
            
            if [[ "$VERBOSE" == "true" ]]; then
                uptime=$(systemctl show "$service" --property=ActiveEnterTimestamp --value 2>/dev/null)
                if [[ -n "$uptime" ]]; then
                    log_verbose "Started: $uptime"
                fi
            fi
        else
            if systemctl list-unit-files | grep -q "^${service}\.service"; then
                log_critical "$service is not running"
            else
                log_info "$service is not installed/configured"
            fi
        fi
    done
}

# Check Redis health
check_redis() {
    print_header "Redis Health"
    
    # Load environment to get Redis password
    if [[ -f "$APP_DIR/config/.env.production" ]]; then
        # Extract password from REDIS_URL
        redis_url=$(grep "^REDIS_URL=" "$APP_DIR/config/.env.production" | cut -d'=' -f2)
        redis_password=$(echo "$redis_url" | sed -n 's/.*redis:\/\/:\([^@]*\)@.*/\1/p')
        
        if [[ -n "$redis_password" ]] && command -v redis-cli >/dev/null 2>&1; then
            # Test Redis connection
            if redis_cli -a "$redis_password" ping >/dev/null 2>&1; then
                log_success "Redis connection OK"
                
                if [[ "$VERBOSE" == "true" ]]; then
                    # Get Redis info
                    connected_clients=$(redis-cli -a "$redis_password" info clients 2>/dev/null | grep "connected_clients:" | cut -d: -f2 | tr -d '\r')
                    used_memory=$(redis-cli -a "$redis_password" info memory 2>/dev/null | grep "used_memory_human:" | cut -d: -f2 | tr -d '\r')
                    
                    if [[ -n "$connected_clients" ]]; then
                        log_verbose "Connected clients: $connected_clients"
                    fi
                    if [[ -n "$used_memory" ]]; then
                        log_verbose "Used memory: $used_memory"
                    fi
                fi
            else
                log_critical "Redis connection failed"
            fi
        else
            log_warning "Cannot test Redis - missing password or redis-cli"
        fi
    else
        log_warning "Cannot test Redis - production config not found"
    fi
}

# Check application logs
check_logs() {
    print_header "Application Logs"
    
    # Check for recent errors in systemd journals
    if command -v journalctl >/dev/null 2>&1; then
        # Check for errors in the last hour
        recent_errors=$(journalctl --since "1 hour ago" --priority=err --no-pager -q 2>/dev/null | wc -l)
        if [[ $recent_errors -gt 10 ]]; then
            log_critical "$recent_errors system errors in the last hour"
        elif [[ $recent_errors -gt 0 ]]; then
            log_warning "$recent_errors system errors in the last hour"
        else
            log_success "No recent system errors"
        fi
        
        # Check application-specific logs
        for service in gunicorn llm-worker nginx; do
            if systemctl is-active --quiet "$service" 2>/dev/null; then
                service_errors=$(journalctl -u "$service" --since "1 hour ago" --priority=err --no-pager -q 2>/dev/null | wc -l)
                if [[ $service_errors -gt 5 ]]; then
                    log_warning "$service: $service_errors errors in last hour"
                elif [[ "$VERBOSE" == "true" ]]; then
                    log_verbose "$service: $service_errors errors in last hour"
                fi
            fi
        done
    fi
    
    # Check application log files if they exist
    app_log_dirs=("$APP_DIR/logs" "/var/log/atlas" "/var/log/nginx")
    for log_dir in "${app_log_dirs[@]}"; do
        if [[ -d "$log_dir" ]]; then
            recent_log_errors=$(find "$log_dir" -name "*.log" -newermt "1 hour ago" -exec grep -l "ERROR\|CRITICAL\|Exception" {} \; 2>/dev/null | wc -l)
            if [[ $recent_log_errors -gt 0 ]]; then
                log_warning "Found error patterns in $recent_log_errors recent log files in $log_dir"
            elif [[ "$VERBOSE" == "true" ]]; then
                log_verbose "No error patterns in recent logs in $log_dir"
            fi
        fi
    done
}

# Check network connectivity
check_network() {
    print_header "Network Connectivity"
    
    # Check if we can resolve DNS
    if nslookup google.com >/dev/null 2>&1; then
        log_success "DNS resolution working"
    else
        log_critical "DNS resolution failed"
    fi
    
    # Check if application port is listening
    if command -v netstat >/dev/null 2>&1; then
        if netstat -tuln | grep -q ":80\|:443\|:8000"; then
            log_success "Web server ports are listening"
        else
            log_warning "No web server ports detected"
        fi
    elif command -v ss >/dev/null 2>&1; then
        if ss -tuln | grep -q ":80\|:443\|:8000"; then
            log_success "Web server ports are listening"
        else
            log_warning "No web server ports detected"
        fi
    fi
}

# Check system load
check_load() {
    print_header "System Load"
    
    if [[ -f /proc/loadavg ]]; then
        load_1min=$(awk '{print $1}' /proc/loadavg)
        load_5min=$(awk '{print $2}' /proc/loadavg)
        load_15min=$(awk '{print $3}' /proc/loadavg)
        
        # Get number of CPU cores
        cpu_cores=$(nproc)
        
        # Convert load to percentage (load/cores * 100)
        load_percent=$(echo "$load_1min $cpu_cores" | awk '{printf "%.0f", $1/$2*100}')
        
        if [[ $load_percent -gt 90 ]]; then
            log_critical "System load critical: ${load_1min} (${load_percent}% of ${cpu_cores} cores)"
        elif [[ $load_percent -gt 70 ]]; then
            log_warning "System load high: ${load_1min} (${load_percent}% of ${cpu_cores} cores)"
        else
            log_success "System load OK: ${load_1min} (${load_percent}% of ${cpu_cores} cores)"
        fi
        
        if [[ "$VERBOSE" == "true" ]]; then
            log_verbose "Load averages: 1min=${load_1min}, 5min=${load_5min}, 15min=${load_15min}"
            log_verbose "CPU cores: ${cpu_cores}"
        fi
    fi
}

# Check application-specific health
check_application() {
    print_header "Application Health"
    
    if [[ -d "$APP_DIR" ]]; then
        log_success "Application directory exists: $APP_DIR"
        
        # Check if virtual environment exists
        if [[ -d "$APP_DIR/.venv" ]]; then
            log_success "Python virtual environment exists"
        else
            log_warning "Python virtual environment not found"
        fi
        
        # Check if config files exist
        if [[ -f "$APP_DIR/config/.env.production" ]]; then
            log_success "Production configuration exists"
        else
            log_critical "Production configuration missing"
        fi
        
        # Check if main application files exist
        if [[ -f "$APP_DIR/backend/app.py" ]]; then
            log_success "Main application file exists"
        else
            log_critical "Main application file missing"
        fi
        
        # Check vector store
        if [[ -f "$APP_DIR/config/.env.production" ]]; then
            chroma_dir=$(grep "^CHROMA_PERSIST_DIRECTORY=" "$APP_DIR/config/.env.production" 2>/dev/null | cut -d'=' -f2 | tr -d '"')
            if [[ -n "$chroma_dir" && -d "$APP_DIR/$chroma_dir" ]]; then
                log_success "Vector store directory exists"
            else
                log_warning "Vector store directory not found"
            fi
        fi
    else
        log_critical "Application directory not found: $APP_DIR"
    fi
}

# Generate summary
print_summary() {
    if [[ "$JSON_OUTPUT" == "true" ]]; then
        # JSON output
        echo "{"
        echo "  \"timestamp\": \"$(date -Iseconds)\","
        echo "  \"hostname\": \"$(hostname)\","
        echo "  \"status\": \"$(if [[ ${#critical_issues[@]} -eq 0 ]]; then echo "OK"; else echo "CRITICAL"; fi)\","
        echo "  \"critical_issues\": $(printf '%s\n' "${critical_issues[@]}" | jq -R . | jq -s .)"
        echo "  \"warnings\": $(printf '%s\n' "${warnings[@]}" | jq -R . | jq -s .)"
        echo "  \"info\": $(printf '%s\n' "${info_messages[@]}" | jq -R . | jq -s .)"
        echo "}"
    else
        echo
        echo -e "${BOLD}${BLUE}=== Health Check Summary ===${NC}"
        echo -e "Timestamp: $(date)"
        echo -e "Hostname: $(hostname)"
        echo
        
        if [[ ${#critical_issues[@]} -gt 0 ]]; then
            echo -e "${RED}CRITICAL ISSUES DETECTED:${NC}"
            for issue in "${critical_issues[@]}"; do
                echo -e "  ${RED}❌${NC} $issue"
            done
            echo
        fi
        
        if [[ ${#warnings[@]} -gt 0 && "$CRITICAL_ONLY" != "true" ]]; then
            echo -e "${YELLOW}WARNINGS:${NC}"
            for warning in "${warnings[@]}"; do
                echo -e "  ${YELLOW}⚠️${NC} $warning"
            done
            echo
        fi
        
        # Overall status
        if [[ ${#critical_issues[@]} -eq 0 ]]; then
            if [[ ${#warnings[@]} -eq 0 ]]; then
                echo -e "${GREEN}✅ SYSTEM HEALTHY${NC}"
            else
                echo -e "${YELLOW}⚠️ SYSTEM OK WITH WARNINGS${NC}"
            fi
        else
            echo -e "${RED}❌ SYSTEM CRITICAL${NC}"
        fi
        
        echo -e "\nRun with ${BOLD}--verbose${NC} for detailed output"
        echo -e "Run with ${BOLD}--json${NC} for machine-readable output"
        echo -e "Run with ${BOLD}--critical-only${NC} to see only critical issues"
    fi
}

# Main execution
main() {
    if [[ "$JSON_OUTPUT" != "true" ]]; then
        echo -e "${BOLD}${BLUE}ATLAS Production Health Check${NC}"
        echo -e "Started at: $(date)"
        echo
    fi
    
    # Run all checks
    check_permissions
    check_disk_space
    check_memory
    check_load
    check_services
    check_redis
    check_network
    check_application
    
    if [[ "$CRITICAL_ONLY" != "true" ]]; then
        check_logs
    fi
    
    print_summary
    
    # Exit with appropriate code
    if [[ ${#critical_issues[@]} -gt 0 ]]; then
        exit 1
    else
        exit 0
    fi
}

# Run the script
main "$@"