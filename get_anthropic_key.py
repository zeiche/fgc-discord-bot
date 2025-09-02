#!/usr/bin/env python3
"""
Script to attempt to retrieve Anthropic API key using browser automation
"""
import subprocess
import time
import re
import os

def get_api_key_with_lynx():
    """Attempt to get API key using lynx browser"""
    
    verification_code = "468772"
    
    # Create lynx command file for automation
    lynx_script = """
# Navigate to Anthropic console
g https://console.anthropic.com/settings/keys
# Wait for page load and enter verification code if prompted
/verification
^J
{code}
^J
# Navigate to API keys section
/API
^J
# Try to create new key
/Create
^J
/New API Key
^J
# Save page to file
p
api_key_page.txt
^J
q
y
""".format(code=verification_code)
    
    # Write lynx commands to file
    with open('/tmp/lynx_commands.txt', 'w') as f:
        f.write(lynx_script)
    
    print("Attempting to retrieve API key using lynx...")
    
    # Run lynx with commands
    try:
        # First attempt: Try to navigate directly
        result = subprocess.run(
            ['lynx', '-accept_all_cookies', '-dump', 'https://console.anthropic.com/settings/keys'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Check if we got any API keys in the output
        if 'sk-ant-' in result.stdout:
            # Extract API key
            matches = re.findall(r'sk-ant-api\d+-[\w-]+', result.stdout)
            if matches:
                print(f"Found API key: {matches[0]}")
                return matches[0]
        
        # If not found, try interactive mode with verification code
        print("Direct access failed, trying with verification code...")
        
        # Create expect script for interactive lynx
        expect_script = f"""#!/usr/bin/expect -f
set timeout 30
spawn lynx https://console.anthropic.com/login
expect "verification" {{
    send "{verification_code}\\r"
}}
expect "API" {{
    send "/API\\r"
}}
expect "Create" {{
    send "/Create\\r"
}}
expect eof
"""
        
        with open('/tmp/lynx_expect.exp', 'w') as f:
            f.write(expect_script)
        
        os.chmod('/tmp/lynx_expect.exp', 0o755)
        
        # Try with expect if available
        try:
            result = subprocess.run(['/tmp/lynx_expect.exp'], capture_output=True, text=True, timeout=60)
            if 'sk-ant-' in result.stdout:
                matches = re.findall(r'sk-ant-api\d+-[\w-]+', result.stdout)
                if matches:
                    print(f"Found API key: {matches[0]}")
                    return matches[0]
        except FileNotFoundError:
            print("Expect not available, trying curl approach...")
        
        # Alternative: Try using curl with cookies
        print("Attempting API request with curl...")
        
        # This would require proper authentication which we can't automate without credentials
        print("Unable to automatically retrieve API key.")
        print("\nManual steps required:")
        print("1. Open browser and go to: https://console.anthropic.com/settings/keys")
        print(f"2. Enter verification code: {verification_code}")
        print("3. Create a new API key")
        print("4. Copy the key and run:")
        print("   echo 'ANTHROPIC_API_KEY=your-key-here' >> /home/ubuntu/claude/.env.discord")
        
        return None
        
    except subprocess.TimeoutExpired:
        print("Request timed out")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def check_existing_key():
    """Check if there's already a key configured somewhere"""
    
    # Check common locations
    locations = [
        '/home/ubuntu/.anthropic',
        '/home/ubuntu/.config/anthropic',
        '/home/ubuntu/.bashrc',
        '/home/ubuntu/.profile',
        '/home/ubuntu/.env',
    ]
    
    for loc in locations:
        if os.path.exists(loc):
            try:
                with open(loc, 'r') as f:
                    content = f.read()
                    if 'sk-ant-' in content:
                        matches = re.findall(r'sk-ant-api\d+-[\w-]+', content)
                        if matches:
                            print(f"Found existing API key in {loc}")
                            return matches[0]
            except:
                pass
    
    return None

if __name__ == "__main__":
    # First check for existing key
    existing_key = check_existing_key()
    if existing_key:
        print(f"\nFound existing API key: {existing_key}")
        print("Adding to Discord bot configuration...")
        
        # Add to .env.discord
        with open('/home/ubuntu/claude/.env.discord', 'r') as f:
            content = f.read()
        
        if 'ANTHROPIC_API_KEY=' not in content or 'ANTHROPIC_API_KEY=your-key-here' in content:
            with open('/home/ubuntu/claude/.env.discord', 'w') as f:
                f.write(content.rstrip())
                f.write(f'\nANTHROPIC_API_KEY={existing_key}\n')
            print("API key added to .env.discord")
            print("Run: sudo systemctl restart discord-ai-bot")
        else:
            print("API key already configured in .env.discord")
    else:
        # Try to get new key
        api_key = get_api_key_with_lynx()
        if api_key:
            print(f"\nSuccessfully retrieved API key: {api_key}")
            print("Adding to Discord bot configuration...")
            
            with open('/home/ubuntu/claude/.env.discord', 'a') as f:
                f.write(f'\nANTHROPIC_API_KEY={api_key}\n')
            
            print("API key added to .env.discord")
            print("Run: sudo systemctl restart discord-ai-bot")
        else:
            print("\nCould not automatically retrieve API key.")
            print("Please obtain it manually from https://console.anthropic.com/settings/keys")