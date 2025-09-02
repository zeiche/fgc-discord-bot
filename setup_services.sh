#!/bin/bash
# Setup script for tournament tracker services

set -e

echo "Tournament Tracker Service Setup"
echo "================================"

# Function to setup web service
setup_web_service() {
    echo "Setting up web editor service..."
    
    # Make script executable
    chmod +x /home/ubuntu/claude/tournament_tracker/editor_web_service.py
    
    # Copy service file
    sudo cp /home/ubuntu/claude/tournament-web.service /etc/systemd/system/
    
    # Reload systemd
    sudo systemctl daemon-reload
    
    # Enable and start service
    sudo systemctl enable tournament-web.service
    sudo systemctl start tournament-web.service
    
    echo "✅ Web service installed and started"
}

# Function to setup Discord bot service
setup_discord_service() {
    echo "Setting up Discord bot service..."
    
    # Check if token is set
    if [ -z "$1" ]; then
        echo "❌ Error: Discord bot token required!"
        echo "Usage: $0 setup-discord YOUR_BOT_TOKEN"
        return 1
    fi
    
    # Make script executable
    chmod +x /home/ubuntu/claude/discord_bot_service.py
    
    # Update service file with token
    sed -i "s/YOUR_BOT_TOKEN_HERE/$1/" /home/ubuntu/claude/discord-bot.service
    
    # Copy service file
    sudo cp /home/ubuntu/claude/discord-bot.service /etc/systemd/system/
    
    # Reload systemd
    sudo systemctl daemon-reload
    
    # Enable and start service
    sudo systemctl enable discord-bot.service
    sudo systemctl start discord-bot.service
    
    echo "✅ Discord bot service installed and started"
}

# Function to check service status
check_status() {
    echo "Service Status:"
    echo "--------------"
    
    # Check web service
    if systemctl is-active --quiet tournament-web.service; then
        echo "✅ Web Editor: Running on http://localhost:8081"
    else
        echo "❌ Web Editor: Not running"
    fi
    
    # Check Discord bot
    if systemctl is-active --quiet discord-bot.service; then
        echo "✅ Discord Bot: Running"
    else
        echo "❌ Discord Bot: Not running"
    fi
    
    echo ""
    echo "Use these commands to manage services:"
    echo "  sudo systemctl status tournament-web"
    echo "  sudo systemctl status discord-bot"
    echo "  sudo systemctl restart tournament-web"
    echo "  sudo systemctl restart discord-bot"
    echo "  sudo journalctl -u tournament-web -f"
    echo "  sudo journalctl -u discord-bot -f"
}

# Main script logic
case "$1" in
    setup-web)
        setup_web_service
        ;;
    setup-discord)
        setup_discord_service "$2"
        ;;
    setup-all)
        if [ -z "$2" ]; then
            echo "❌ Error: Discord bot token required!"
            echo "Usage: $0 setup-all YOUR_BOT_TOKEN"
            exit 1
        fi
        setup_web_service
        setup_discord_service "$2"
        ;;
    status)
        check_status
        ;;
    stop-all)
        sudo systemctl stop tournament-web.service
        sudo systemctl stop discord-bot.service
        echo "✅ All services stopped"
        ;;
    start-all)
        sudo systemctl start tournament-web.service
        sudo systemctl start discord-bot.service
        echo "✅ All services started"
        ;;
    remove-all)
        sudo systemctl stop tournament-web.service 2>/dev/null || true
        sudo systemctl stop discord-bot.service 2>/dev/null || true
        sudo systemctl disable tournament-web.service 2>/dev/null || true
        sudo systemctl disable discord-bot.service 2>/dev/null || true
        sudo rm -f /etc/systemd/system/tournament-web.service
        sudo rm -f /etc/systemd/system/discord-bot.service
        sudo systemctl daemon-reload
        echo "✅ All services removed"
        ;;
    *)
        echo "Tournament Tracker Service Manager"
        echo ""
        echo "Usage:"
        echo "  $0 setup-web              - Setup web editor service only"
        echo "  $0 setup-discord TOKEN    - Setup Discord bot with token"
        echo "  $0 setup-all TOKEN        - Setup both services"
        echo "  $0 status                 - Check service status"
        echo "  $0 start-all              - Start all services"
        echo "  $0 stop-all               - Stop all services"
        echo "  $0 remove-all             - Remove all services"
        echo ""
        echo "Example:"
        echo "  $0 setup-all YOUR_DISCORD_BOT_TOKEN"
        ;;
esac