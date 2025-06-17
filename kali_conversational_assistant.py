"""
Kali Linux Conversational Assistant (Improved)
Filename: kali_assistant.py
Version: 5.1
License: MIT
"""

import subprocess
import os
import re
import requests
import json
import logging
import platform
import time
import getpass
from pathlib import Path
from typing import Dict, List, Tuple, Optional

class KaliAssistant:
    def __init__(self):
        self.context = []
        self.safety_checks = True
        self.config = self._load_config()
        self.is_wsl = self._detect_wsl()
        self.is_root = os.geteuid() == 0
        self.user_name = self._get_username()
        self.session_start = time.strftime("%Y-%m-%d %H:%M:%S")
        
        # Initialize logging
        self._init_logging()
        
        # Set initial context
        self.context.append({
            "role": "system",
            "content": (
                f"You are an advanced AI assistant running in Kali Linux. Today is {self.session_start}. "
                f"User: {self.user_name}. System: {platform.platform()}. "
                "You can help with security testing, Linux administration, coding, and general questions. "
                "When appropriate, generate and execute commands. Always maintain a helpful, professional tone. "
                "For security tools, provide context and explanations."
            )
        })
        
        logging.info(f"Session started for user: {self.user_name}")

    def _init_logging(self):
        """Initialize logging system"""
        log_path = Path.home() / 'kali_assistant.log'
        logging.basicConfig(
            filename=str(log_path),
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filemode='a'
        )
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        formatter = logging.Formatter('%(message)s')
        console.setFormatter(formatter)
        logging.getLogger('').addHandler(console)
        
    def _get_username(self) -> str:
        """Get username safely"""
        try:
            return getpass.getuser()
        except:
            return os.getenv('USER', 'kali-user')
        
    def _load_config(self) -> Dict:
        """Load configuration from file"""
        config_path = Path.home() / '.kali_assistant.json'
        default_config = {
            "api": {
                "ollama_endpoint": "http://localhost:11434/api/chat",
                "timeout": 30
            },
            "personality": {
                "name": "Kali-Assist",
                "tone": "professional",
                "verbosity": "detailed",
            },
            "security": {
                "require_confirmation": True,
                "max_output": 5000,
                "timeout": 45
            },
            "context": {
                "memory_size": 10,
            }
        }
        
        try:
            if config_path.exists():
                with open(config_path) as f:
                    return {**default_config, **json.load(f)}
            return default_config
        except Exception as e:
            logging.error(f"Config error: {str(e)}")
            return default_config

    def _detect_wsl(self) -> bool:
        """Check if running in WSL environment"""
        try:
            return 'microsoft' in platform.uname().release.lower()
        except:
            return False

    def _add_to_history(self, role: str, content: str):
        """Add to conversation history"""
        self.context.append({"role": role, "content": content})
        
        # Trim context to maintain size
        if len(self.context) > self.config["context"]["memory_size"] + 1:
            self.context = [self.context[0]] + self.context[-self.config["context"]["memory_size"]:]
    
    def _generate_response(self, prompt: str) -> str:
        """Generate response using Ollama API"""
        payload = {
            "model": "deepseek-coder",
            "messages": self.context,
            "options": {
                "temperature": 0.7,
            }
        }
        
        try:
            response = requests.post(
                self.config["api"]["ollama_endpoint"],
                json=payload,
                timeout=self.config["api"]["timeout"]
            )
            response.raise_for_status()
            return response.json()["message"]["content"].strip()
        except Exception as e:
            logging.error(f"API error: {str(e)}")
            return "I encountered an error processing your request. Please try again."

    def _execute_command(self, command: str) -> Tuple[str, int]:
        """Execute command with safety checks"""
        if not command:
            return "No command to execute", 1
            
        # Safety validation
        if self.safety_checks and not self._is_safe(command):
            return "Command blocked by safety system", 1
            
        try:
            # Execute with resource limits
            process = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.config["security"]["timeout"]
            )
            
            # Limit output size
            output = process.stdout + process.stderr
            if len(output) > self.config["security"]["max_output"]:
                output = output[:self.config["security"]["max_output"]] + "\n\n[OUTPUT TRUNCATED]"
                
            return output, process.returncode
        except subprocess.TimeoutExpired:
            return "Command timed out", 1
        except Exception as e:
            return f"Execution error: {str(e)}", 1

    def _is_safe(self, command: str) -> bool:
        """Check if command is safe to execute"""
        # Basic danger patterns
        danger_patterns = [
            r'rm\s+-rf\s+', r'dd\s+if=', r'>\s*/dev/sd', r'chmod\s+777\s+', 
            r':\(\)\{.*;\};', r'mv\s+/\s*', r'fdisk\s+/dev/', r'format\s+'
        ]
        
        for pattern in danger_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return False
                
        # If confirmation required
        if self.config["security"]["require_confirmation"]:
            print(f"\n[Safety] Command to execute: {command}")
            response = input("[Safety] Execute command? (y/N): ").strip().lower()
            return response == "y"
            
        return True

    def _extract_command(self, response: str) -> Optional[str]:
        """Extract command from assistant response"""
        # Look for code blocks or command markers
        if "```bash" in response:
            match = re.search(r'```bash\n(.*?)\n```', response, re.DOTALL)
            if match:
                return match.group(1).strip()
                
        # Look for command lines
        if response.startswith("$ "):
            return response[2:].strip()
            
        return None

    def handle_query(self, user_input: str) -> str:
        """Process user input and generate response"""
        self._add_to_history("user", user_input)
        
        # Handle special requests naturally
        if "toggle safety" in user_input.lower():
            self.safety_checks = not self.safety_checks
            status = "ENABLED" if self.safety_checks else "DISABLED"
            return f"Safety checks have been {status}."
            
        if "system information" in user_input.lower():
            info = self.get_system_info()
            info_str = "\n".join(f"{k}: {v}" for k, v in info.items())
            return f"System Information:\n{info_str}"
            
        if "conversation history" in user_input.lower():
            history = "\n".join(
                f"{i+1}. {msg['role']}: {msg['content'][:60]}{'...' if len(msg['content']) > 60 else ''}" 
                for i, msg in enumerate(self.context[1:])
            )
            return f"Recent Conversation History:\n{history}"
            
        if "exit" in user_input.lower() or "quit" in user_input.lower():
            return "EXIT_REQUEST"
        
        # Generate initial response
        response = self._generate_response(user_input)
        self._add_to_history("assistant", response)
        
        # Check if response contains a command
        command = self._extract_command(response)
        if command:
            output, returncode = self._execute_command(command)
            command_result = f"Command executed (exit={returncode}): {command}\nOutput:\n{output}"
            logging.info(command_result)
            
            # Generate follow-up explaining results
            follow_up = f"Command executed:\n```bash\n{command}\n```\nExit code: {returncode}\nOutput:\n{output[:500]}{'...' if len(output) > 500 else ''}"
            self._add_to_history("system", follow_up)
            
            # Summarize results
            if returncode == 0:
                response += f"\n\nCommand executed successfully:\n```bash\n{command}\n```"
            else:
                response += f"\n\nCommand failed (exit {returncode}):\n```bash\n{command}\n```"
        
        return response

    def get_system_info(self) -> Dict:
        """Get system information"""
        return {
            "system": platform.platform(),
            "user": self.user_name,
            "wsl": self.is_wsl,
            "root": self.is_root,
            "session_start": self.session_start,
            "context_size": len(self.context) - 1
        }

# User-friendly interface
def main():
    print("\n" + "="*50)
    print("KALI LINUX CONVERSATIONAL ASSISTANT")
    print("="*50)
    print("Type naturally - I can help with security, Linux, coding, or general questions")
    print("Special requests: 'show system info', 'toggle safety', 'history', 'exit'")
    print("="*50 + "\n")
    
    assistant = KaliAssistant()
    info = assistant.get_system_info()
    
    print(f"Hello {info['user']}! How can I help you today?")
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if not user_input:
                continue
                
            start_time = time.time()
            response = assistant.handle_query(user_input)
            response_time = time.time() - start_time
            
            # Handle exit request
            if response == "EXIT_REQUEST":
                print("\nGoodbye! Have a great day.")
                break
                
            # Print response
            print(f"\nAssistant ({response_time:.2f}s):")
            print(response)
            
        except KeyboardInterrupt:
            print("\nType 'exit' to quit")
        except Exception as e:
            print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()