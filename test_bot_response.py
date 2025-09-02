#!/usr/bin/env python3
"""
Test bot responses without actually sending Discord messages
"""

import asyncio
import sys
sys.path.insert(0, '/home/ubuntu/claude/tournament_tracker')

from claude_ai import get_ai_response

async def test_response(message: str, channel: str = 'general'):
    """Test what response the bot would give"""
    response = await get_ai_response(message, channel, 'test_user')
    print(f"Channel: #{channel}")
    print(f"Message: {message}")
    print(f"Response: {response}")
    print("-" * 60)
    return response

async def main():
    # Test developer channel
    print("=== DEVELOPER CHANNEL TESTS ===")
    await test_response("show me README.md", "developer")
    await test_response("can you see the README?", "developer")
    await test_response("help me with code", "developer")
    await test_response("hey", "developer")
    
    print("\n=== GENERAL CHANNEL TESTS ===")
    await test_response("hey", "general")
    await test_response("show me top organizations", "general")

if __name__ == "__main__":
    asyncio.run(main())