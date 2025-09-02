#!/bin/bash
# Start the AI-powered Discord bot

# Load Discord token
source /home/ubuntu/claude/.env.discord

# Export the token
export DISCORD_BOT_TOKEN

# Optional: Set Anthropic API key if available
# export ANTHROPIC_API_KEY="your-key-here"

# Start the bot
cd /home/ubuntu/claude
python3 discord_ai_bot.py