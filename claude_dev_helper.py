#!/usr/bin/env python3
"""
Enhanced developer helper for natural language command execution
Detects intent and automatically executes appropriate commands
"""

import re
import logging

logger = logging.getLogger('claude_dev_helper')

class DeveloperHelper:
    """Helper to translate natural language to bot commands in developer channel"""
    
    def extract_commands(self, message: str, channel_name: str = None) -> list:
        """
        Extract potential commands from natural language
        Returns list of suggested commands to execute
        """
        msg_lower = message.lower()
        commands = []
        
        # Only process in developer channels
        if not channel_name or 'dev' not in channel_name.lower():
            return commands
        
        # File operations
        if any(word in msg_lower for word in ['read', 'show', 'cat', 'display', 'look at', 'check']):
            # Try to extract file paths
            paths = re.findall(r'[/\w\-_.]+\.\w+', message)
            if not paths:
                paths = re.findall(r'/[\w/\-_.]+', message)
            for path in paths:
                commands.append(f"!read {path}")
        
        # Write operations
        if any(word in msg_lower for word in ['write', 'create', 'save', 'make']):
            # Look for file paths and content
            if 'file' in msg_lower or '.py' in message or '.txt' in message:
                # Extract potential file path
                path_match = re.search(r'(\S+\.\w+)', message)
                if path_match:
                    commands.append(f"!write {path_match.group(1)} [content]")
        
        # Database queries
        if any(word in msg_lower for word in ['query', 'select', 'update', 'delete', 'insert', 'database', 'sql']):
            # Extract SQL-like statements
            sql_match = re.search(r'(select|update|delete|insert|show|describe).+', msg_lower, re.IGNORECASE)
            if sql_match:
                commands.append(f"!query {sql_match.group(0)}")
            elif 'table' in msg_lower:
                commands.append("!query SELECT name FROM sqlite_master WHERE type='table'")
        
        # Code execution
        if any(word in msg_lower for word in ['run', 'execute', 'exec', 'python', 'code']):
            # Look for code blocks or python snippets
            code_block = re.search(r'```(?:python)?\n?(.*?)```', message, re.DOTALL)
            if code_block:
                commands.append(f"!exec {code_block.group(1)}")
            elif 'print' in msg_lower or 'import' in msg_lower:
                # Likely contains Python code
                commands.append("!exec [detected python code]")
        
        # Service management
        if any(word in msg_lower for word in ['restart', 'reload', 'refresh']):
            if 'bot' in msg_lower:
                commands.append("!reload")
            if 'service' in msg_lower:
                commands.append("!services")
        
        # Log viewing
        if any(word in msg_lower for word in ['log', 'error', 'debug', 'trace']):
            if 'error' in msg_lower:
                commands.append("!errors 10")
            else:
                commands.append("!logs 20")
        
        # Database stats
        if any(word in msg_lower for word in ['stats', 'statistics', 'count', 'database size']):
            if 'database' in msg_lower or 'db' in msg_lower:
                commands.append("!dbstats")
        
        # System commands via exec
        if any(word in msg_lower for word in ['ls', 'pwd', 'whoami', 'ps', 'kill', 'top']):
            # Wrap system commands in Python subprocess
            for cmd in ['ls', 'pwd', 'whoami', 'ps']:
                if cmd in msg_lower:
                    commands.append(f"!exec import subprocess; result = subprocess.run(['{cmd}'], capture_output=True, text=True).stdout")
        
        return commands
    
    def generate_helpful_response(self, message: str, commands: list) -> str:
        """
        Generate a helpful response suggesting commands
        """
        if not commands:
            return None
        
        if len(commands) == 1:
            return f"I can help with that! Try this command:\n`{commands[0]}`"
        else:
            cmd_list = '\n'.join(f"• `{cmd}`" for cmd in commands[:5])
            return f"I can help! Here are some commands that might work:\n{cmd_list}"
    
    def should_auto_execute(self, message: str) -> bool:
        """
        Determine if we should auto-execute detected commands
        """
        msg_lower = message.lower()
        
        # Strong action words that indicate desire for execution
        action_words = [
            'please', 'do', 'execute', 'run', 'perform',
            'show me', 'can you', 'could you', 'would you',
            'go ahead', 'yes', 'sure', 'definitely'
        ]
        
        return any(word in msg_lower for word in action_words)

# Singleton instance
_helper = DeveloperHelper()

def extract_developer_commands(message: str, channel_name: str = None) -> list:
    """Extract commands from natural language"""
    return _helper.extract_commands(message, channel_name)

def get_command_suggestion(message: str, commands: list) -> str:
    """Get helpful suggestion for commands"""
    return _helper.generate_helpful_response(message, commands)

def should_auto_execute(message: str) -> bool:
    """Check if auto-execution is desired"""
    return _helper.should_auto_execute(message)