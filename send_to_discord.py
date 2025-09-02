#!/usr/bin/env python3
"""
Send messages to Discord channels directly
"""

import os
import sys
import asyncio
import discord
from discord.ext import commands

async def send_message(channel_name: str, message: str):
    """Send a message to a specific Discord channel"""
    
    # Load Discord token
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        # Try loading from .env.discord
        env_file = '/home/ubuntu/claude/.env.discord'
        if os.path.exists(env_file):
            with open(env_file) as f:
                for line in f:
                    if line.startswith('DISCORD_BOT_TOKEN='):
                        token = line.split('=', 1)[1].strip()
                        break
    
    if not token:
        print("Error: Discord token not found")
        return False
    
    # Create a minimal bot client
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)
    
    @client.event
    async def on_ready():
        """Send message once connected"""
        # Find the channel
        for guild in client.guilds:
            for channel in guild.text_channels:
                if channel.name == channel_name:
                    await channel.send(message)
                    print(f"Sent to #{channel_name}: {message}")
                    await client.close()
                    return
        
        print(f"Channel #{channel_name} not found")
        await client.close()
    
    try:
        await client.start(token)
    except:
        pass
    
    return True

def send_to_channel(channel: str, msg: str):
    """Synchronous wrapper for sending messages"""
    asyncio.run(send_message(channel, msg))

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 send_to_discord.py <channel> <message>")
        sys.exit(1)
    
    channel = sys.argv[1]
    message = " ".join(sys.argv[2:])
    send_to_channel(channel, message)