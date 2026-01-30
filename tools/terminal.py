import asyncio
import os
import platform
from agent_core import BaseTool

class TerminalTool(BaseTool):
    name: str = "terminal"
    description: str = """Execute shell/terminal commands on the host system. 
    Use this for file management, system checks, or running scripts. 
    Warning: Be careful with destructive commands."""
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The command to execute (e.g., 'ls' or 'dir')."
            }
        },
        "required": ["command"]
    }

    async def execute(self, command: str) -> str:
        try:
            # Use appropriate shell based on OS
            if platform.system() == "Windows":
                # Using powershell for better consistency
                shell_cmd = f"powershell -Command \"{command}\""
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
