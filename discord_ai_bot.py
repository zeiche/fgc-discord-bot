#!/usr/bin/env python3
"""
AI-Powered Discord bot for tournament tracker
Uses Claude AI for natural language understanding
"""
import os
import sys
import logging
import discord
from discord.ext import commands
import asyncio
import re

# Add tournament_tracker to path
sys.path.insert(0, '/home/ubuntu/claude/tournament_tracker')

from claude_ai import get_ai_response, get_claude_ai
from database_utils import get_summary_stats, get_session, get_attendance_rankings, get_player_rankings
from claude_dev_helper import extract_developer_commands, get_command_suggestion
from async_handler import ProgressiveTask, StreamingResponse, run_with_progress
from sqlalchemy import text
import subprocess
import traceback

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/ubuntu/claude/discord_bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('discord_bot')

class AIBot(commands.Bot):
    """Bot powered by Claude AI"""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(
            command_prefix='!',
            intents=intents,
            description='AI-powered Tournament Tracker'
        )
        
        # Initialize Claude AI with context
        self.ai = get_claude_ai()
        if self.ai.enabled:
            # Update AI with current database stats
            try:
                stats = get_summary_stats()
                self.ai.update_context({'stats': stats})
            except Exception as e:
                logger.error(f"Could not update AI context: {e}")

# Create bot instance
bot = AIBot()

async def handle_developer_execution(message):
    """Handle natural language execution requests in developer channel"""
    msg_lower = message.content.lower()
    
    # Database queries
    if any(word in msg_lower for word in ['query', 'select', 'show me from database', 'database']):
        if 'select' in msg_lower or 'show' in msg_lower:
            # Extract SQL query
            sql_match = None
            if 'select' in msg_lower:
                sql_match = message.content[message.content.lower().index('select'):]
            elif 'organizations' in msg_lower:
                sql_match = "SELECT display_name, id FROM organizations LIMIT 10"
            elif 'tournaments' in msg_lower:
                sql_match = "SELECT name, num_attendees FROM tournaments ORDER BY num_attendees DESC LIMIT 10"
            
            if sql_match:
                await message.channel.send(f"Executing query: `{sql_match}`")
                try:
                    with get_session() as session:
                        result = session.execute(text(sql_match))
                        rows = result.fetchall()
                        
                        if not rows:
                            await message.channel.send("No results found.")
                        else:
                            output = f"```\nFound {len(rows)} results:\n"
                            if hasattr(result, 'keys'):
                                output += " | ".join(result.keys()) + "\n"
                                output += "-" * 50 + "\n"
                            
                            for row in rows[:10]:
                                output += " | ".join(str(val)[:30] for val in row) + "\n"
                            
                            if len(rows) > 10:
                                output += f"\n... and {len(rows) - 10} more rows"
                            output += "```"
                            
                            await message.channel.send(output[:2000])
                        return True
                except Exception as e:
                    await message.channel.send(f"❌ Query error: {e}")
                    return True
    
    # File reading
    if any(word in msg_lower for word in ['read file', 'show file', 'cat', 'show me']) and '/' in message.content:
        # Extract file path
        import re
        paths = re.findall(r'/[\w/\-_.]+', message.content)
        if paths:
            file_path = paths[0]
            await message.channel.send(f"Reading file: `{file_path}`")
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    if len(content) > 1900:
                        content = content[:1900] + "\n... (truncated)"
                    await message.channel.send(f"```\n{content}\n```")
                return True
            except Exception as e:
                await message.channel.send(f"❌ Error reading file: {e}")
                return True
    
    # Python execution
    if any(word in msg_lower for word in ['run python', 'execute', 'exec', 'run code']):
        # Extract code block
        code_match = re.search(r'```(?:python)?\n?(.*?)```', message.content, re.DOTALL)
        if code_match:
            code = code_match.group(1)
            await message.channel.send("Executing Python code...")
            try:
                # Create safe namespace
                namespace = {
                    'get_session': get_session,
                    'get_attendance_rankings': get_attendance_rankings,
                    'get_summary_stats': get_summary_stats
                }
                
                # Capture output
                from io import StringIO
                import sys
                old_stdout = sys.stdout
                sys.stdout = output_buffer = StringIO()
                
                exec(code, namespace)
                
                sys.stdout = old_stdout
                output = output_buffer.getvalue()
                
                if output:
                    await message.channel.send(f"```\n{output[:1900]}\n```")
                else:
                    await message.channel.send("✅ Code executed successfully (no output)")
                return True
            except Exception as e:
                await message.channel.send(f"❌ Execution error: {e}")
                return True
    
    # Top organizations shortcut with progress
    if 'top organizations' in msg_lower or 'top orgs' in msg_lower:
        progress = ProgressiveTask(message.channel, "Organization Rankings")
        await progress.start()
        try:
            await progress.update("Querying database...")
            rankings = get_attendance_rankings(10)
            await progress.update(f"Found {len(rankings)} organizations")
            
            output = "**Top 10 Organizations by Attendance:**\n```\n"
            for i, org in enumerate(rankings, 1):
                output += f"{i:2}. {org['display_name'][:30]:30} - {org['total_attendance']:,} attendees ({org['tournament_count']} events)\n"
            output += "```"
            
            await progress.complete("Rankings calculated")
            await message.channel.send(output)
            return True
        except Exception as e:
            await progress.error(str(e))
            return True
    
    # Top players with progress updates
    if 'top players' in msg_lower or 'player rankings' in msg_lower:
        progress = ProgressiveTask(message.channel, "Player Rankings")
        await progress.start()
        try:
            await progress.update("Calculating player scores...")
            
            # Determine event type
            event_type = 'all'
            if 'singles' in msg_lower:
                event_type = 'singles'
                await progress.update("Filtering for singles events")
            elif 'doubles' in msg_lower:
                event_type = 'doubles'
                await progress.update("Filtering for doubles events")
            
            rankings = get_player_rankings(10, event_type, 1)
            await progress.update(f"Ranked {len(rankings)} players")
            
            output = f"**Top Players ({event_type.title()}):**\n```\n"
            for r in rankings:
                output += f"{r['rank']:2}. {r['gamer_tag'][:20]:20} - {r['total_points']} pts ({r['tournament_count']} events)\n"
            output += "```"
            
            await progress.complete()
            await message.channel.send(output)
            return True
        except Exception as e:
            await progress.error(str(e))
            return True
    
    return False

@bot.event
async def on_ready():
    logger.info(f'AI Bot ready as {bot.user}')
    logger.info(f'Guilds: {len(bot.guilds)}')
    logger.info(f'Claude AI enabled: {bot.ai.enabled}')
    
    # Load developer commands if available
    try:
        from discord_dev_commands import setup as dev_setup
        await dev_setup(bot)
        logger.info('Developer commands loaded')
    except Exception as e:
        logger.error(f'Failed to load developer commands: {e}')

@bot.event
async def on_message(message):
    # Ignore bot's own messages (but allow messages from other bots for testing)
    if message.author == bot.user:
        return
    
    # Process commands first (anything starting with !)
    if message.content.startswith('!'):
        await bot.process_commands(message)
        return
    
    # Check if this is a DM
    is_dm = isinstance(message.channel, discord.DMChannel)
    
    if is_dm:
        # Handle DMs - private conversations
        logger.info(f'[DM] {message.author}: {message.content}')
        
        # In DMs, always respond (no channel restrictions)
        msg_lower = message.content.lower()
        
        # Handle quick status checks
        if any(phrase in msg_lower for phrase in ['are you there', 'you there', 'still there', 'hello?', 'status']):
            if len(msg_lower) < 20:
                await message.channel.send("Yes")
                return
        
        # Check for heat map requests FIRST in DMs
        if any(word in msg_lower for word in ['heat map', 'heatmap', 'heat-map']):
            if any(word in msg_lower for word in ['make', 'create', 'show', 'see', 'generate', 'view', 'display', 'give', 'send']):
                # Import heatmap generation functions
                import os
                import sys
                sys.path.insert(0, '/home/ubuntu/claude/tournament_tracker')
                from tournament_heatmap import generate_static_heatmap, generate_attendance_heatmap
                
                # Generate heatmaps if requested or if they don't exist
                should_generate = any(word in msg_lower for word in ['make', 'create', 'generate', 'update', 'refresh'])
                
                heat_map_files = [
                    ('tournament_heatmap.png', '🗺️ **Tournament Density Heat Map**\nShowing geographic distribution of tournaments'),
                    ('tournament_heatmap_with_map.png', '🌍 **Heat Map with Street Overlay**\nTournament locations on street map'),
                    ('attendance_heatmap.png', '📊 **Attendance-Weighted Heat Map**\nLarger circles = higher attendance')
                ]
                
                # Check if files exist or need regeneration
                base_path = '/home/ubuntu/claude/tournament_tracker'
                files_exist = all(os.path.exists(f"{base_path}/{f[0]}") for f in heat_map_files)
                
                if should_generate or not files_exist:
                    await message.channel.send("🔄 Generating heat maps...")
                    
                    # Generate the heatmaps
                    try:
                        generate_static_heatmap(f'{base_path}/tournament_heatmap.png', use_map_background=False)
                        generate_static_heatmap(f'{base_path}/tournament_heatmap_with_map.png', use_map_background=True)
                        generate_attendance_heatmap(f'{base_path}/attendance_heatmap.png')
                        logger.info("Generated fresh heat maps for DM")
                    except Exception as e:
                        logger.error(f"Failed to generate heat maps: {e}")
                        await message.channel.send("❌ Error generating heat maps. Check logs.")
                        return
                
                # Send the heat map images
                files_sent = 0
                for filename, description in heat_map_files:
                    file_path = f"{base_path}/{filename}"
                    if os.path.exists(file_path):
                        try:
                            # Send description first, then the image
                            await message.channel.send(description)
                            file = discord.File(file_path)
                            await message.channel.send(file=file)
                            files_sent += 1
                            logger.info(f"Sent heat map image to DM: {file_path}")
                        except Exception as e:
                            logger.error(f"Failed to send {file_path} to DM: {e}")
                
                if files_sent > 0:
                    await message.channel.send(f"✅ Displayed {files_sent} heat map visualizations\n💡 Try: 'show attendance heatmap' or 'create new heatmaps'")
                    return
                else:
                    await message.channel.send("❌ No heat map files found. Try: 'create heat maps'")
                    return
        
        # Get AI response for DM (if not a heatmap request)
        async with message.channel.typing():
            response = await get_ai_response(
                message.content,
                channel_name="direct_message",
                author=str(message.author)
            )
            logger.info(f"AI response for DM generated, length: {len(response)}")
        
        # Send response
        if len(response) > 2000:
            chunks = [response[i:i+1900] for i in range(0, len(response), 1900)]
            for chunk in chunks:
                await message.channel.send(chunk)
        else:
            await message.channel.send(response)
        return
    
    # Server message handling
    # Log the message with channel info
    logger.info(f'[{message.guild.name}#{message.channel.name}] {message.author}: {message.content}')
    
    # Check channel type
    channel_name = message.channel.name.lower()
    is_dev_channel = channel_name in ['developer', 'developers', 'dev', 'bot-dev', 'claude-dev-backchannel']
    is_stats_channel = channel_name in ['stats', 'statistics', 'fgc-stats', 'tournament-stats']
    
    # Only respond in stats or developer channels
    if not (is_stats_channel or is_dev_channel):
        logger.info(f"Ignoring message in #{message.channel.name} (not a stats or dev channel)")
        return
    
    # In developer channel, let Claude AI handle everything naturally
    # Skip command detection - just let AI be helpful
    
    # Quick responses for status checks
    msg_lower = message.content.lower()
    if any(phrase in msg_lower for phrase in ['are you there', 'you there', 'still there', 'hello?', 'status']):
        if len(msg_lower) < 20:  # Short status check messages
            await message.channel.send("Yes")
            logger.info("Responded to status check")
            return
    
    # Check for heat map requests in ANY channel
    if any(word in msg_lower for word in ['heat map', 'heatmap', 'heat-map']):
        if any(word in msg_lower for word in ['make', 'create', 'show', 'see', 'generate', 'view', 'display', 'give', 'send']):
            # Import heatmap generation functions
            import os
            import sys
            sys.path.insert(0, '/home/ubuntu/claude/tournament_tracker')
            from tournament_heatmap import generate_static_heatmap, generate_attendance_heatmap
            
            # Generate heatmaps if requested or if they don't exist
            should_generate = any(word in msg_lower for word in ['make', 'create', 'generate', 'update', 'refresh'])
            
            heat_map_files = [
                ('tournament_heatmap.png', '🗺️ **Tournament Density Heat Map**\nShowing geographic distribution of tournaments'),
                ('tournament_heatmap_with_map.png', '🌍 **Heat Map with Street Overlay**\nTournament locations on street map'),
                ('attendance_heatmap.png', '📊 **Attendance-Weighted Heat Map**\nLarger circles = higher attendance')
            ]
            
            # Check if files exist or need regeneration
            base_path = '/home/ubuntu/claude/tournament_tracker'
            files_exist = all(os.path.exists(f"{base_path}/{f[0]}") for f in heat_map_files)
            
            if should_generate or not files_exist:
                await message.channel.send("🔄 Generating heat maps...")
                
                # Generate the heatmaps
                try:
                    generate_static_heatmap(f'{base_path}/tournament_heatmap.png', use_map_background=False)
                    generate_static_heatmap(f'{base_path}/tournament_heatmap_with_map.png', use_map_background=True)
                    generate_attendance_heatmap(f'{base_path}/attendance_heatmap.png')
                    logger.info("Generated fresh heat maps")
                except Exception as e:
                    logger.error(f"Failed to generate heat maps: {e}")
                    await message.channel.send("❌ Error generating heat maps. Check logs.")
                    return
            
            # Send the heat map images
            files_sent = 0
            for filename, description in heat_map_files:
                file_path = f"{base_path}/{filename}"
                if os.path.exists(file_path):
                    try:
                        # Send description first, then the image
                        await message.channel.send(description)
                        file = discord.File(file_path)
                        await message.channel.send(file=file)
                        files_sent += 1
                        logger.info(f"Sent heat map image: {file_path}")
                    except Exception as e:
                        logger.error(f"Failed to send {file_path}: {e}")
            
            if files_sent > 0:
                await message.channel.send(f"✅ Displayed {files_sent} heat map visualizations\n💡 Try: 'show attendance heatmap' or 'create new heatmaps'")
                return
            else:
                await message.channel.send("❌ No heat map files found. Try: 'create heat maps'")
                return
    
    # In developer channel, check for execution requests
    if is_dev_channel:
        executed = await handle_developer_execution(message)
        if executed:
            return
    
    # Get AI response with typing indicator
    
    async with message.channel.typing():
        response = await get_ai_response(
            message.content,
            channel_name=message.channel.name,
            author=str(message.author)
        )
        logger.info(f"AI response generated, length: {len(response)}")
    
    # Send response (handle Discord's 2000 char limit)
    if len(response) > 2000:
        # Split into chunks
        chunks = [response[i:i+1900] for i in range(0, len(response), 1900)]
        for chunk in chunks:
            await message.channel.send(chunk)
        logger.info(f"Sent chunked response ({len(chunks)} chunks)")
    else:
        await message.channel.send(response)
        logger.info(f"Sent response: {response[:100]}...")

# Keep essential commands
@bot.command()
async def sync(ctx):
    """Sync from start.gg (Admin only)"""
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("Admin permission required for sync")
        return
    
    progress = ProgressiveTask(ctx.channel, "Tournament Sync")
    await progress.start("Connecting to start.gg API...")
    
    try:
        from startgg_sync import sync_from_startgg
        
        # Run sync with progress updates
        async def sync_with_updates():
            await progress.update("Fetching tournament list...")
            await asyncio.sleep(0.5)
            
            # Run sync in background executor
            loop = asyncio.get_event_loop()
            stats = await loop.run_in_executor(
                None,
                sync_from_startgg,
                250,  # page_size
                False,  # fetch_standings
                5  # standings_limit
            )
            return stats
        
        # Simulate progress during sync
        sync_task = asyncio.create_task(sync_with_updates())
        
        # Update status while syncing
        for i in range(10):
            if sync_task.done():
                break
            await progress.update(f"Processing tournaments... ({i*10}%)", append=False)
            await asyncio.sleep(2)
        
        stats = await sync_task
        
        if stats:
            await progress.update(f"Processed {stats['summary']['tournaments_processed']} tournaments")
            await progress.update(f"Created {stats['summary']['organizations_created']} organizations")
            await progress.complete(f"Success rate: {stats['summary']['success_rate']:.1f}%")
        else:
            await progress.error("Sync failed - check logs")
            
    except Exception as e:
        await progress.error(str(e))

@bot.command()
async def restart(ctx):
    """Restart the bot (Admin only)"""
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("Admin permission required")
        return
    
    await ctx.send("Restarting...")
    os.execv(sys.executable, ['python3'] + sys.argv)

@bot.command()
async def ai_status(ctx):
    """Check AI status"""
    if bot.ai.enabled:
        await ctx.send(f"✅ Claude AI is active (Model: {bot.ai.model})")
    else:
        await ctx.send("❌ Claude AI is not configured. Add ANTHROPIC_API_KEY to enable.")

if __name__ == '__main__':
    # Check for API key
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("⚠️  WARNING: No ANTHROPIC_API_KEY found. Bot will run with limited responses.")
        print("To enable Claude AI, set: export ANTHROPIC_API_KEY='your-key-here'")
    
    # Get Discord token
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print("Error: Set DISCORD_BOT_TOKEN environment variable")
        sys.exit(1)
    
    bot.run(token)