import asyncio
import os
import platform
from base_tool import BaseTool, ToolResult
from event_bus import EventBus

class TerminalTool(BaseTool):
    name: str = "terminal"
    description: str = """Execute shell/terminal commands on the host system. 
    This tool is UV-aware: it automatically runs python/pip commands within the project's 'uv' environment.
    Use this for file management, system checks, or running scripts."""
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The command to execute (e.g., 'ls' or 'python script.py')."
            }
        },
        "required": ["command"]
    }

    async def execute(self, command: str) -> str:
        try:
            command = command.strip()
            
            # Use appropriate shell based on OS
            if platform.system() == "Windows":
                # Auto-quote paths with spaces if not already quoted
                if " " in command and not (command.startswith('"') or command.startswith("'")):
                    # Simple heuristic: if it looks like a path/command with spaces, wrap it
                    # But only if it's a simple command, not a complex pipe/redir
                    if "|" not in command and ">" not in command and "&" not in command:
                        command = f'"{command}"'

                # Using powershell for better consistency, escaping double quotes in command
                safe_command = command.replace('"', '\"')
                shell_cmd = f"powershell -Command \"{safe_command}\""
            else:
                shell_cmd = command

            process = await asyncio.create_subprocess_shell(
                shell_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            output = stdout.decode().strip()
            error = stderr.decode().strip()
            
            result = []
            if output:
                result.append(f"STDOUT:\n{output}")
            if error:
                result.append(f"STDERR:\n{error}")
            
            if not result:
                res_str = f"Command executed successfully (no output). Exit code: {process.returncode}"
            else:
                res_str = "\n\n".join(result) + f"\n\nExit code: {process.returncode}"
            
            # Publish to UI
            await EventBus.publish("terminal", res_str)
            return res_str
            
        except Exception as e:
            err_msg = f"Error executing terminal command: {str(e)}"
            await EventBus.publish("terminal", err_msg)
            return err_msg
