import json
import os
from typing import List, Dict, Any
from openai import AsyncOpenAI
from services.brawl_client import BrawlStarsClient
from services.vectorstore import PatchVectorStore

class BrawlAgent:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.brawl_client = BrawlStarsClient()
        self.vector_store = PatchVectorStore()

    def get_tools_definition(self) -> List[Dict[str, Any]]:
        """Define the tools the LLM can call dynamically."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_player_profile",
                    "description": "Fetch a player's trophy count, stats, and list of unlocked brawlers.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "player_tag": {
                                "type": "string",
                                "description": "The Brawl Stars player tag, e.g. #2Y0290P0Q"
                            }
                        },
                        "required": ["player_tag"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_battle_log",
                    "description": "Fetch a player's recent 25 battle logs including win/loss status, game modes, and maps played.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "player_tag": {
                                "type": "string",
                                "description": "The Brawl Stars player tag, e.g. #2Y0290P0Q"
                            }
                        },
                        "required": ["player_tag"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_patch_notes",
                    "description": "Search historical game balance changes, buffs, nerfs, and reworks from patch notes.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query about balance changes, stats, or mechanics."
                            },
                            "brawler_name": {
                                "type": "string",
                                "description": "Optional specific brawler name to filter by (e.g. 'Edgar', 'Shelly', 'Damian')."
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]

    async def execute_tool(self, tool_name: str, args: dict) -> str:
        """Executes the corresponding local Python function based on LLM choice."""
        if tool_name == "get_player_profile":
            profile = await self.brawl_client.get_player_profile(args["player_tag"])
            return profile.model_dump_json()

        elif tool_name == "get_battle_log":
            battles = await self.brawl_client.get_battle_log(args["player_tag"])
            # Return the last 5 battles to keep context concise
            recent_items = battles.items[:5] if battles.items else []
            return json.dumps([item.model_dump() for item in recent_items])

        elif tool_name == "search_patch_notes":
            results = self.vector_store.search(
                query=args["query"],
                n_results=3,
                brawler_name=args.get("brawler_name")
            )
            docs = results.get("documents", [[]])[0]
            return json.dumps(docs if docs else ["No matching patch notes found."])

        return json.dumps({"error": f"Tool {tool_name} not found"})

    async def run(self, player_tag: str, user_message: str) -> str:
        """Agentic loop: determines tool calls, executes them, and returns final answer."""
        system_prompt = f"""
You are a competitive Brawl Stars AI coach.
The user's player tag is: {player_tag}

GUIDELINES:
1. Always use your available tools to retrieve facts instead of relying on assumptions.
2. If the user asks about recent performance or match issues, call `get_battle_log`.
3. If the user asks about brawler stats, nerfs, buffs, or reworks, call `search_patch_notes`.
4. Provide precise, factual advice citing exact patch numbers and stats where available.
"""
        messages = [
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": user_message}
        ]

        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=self.get_tools_definition(),
            tool_choice="auto",
            temperature=0.2
        )

        response_message = response.choices[0].message
        messages.append(response_message)

        if response_message.tool_calls:
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)

                if "player_tag" in function_args and not function_args["player_tag"]:
                    function_args["player_tag"] = player_tag

                tool_result = await self.execute_tool(function_name, function_args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": function_name,
                    "content": tool_result
                })

            final_response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.2
            )
            return final_response.choices[0].message.content

        return response_message.content or "No response generated."