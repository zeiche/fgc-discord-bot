#!/usr/bin/env python3
"""
Developer commands for Discord bot - accessible only in #developer channel
"""
import discord
from discord.ext import commands
import sys
import os
import logging

# Add tournament_tracker to path
sys.path.insert(0, '/home/ubuntu/claude/tournament_tracker')

from database_utils import get_session
from sqlalchemy import text

logger = logging.getLogger('discord_bot')

def is_developer_channel():
    """Check if command is in #developer or #dev channel"""
    async def predicate(ctx):
        channel_name = ctx.channel.name.lower()
        if channel_name in ['developer', 'developers', 'dev', 'bot-dev']:
            return True
        await ctx.send("❌ This command can only be used in #developer channel")
        return False
    return commands.check(predicate)

class DeveloperCommands(commands.Cog):
    """Developer commands for #developer channel"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name='query')
    @is_developer_channel()
    async def database_query(self, ctx, *, query: str):
        """Execute ANY database query - FULL ACCESS in #developer"""
        
        try:
            with get_session() as session:
                result = session.execute(text(query))
                rows = result.fetchall()
                
                if not rows:
                    await ctx.send("No results")
                    return
                
                # Format results
                output = f"```\n{len(rows)} rows:\n"
                
                # Column names
                if hasattr(result, 'keys'):
                    cols = result.keys()
                    output += " | ".join(cols[:5]) + "\n"
                    output += "-" * 50 + "\n"
                
                # First 10 rows
                for row in rows[:10]:
                    output += " | ".join(str(val)[:20] for val in row[:5]) + "\n"
                
                if len(rows) > 10:
                    output += f"\n... +{len(rows) - 10} more"
                
                output += "```"
                
                if len(output) > 2000:
                    output = output[:1997] + "..."
                
                await ctx.send(output)
                logger.info(f"Query by {ctx.author}: {query}")
                
        except Exception as e:
            await ctx.send(f"❌ Error: {e}")
    
    @commands.command(name='logs')
    @is_developer_channel()
    async def show_logs(self, ctx, lines: int = 20):
        """Show recent bot logs"""
        try:
            with open('/home/ubuntu/claude/discord_bot.log', 'r') as f:
                all_lines = f.readlines()
                recent = all_lines[-lines:]
            
            output = "```\n" + "".join(recent) + "```"
            
            if len(output) > 2000:
                output = "```\n" + "".join(recent[-(lines//2):]) + "```"
            
            await ctx.send(output)
            
        except Exception as e:
            await ctx.send(f"❌ Error: {e}")
    
    @commands.command(name='errors')
    @is_developer_channel()
    async def show_errors(self, ctx, lines: int = 10):
        """Show recent errors from log"""
        try:
            with open('/home/ubuntu/claude/discord_bot.log', 'r') as f:
                error_lines = [line for line in f if 'ERROR' in line][-lines:]
            
            if not error_lines:
                await ctx.send("No recent errors found ✅")
                return
            
            output = "```\n" + "".join(error_lines) + "```"
            
            if len(output) > 2000:
                output = output[:1997] + "..."
            
            await ctx.send(output)
            
        except Exception as e:
            await ctx.send(f"❌ Error: {e}")
    
    @commands.command(name='dbstats')
    @is_developer_channel()
    async def database_stats(self, ctx):
        """Show database statistics"""
        try:
            with get_session() as session:
                # Get table counts
                tables = {
                    'Organizations': "SELECT COUNT(*) FROM organizations",
                    'Tournaments': "SELECT COUNT(*) FROM tournaments",
                    'Attendance': "SELECT COUNT(*) FROM attendance_records",
                    'Contacts': "SELECT COUNT(*) FROM organization_contacts"
                }
                
                embed = discord.Embed(
                    title="Database Statistics",
                    color=discord.Color.green()
                )
                
                for name, query in tables.items():
                    result = session.execute(text(query))
                    count = result.scalar()
                    embed.add_field(name=name, value=f"{count:,}", inline=True)
                
                # Get database file size
                import os
                db_path = '/home/ubuntu/claude/tournament_tracker/tournament_tracker.db'
                if os.path.exists(db_path):
                    size_mb = os.path.getsize(db_path) / (1024 * 1024)
                    embed.add_field(name="DB Size", value=f"{size_mb:.2f} MB", inline=True)
                
                await ctx.send(embed=embed)
                
        except Exception as e:
            await ctx.send(f"❌ Error: {e}")
    
    @commands.command(name='reload')
    @is_developer_channel()
    async def reload_cogs(self, ctx):
        """Reload bot extensions"""
        try:
            # Reload this cog
            await self.bot.reload_extension('discord_dev_commands')
            
            # Try to reload tournament commands
            try:
                from discord_commands import setup
                await setup(self.bot)
                await ctx.send("✅ Reloaded all extensions")
            except:
                await ctx.send("✅ Reloaded developer commands")
                
        except Exception as e:
            await ctx.send(f"❌ Reload failed: {e}")
    
    @commands.command(name='exec')
    @is_developer_channel()
    async def execute_python(self, ctx, *, code: str):
        """Execute Python code - FULL ACCESS in #developer"""
        # Remove code blocks if present
        if code.startswith('```python'):
            code = code[9:]
        elif code.startswith('```'):
            code = code[3:]
        if code.endswith('```'):
            code = code[:-3]
        
        try:
            # Full unrestricted namespace for #developer
            import os
            import sys
            import subprocess
            
            namespace = {
                'bot': self.bot,
                'ctx': ctx,
                'get_session': get_session,
                'os': os,
                'sys': sys,
                'subprocess': subprocess,
                'open': open,
                '__builtins__': __builtins__
            }
            
            # Execute with full access
            exec(code, namespace)
            
            # Check if there's a result to display
            if 'result' in namespace:
                await ctx.send(f"Result: {namespace['result']}")
            else:
                await ctx.send("✅ Executed")
                
        except Exception as e:
            await ctx.send(f"❌ Error: {e}")
    
    @commands.command(name='write')
    @is_developer_channel()
    async def write_file(self, ctx, path: str, *, content: str):
        """Write to any file - FULL ACCESS in #developer"""
        try:
            with open(path, 'w') as f:
                f.write(content)
            await ctx.send(f"✅ Wrote to {path}")
            logger.info(f"File written by {ctx.author}: {path}")
        except Exception as e:
            await ctx.send(f"❌ Error: {e}")
    
    @commands.command(name='read')
    @is_developer_channel()
    async def read_file(self, ctx, path: str):
        """Read any file - FULL ACCESS in #developer"""
        try:
            with open(path, 'r') as f:
                content = f.read()
            
            if len(content) > 1900:
                content = content[:1900] + "..."
            
            await ctx.send(f"```\n{content}\n```")
        except Exception as e:
            await ctx.send(f"❌ Error: {e}")
    
    @commands.command(name='services')
    @is_developer_channel()
    async def check_services(self, ctx):
        """Check status of tournament services"""
        import subprocess
        
        services = ['tournament-web', 'discord-bot']
        
        embed = discord.Embed(
            title="Service Status",
            color=discord.Color.blue()
        )
        
        for service in services:
            try:
                result = subprocess.run(
                    ['systemctl', 'is-active', service],
                    capture_output=True,
                    text=True
                )
                status = result.stdout.strip()
                
                if status == 'active':
                    embed.add_field(name=service, value="✅ Active", inline=True)
                else:
                    embed.add_field(name=service, value=f"❌ {status}", inline=True)
                    
            except Exception as e:
                embed.add_field(name=service, value=f"❓ Unknown", inline=True)
        
        await ctx.send(embed=embed)

async def setup(bot):
    """Setup function for loading cog"""
    await bot.add_cog(DeveloperCommands(bot))

if __name__ == "__main__":
    # For testing
    print("Developer commands module - import this into your bot")