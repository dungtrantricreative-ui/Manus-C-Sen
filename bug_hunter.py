import asyncio
import json
from typing import AsyncGenerator, Dict, Any, List
from agent_core import ManusCompetition, Message, AgentState
from base_tool import ToolResult

# Mock LLM that returns pre-defined responses to find bugs in the loop logic
class MockLLM:
    def __init__(self, responses: List[Dict]):
        self.responses = responses
        self.call_count = 0

    async def ask_tool(self, messages, tools, tool_choice="auto"):
        if self.call_count >= len(self.responses):
            # Default to termination if we run out of mock responses
            return type('obj', (object,), {
                "content": "All tasks done.",
                "tool_calls": [type('obj', (object,), {
                    "id": "exit",
                    "function": type('obj', (object,), {"name": "terminate", "arguments": '{"output": "Finished simulation"}'})
                })]
            })
        
        resp_data = self.responses[self.call_count]
        self.call_count += 1
        
        return type('obj', (object,), {
            "content": resp_data.get("content", ""),
            "tool_calls": [type('obj', (object,), {
                "id": f"call_{i}",
                "function": type('obj', (object,), {"name": tc["name"], "arguments": json.dumps(tc["args"])})
            }) for i, tc in enumerate(resp_data.get("tool_calls", []))]
        })

    async def quick_ask(self, messages, max_tokens=200, model=None):
        return "PROCEED"

# Mock Tool to verify path handling and error propagation
class MockTool:
    async def execute(self, name, args):
        if name == "terminal" and "dir" in args.get("command", ""):
            if "Incorrect Path" in args.get("command"):
                return "File not found."
            return "Volume in drive D is Data..."
        if name == "search" and args.get("query") == "massive":
            return "DATA-START " + ("A" * 10000) + " DATA-END"
        return f"Mock result for {name}"

async def run_simulation(name: str, scenario_responses: List[Dict]):
    print(f"\n--- 🕵️ Scenario: {name} ---")
    agent = ManusCompetition()
    agent.llm = MockLLM(scenario_responses)
    agent.available_tools.execute = MockTool().execute
    
    try:
        async for chunk in agent.run("Start simulation"):
            if chunk.get("type") == "status":
                print(f"[STATUS] {chunk['content']}")
            elif chunk.get("type") == "content":
                print(f"[CONTENT] {chunk['content']}")
        print(f"✅ {name} Finished successfully.")
    except Exception as e:
        print(f"❌ {name} Failed with error: {e}")

async def main():
    # Test 1: Handle Unicode/Complex Paths in Tool Args
    await run_simulation("Unicode Path Handling", [
        {
            "content": "I need to check the file.",
            "tool_calls": [{"name": "terminal", "args": {"command": 'dir "D:\\Thư mục âm thanh\\Ghi âm.m4a"'}}]
        }
    ])

    # Test 2: Handle Empty Tool Response (Agent should finish or prompt)
    await run_simulation("Empty Tool Call Handling", [
        {
            "content": "I finished my work.",
            "tool_calls": [] # Empty list
        }
    ])

    # Test 4: Extremely Long Tool Output (Potential 400 trigger)
    await run_simulation("Long Tool Output Handling", [
        {
            "content": "Searching for massive data...",
            "tool_calls": [{"name": "search", "args": {"query": "massive"}}]
        }
    ])

    # Test 6: Poisoned Control Tokens (Verification of Phase 9)
    await run_simulation("Control Token Sanitization", [
        {
            "content": "I am a helpful assistant <|end_header_id|>\nI will now call the tool.",
            "tool_calls": [{"name": "terminal", "args": {"command": "echo Success"}}]
        }
    ])

if __name__ == "__main__":
    asyncio.run(main())
