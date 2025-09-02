#!/usr/bin/env python3
"""
Async handler for progressive status updates in Discord
Provides real-time feedback during long-running operations
"""

import asyncio
import time
import discord
from typing import Optional, Callable
import logging

logger = logging.getLogger('async_handler')

class ProgressiveTask:
    """Manages a task with progressive status updates"""
    
    def __init__(self, channel: discord.TextChannel, task_name: str = "Task"):
        self.channel = channel
        self.task_name = task_name
        self.message: Optional[discord.Message] = None
        self.start_time = time.time()
        self.status_lines = []
        self.is_complete = False
        
    async def start(self, initial_status: str = None):
        """Send initial status message"""
        status = initial_status or f"Starting {self.task_name}..."
        self.status_lines = [f"**{self.task_name}**", status]
        self.message = await self.channel.send(self._format_status())
        
    async def update(self, status: str, append: bool = True):
        """Update status message"""
        if append:
            self.status_lines.append(f"• {status}")
        else:
            self.status_lines[-1] = f"• {status}"
        
        if self.message:
            try:
                await self.message.edit(content=self._format_status())
            except discord.errors.NotFound:
                # Message was deleted, send a new one
                self.message = await self.channel.send(self._format_status())
    
    async def complete(self, final_status: str = None):
        """Mark task as complete"""
        self.is_complete = True
        elapsed = time.time() - self.start_time
        
        if final_status:
            self.status_lines.append(final_status)
        self.status_lines.append(f"✓ Complete ({elapsed:.1f}s)")
        
        if self.message:
            await self.message.edit(content=self._format_status())
    
    async def error(self, error_msg: str):
        """Mark task as failed"""
        self.is_complete = True
        elapsed = time.time() - self.start_time
        
        self.status_lines.append(f"❌ Error: {error_msg}")
        self.status_lines.append(f"Failed after {elapsed:.1f}s")
        
        if self.message:
            await self.message.edit(content=self._format_status())
    
    def _format_status(self) -> str:
        """Format status lines for Discord"""
        if len(self.status_lines) > 10:
            # Keep first 2 and last 8 lines
            lines = self.status_lines[:2] + ["..."] + self.status_lines[-7:]
        else:
            lines = self.status_lines
        
        return "\n".join(lines)


class StreamingResponse:
    """Handle streaming responses from Claude"""
    
    def __init__(self, channel: discord.TextChannel):
        self.channel = channel
        self.message: Optional[discord.Message] = None
        self.buffer = ""
        self.last_update = 0
        self.update_interval = 0.5  # Update every 0.5 seconds
        
    async def add_chunk(self, chunk: str):
        """Add a chunk of text to the response"""
        self.buffer += chunk
        
        # Update if enough time has passed
        if time.time() - self.last_update > self.update_interval:
            await self._update_message()
            
    async def finish(self):
        """Send final complete message"""
        await self._update_message(final=True)
        
    async def _update_message(self, final: bool = False):
        """Update or create the message"""
        display_text = self.buffer
        
        if not final and len(display_text) > 1900:
            display_text = display_text[:1900] + "..."
            
        if self.message is None:
            self.message = await self.channel.send(display_text)
        else:
            try:
                await self.message.edit(content=display_text)
            except discord.errors.HTTPException:
                # Message too long, send a new one
                self.message = await self.channel.send(display_text)
                
        self.last_update = time.time()


async def run_with_progress(channel: discord.TextChannel, 
                           task_func: Callable,
                           task_name: str = "Task",
                           updates: list = None):
    """
    Run a task with progressive status updates
    
    Example:
        result = await run_with_progress(
            channel, 
            fetch_standings,
            "Fetching Standings",
            ["Connecting to API", "Downloading data", "Processing results"]
        )
    """
    progress = ProgressiveTask(channel, task_name)
    await progress.start()
    
    try:
        # If updates provided, show them with delays
        if updates:
            for update in updates:
                await progress.update(update)
                await asyncio.sleep(0.5)
        
        # Run the actual task
        result = await task_func()
        
        await progress.complete()
        return result
        
    except Exception as e:
        await progress.error(str(e))
        raise


async def parallel_tasks_with_status(channel: discord.TextChannel, tasks: dict):
    """
    Run multiple tasks in parallel with status updates
    
    Example:
        tasks = {
            "Fetch Players": fetch_players(),
            "Fetch Tournaments": fetch_tournaments(),
            "Calculate Rankings": calculate_rankings()
        }
        results = await parallel_tasks_with_status(channel, tasks)
    """
    progress = ProgressiveTask(channel, "Parallel Tasks")
    await progress.start(f"Running {len(tasks)} tasks...")
    
    # Create coroutines with status updates
    async def run_task(name: str, coro):
        await progress.update(f"{name}: Started")
        try:
            result = await coro
            await progress.update(f"{name}: ✓ Complete", append=False)
            return result
        except Exception as e:
            await progress.update(f"{name}: ❌ Failed - {e}", append=False)
            raise
    
    # Run all tasks in parallel
    task_coros = [run_task(name, coro) for name, coro in tasks.items()]
    results = await asyncio.gather(*task_coros, return_exceptions=True)
    
    # Summary
    successful = sum(1 for r in results if not isinstance(r, Exception))
    await progress.complete(f"Completed: {successful}/{len(tasks)} successful")
    
    return dict(zip(tasks.keys(), results))


# Example usage for Discord bot integration
async def handle_long_operation(message: discord.Message):
    """Example of handling a long operation with updates"""
    
    progress = ProgressiveTask(message.channel, "Data Sync")
    await progress.start()
    
    try:
        # Step 1: Connect
        await progress.update("Connecting to start.gg API...")
        await asyncio.sleep(1)  # Simulate work
        
        # Step 2: Fetch
        await progress.update("Fetching tournament data...")
        await asyncio.sleep(2)  # Simulate work
        
        # Step 3: Process
        await progress.update("Processing 500 tournaments...")
        for i in range(5):
            await progress.update(f"Processed {i*100}/500 tournaments", append=False)
            await asyncio.sleep(0.5)
        
        # Step 4: Save
        await progress.update("Saving to database...")
        await asyncio.sleep(1)
        
        await progress.complete("All data synchronized successfully!")
        
    except Exception as e:
        await progress.error(str(e))