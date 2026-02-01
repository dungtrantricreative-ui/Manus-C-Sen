import asyncio
import os
import platform
from typing import ClassVar, Dict
from base_tool import BaseTool, ToolResult
from event_bus import EventBus

class TerminalTool(BaseTool):
    name: str = "terminal"
    description: str = """Execute shell/terminal/CMD/PowerShell commands.
    CAPABILITIES: Run ANY command (python, pip, git, curl, powershell), install packages, and manage files.
    This is your fallback tool when others fail."""
    instructions: str = """
1. **NON-INTERACTIVE**: Always use silent/auto-accept flags (e.g., `winget install --accept-package-agreements`, `choco install -y`, `pip install --quiet`).
2. **MEDIA EXPERT**: Use `yt-dlp` for ALL video downloads. Use `ffmpeg` for ALL media conversions.
3. **POWERSHELL**: Always prefer PowerShell syntax on Windows.
4. **SILENT**: Do not ask for permissions for individual steps once the main task is approved.
"""
    
    parameters: dict = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The command to execute (PowerShell/CMD on Windows, bash on Linux/Mac)."
            },
            "working_dir": {
                "type": "string",
                "description": "Optional working directory for the command. Defaults to project root."
            },
            "timeout": {
                "type": "integer",
                "description": "Optional timeout in seconds. Default is 120."
            }
        },
        "required": ["command"]
    }
    
    # Common useful commands for reference
    COMMAND_EXAMPLES: ClassVar[Dict[str, str]] = {
        "download": "Invoke-WebRequest -Uri 'URL' -OutFile 'outputs/file.ext'",
        "install_pip": "pip install package_name",
        "install_npm": "npm install package_name",
        "git_clone": "git clone URL outputs/repo_name",
        "create_dir": "mkdir outputs/new_folder",
        "list_files": "Get-ChildItem -Recurse",
        "run_python": "python script.py",
    }

    async def execute(self, command: str, working_dir: str = None, timeout: int = 120) -> str:
        try:
            command = command.strip()
            
            # Auto-ensure outputs directory exists for common operations
            if "outputs/" in command or "outputs\\" in command:
                os.makedirs("outputs", exist_ok=True)
            
            # Determine working directory
            cwd = working_dir or os.getcwd()
            
            # Use appropriate shell based on OS
            if platform.system() == "Windows":
                # PowerShell for better Windows compatibility
                # Escape for PowerShell
                safe_command = command.replace('"', '`"')
                shell_cmd = f'powershell -NoProfile -ExecutionPolicy Bypass -Command "{safe_command}"'
            else:
                shell_cmd = command

            process = await asyncio.create_subprocess_shell(
                shell_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return f"Command timed out after {timeout} seconds. Consider breaking into smaller steps."
            
            output = stdout.decode(errors='replace').strip()
            error = stderr.decode(errors='replace').strip()
            
            result = []
            if output:
                # Truncate very long outputs
                if len(output) > 5000:
                    output = output[:5000] + "\n... [OUTPUT TRUNCATED]"
                result.append(f"STDOUT:\n{output}")
            if error:
                if len(error) > 2000:
                    error = error[:2000] + "\n... [ERROR TRUNCATED]"
                result.append(f"STDERR:\n{error}")
            
            exit_code = process.returncode
            
            if not result:
                res_str = f"✅ Command executed successfully (no output). Exit code: {exit_code}"
            else:
                status = "✅" if exit_code == 0 else "⚠️"
                res_str = f"{status} Exit code: {exit_code}\n\n" + "\n\n".join(result)
            
            # Publish to UI
            await EventBus.publish("terminal", res_str)
            return res_str
            
        except Exception as e:
            err_msg = f"❌ Error executing command: {str(e)}\nTry a different approach or simpler command."
            await EventBus.publish("terminal", err_msg)
            return err_msg
