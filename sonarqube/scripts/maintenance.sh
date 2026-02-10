#!/bin/bash
# SonarQube Maintenance Script
# Provides various maintenance operations

set -e

INSTALL_DIR="/opt/sonarqube"
cd "$INSTALL_DIR"

show_menu() {
    echo ""
    echo "========================================"
    echo "SonarQube Maintenance Menu"
    echo "========================================"
    echo "1. Check system status"
    echo "2. View logs"
    echo "3. Backup database now"
    echo "4. Run cold storage archival now"
    echo "5. List backups"
    echo "6. List cold storage archives"
    echo "7. Restore from backup"
    echo "8. Database statistics"
    echo "9. Disk usage report"
    echo "10. Update SonarQube"
    echo "0. Exit"
    echo ""
    read -p "Select option: " choice
}

check_status() {
    echo ""
    echo "=== System Status ==="
    echo ""
    echo "Docker Containers:"
    docker-compose ps
    echo ""
    echo "Systemd Services:"
    systemctl status sonarqube.service --no-pager -l || true
    echo ""
    echo "Timers:"
    systemctl list-timers sonarqube-* --no-pager
    echo ""
    echo "SonarQube API Status:"
    curl -s http://localhost:9000/api/system/status | jq . || echo "Failed to connect"
}

view_logs() {
    echo ""
    echo "Select log to view:"
    echo "1. SonarQube application logs"
    echo "2. PostgreSQL logs"
    echo "3. Systemd journal (last 100 lines)"
    echo "4. Live tail (Ctrl+C to stop)"
    read -p "Choice: " log_choice

    case $log_choice in
        1) docker-compose logs --tail=100 sonarqube ;;
        2) docker-compose logs --tail=100 sonarqube-db ;;
        3) journalctl -u sonarqube.service -n 100 ;;
        4) docker-compose logs -f ;;
        *) echo "Invalid choice" ;;
    esac
}

backup_now() {
    echo ""
    echo "Running backup..."
    docker-compose run --rm sonarqube-backup /scripts/backup-db.sh
}

archive_now() {
    echo ""
    echo "Running cold storage archival..."
    docker-compose run --rm sonarqube-backup /scripts/cold-storage-archival.sh
}

list_backups() {
    echo ""
    echo "=== Recent Backups ==="
    ls -lht backups/sonarqube_backup_*.sql.gz 2>/dev/null | head -20 || echo "No backups found"
}

list_archives() {
    echo ""
    echo "=== Cold Storage Archives ==="
    ls -lht /mnt/usb-backup/sonarqube-cold-storage/* 2>/dev/null | head -20 || echo "No archives found"
}

restore_backup() {
    list_backups
    echo ""
    read -p "Enter backup filename (or full path): " backup_file
    if [ -f "$backup_file" ]; then
        /scripts/restore-backup.sh "$backup_file"
    elif [ -f "backups/$backup_file" ]; then
        /scripts/restore-backup.sh "backups/$backup_file"
    else
        echo "❌ Backup file not found"
    fi
}

db_statistics() {
    echo ""
    echo "=== Database Statistics ==="
    docker-compose exec sonarqube-db psql -U sonar -d sonarqube -c "
        SELECT
            schemaname,
            tablename,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
            pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) AS index_size
        FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
        LIMIT 20;
    "
    echo ""
    echo "=== Snapshot Count ==="
    docker-compose exec sonarqube-db psql -U sonar -d sonarqube -c "
        SELECT COUNT(*) as total_snapshots FROM snapshots;
        SELECT COUNT(*) as old_snapshots FROM snapshots WHERE created_at < NOW() - INTERVAL '180 days';
    "
}

disk_usage() {
    echo ""
    echo "=== Disk Usage Report ==="
    echo ""
    echo "Docker Volumes:"
    docker system df -v | grep sonarqube || true
    echo ""
    echo "Backup Directory:"
    du -sh backups/ || echo "No backups directory"
    echo ""
    echo "Cold Storage:"
    du -sh /mnt/usb-backup/sonarqube-cold-storage/ || echo "No cold storage directory"
    echo ""
    echo "System Disk:"
    df -h /
}

update_sonarqube() {
    echo ""
    echo "⚠️  Updating SonarQube..."
    echo "Current version:"
    docker-compose exec sonarqube cat /opt/sonarqube/lib/sonar-application-*.jar | grep -o '[0-9]*\.[0-9]*\.[0-9]*' | head -1 || echo "Unknown"
    echo ""
    read -p "Continue with update? (yes/no): " confirm
    if [ "$confirm" = "yes" ]; then
        echo "Creating backup before update..."
        backup_now
        echo "Pulling latest image..."
        docker-compose pull sonarqube
        echo "Restarting services..."
        docker-compose up -d sonarqube
        echo "✅ Update complete. Check logs for any issues."
    fi
}

# Main loop
while true; do
    show_menu
    case $choice in
        1) check_status ;;
        2) view_logs ;;
        3) backup_now ;;
        4) archive_now ;;
        5) list_backups ;;
        6) list_archives ;;
        7) restore_backup ;;
        8) db_statistics ;;
        9) disk_usage ;;
        10) update_sonarqube ;;
        0) echo "Goodbye!"; exit 0 ;;
        *) echo "Invalid option" ;;
    esac

    echo ""
    read -p "Press Enter to continue..."
done
