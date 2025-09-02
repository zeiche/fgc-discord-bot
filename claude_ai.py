#!/usr/bin/env python3
"""
Claude AI integration for Discord bot
Provides real AI-powered responses instead of pattern matching
"""

import os
import httpx
import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger('claude_ai')

class ClaudeAI:
    """Claude API integration for intelligent responses"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            logger.warning("No Anthropic API key found - Claude AI disabled")
            self.enabled = False
        else:
            self.enabled = True
            logger.info("Claude AI initialized")
        
        self.api_url = "https://api.anthropic.com/v1/messages"
        self.model = "claude-3-haiku-20240307"  # Fast, affordable model for Discord
        
        # System prompt for the bot's personality and knowledge
        self.system_prompt = """You are a Discord bot for tournament data.

CHANNEL RULES:

#developer or #dev:
- Be extremely terse. One line answers preferred.
- No introductions, no explanations unless asked
- Just answer or execute. Act like a CLI tool.
- If showing code, just show it. No preamble.

#stats:
- Brief data responses. Numbers first.
- Format: "Top 3: SoCal FGC (1234), Level Up (987), WNF (654)"
- No fluff. Just data.

#general:
- Normal friendly bot

DMs:
- Friendly but concise

Data available:
- 100+ tournaments, organization rankings, attendance stats
- Heat maps at tournament_heatmap.png and attendance_heatmap.png

Max 500 chars unless showing data tables."""
    
    async def get_response(self, message: str, channel_name: str = None, author: str = None) -> str:
        """
        Get an AI-powered response to a message
        
        Args:
            message: The user's message
            channel_name: The Discord channel name for context
            author: The message author for context
        
        Returns:
            AI-generated response string
        """
        if not self.enabled:
            # Fallback to simple response if no API key
            return self._get_fallback_response(message, channel_name)
        
        try:
            # Add context to the user message
            context_message = message
            if channel_name:
                context_message = f"[Channel: #{channel_name}] {message}"
            
            # Prepare the API request
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            
            data = {
                "model": self.model,
                "max_tokens": 200,  # Much shorter responses
                "temperature": 0.3,  # More deterministic/focused
                "system": self.system_prompt,
                "messages": [
                    {
                        "role": "user",
                        "content": context_message
                    }
                ]
            }
            
            # Make async request to Claude API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    headers=headers,
                    json=data,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    ai_response = result['content'][0]['text']
                    logger.info(f"Claude AI response generated for: {message[:50]}...")
                    return ai_response
                else:
                    logger.error(f"Claude API error: {response.status_code} - {response.text}")
                    return self._get_fallback_response(message, channel_name)
                    
        except Exception as e:
            logger.error(f"Error getting Claude response: {e}")
            return self._get_fallback_response(message, channel_name)
    
    def _get_fallback_response(self, message: str, channel_name: str = None) -> str:
        """Simple fallback response when AI is not available"""
        msg_lower = message.lower()
        is_developer = channel_name and 'developer' in channel_name.lower()
        
        # Developer channel gets technical responses
        if is_developer:
            if any(word in msg_lower for word in ['hi', 'hello', 'hey']):
                return "Hey! Ready to help with code. What are you working on?"
            elif 'help' in msg_lower:
                return "I can help with the tournament_tracker codebase! Ask me about the code architecture, database schema, or any programming questions!"
            elif any(word in msg_lower for word in ['programming', 'code', 'serious', 'conversation']):
                return "Absolutely! I can discuss the codebase, architecture, help debug issues, or talk about programming concepts. What technical topic would you like to explore?"
            elif any(word in msg_lower for word in ['readme', 'file', 'show', 'see', 'look', 'read']):
                return "I don't have the current contents of that file in my context, but I can help with questions about the codebase structure and architecture."
            elif any(word in msg_lower for word in ['thank', 'thanks']):
                return "You're welcome! Let me know if you need more code help!"
            else:
                return "I can help with code, debugging, or any technical questions about the tournament_tracker. What do you need?"
        
        # Check if it's a stats channel
        if channel_name and 'stats' in channel_name.lower():
            if any(word in msg_lower for word in ['hi', 'hello', 'hey']):
                return "Hey! Welcome to stats! I've got all the FGC tournament data - attendance numbers, organization rankings, venue statistics. What would you like to know?"
            elif 'help' in msg_lower:
                return "I track SoCal FGC tournament statistics! I can show you attendance data, organization rankings, venue heat maps, and tournament trends."
            elif any(word in msg_lower for word in ['top', 'best', 'biggest']):
                return "The top organizations have impressive numbers! SoCal FGC leads with huge attendance. Want specific stats?"
            else:
                return "I have tournament statistics, attendance data, and organization rankings. What data are you interested in?"
        
        # General channel responses - be friendly and general
        if any(word in msg_lower for word in ['hi', 'hello', 'hey']):
            return "Hey there! How's it going? 👋"
        elif 'help' in msg_lower:
            return "I'm here to help! I can chat about various topics. For tournament stats, check out #stats!"
        elif any(word in msg_lower for word in ['thank', 'thanks']):
            return "You're welcome! Happy to help!"
        else:
            return "I'm here to chat! What's on your mind?"
    
    def update_context(self, context: Dict[str, Any]):
        """Update the system prompt with additional context"""
        if 'stats' in context:
            stats = context['stats']
            self.system_prompt += f"""
            
Current database statistics:
- Total organizations: {stats.get('total_organizations', 'unknown')}
- Total tournaments: {stats.get('total_tournaments', 'unknown')}
- Total attendance: {stats.get('total_attendance', 'unknown')}"""
            logger.info("Updated Claude context with current stats")

# Singleton instance
_claude_ai = None

def get_claude_ai(api_key: Optional[str] = None) -> ClaudeAI:
    """Get or create the Claude AI instance"""
    global _claude_ai
    if _claude_ai is None:
        _claude_ai = ClaudeAI(api_key)
    return _claude_ai

async def get_ai_response(message: str, channel_name: str = None, author: str = None) -> str:
    """Convenience function to get AI response"""
    ai = get_claude_ai()
    return await ai.get_response(message, channel_name, author)