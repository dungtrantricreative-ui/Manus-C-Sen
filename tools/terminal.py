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
            
            # Auto-ensure outputs directory
            if "outputs/" in command or "outputs\\" in command:
                os.makedirs("outputs", exist_ok=True)
            
            cwd = working_dir or os.getcwd()
            
            if platform.system() == "Windows":
                # Robust PowerShell execution: Base64 encoding prevents quote/escaping issues
                import base64
                # We wrap the command in a script block to handle multiline and complex logic
                encoded_cmd = base64.b64encode(command.encode('utf-16-le')).decode('ascii')
                shell_cmd = f'powershell -NoProfile -ExecutionPolicy Bypass -EncodedCommand {encoded_cmd}'
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
                return f"Timeout after {timeout}s."
            
            output = stdout.decode(errors='replace').strip()
            error = stderr.decode(errors='replace').strip()
            
            result = []
            if output:
                if len(output) > 3000:
                    output = output[:3000] + "\n... [TRUNCATED]"
                result.append(output)
            if error:
                if len(error) > 1000:
                    error = error[:1000] + "\n... [TRUNCATED]"
                result.append(f"STDERR: {error}")
            
            exit_code = process.returncode
            if not result:
                return f"Done (Code {exit_code})"
            
            status = "Success" if exit_code == 0 else "Error"
            return f"{status} (Code {exit_code}): " + " | ".join(result)
            
        except Exception as e:
            return f"Terminal failure: {str(e)}"
