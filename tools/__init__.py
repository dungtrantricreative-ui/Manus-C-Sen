import os
import importlib
import inspect
from loguru import logger
from base_tool import BaseTool

def load_tools(enabled_tools: list = None):
    """
    Dynamically loads tool classes from the current directory.
    Only loads classes that inherit from BaseTool and are not BaseTool itself.
    """
    tools = []
    current_dir = os.path.dirname(__file__)
    
    for filename in os.listdir(current_dir):
        if filename.endswith(".py") and filename != "__init__.py":
            module_name = f"tools.{filename[:-3]}"
            try:
                module = importlib.import_module(module_name)
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, BaseTool) and 
                        obj is not BaseTool):
                        
                        instance = obj()
                        # If enabled_tools is provided, filter by tool name
                        if enabled_tools is not None:
                            if instance.name in enabled_tools:
                                tools.append(instance)
                                logger.debug(f"Loaded tool: {instance.name} from {module_name}")
                        else:
                            tools.append(instance)
                            logger.debug(f"Loaded tool: {instance.name} from {module_name}")
            except Exception as e:
                logger.error(f"Failed to load tool from {module_name}: {e}")
                
    return tools
