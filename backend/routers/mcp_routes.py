from fastapi import APIRouter
from typing import Dict, Union, Any

router = APIRouter(
    prefix="/mcp",
    tags=["MCP"],
)


def get_item(item_id: int) -> Dict[str, Any]:
    # Your existing business logic to fetch item details
    return {"item_id": item_id, "name": "Item Name", "description": "Item Description"}


async def analyze_text_sentiment_logic(text: str) -> Dict[str, Union[str, float]]:
    # This is the actual function that performs the sentiment analysis
    print(f"Analyzing sentiment for text: '{text}'")
    if "happy" in text.lower() or "joy" in text.lower():
        return {"sentiment": "positive", "score": 0.9}
    elif "sad" in text.lower() or "unhappy" in text.lower():
        return {"sentiment": "negative", "score": 0.7}
    else:
        return {"sentiment": "neutral", "score": 0.5}


async def get_system_status_logic() -> Dict[str, Any]:
    # This is the actual function to get system status
    print("Retrieving system status...")
    return {"cpu_usage": 0.15, "memory_usage": 0.60, "service_uptime_days": 7}


@router.get(
    "/tools/items/get_by_id",
    summary="Get an item by its ID (as a tool)",
    operation_id="getItemByIdTool",
)
async def get_item_as_tool(item_id: int) -> Dict[str, Any]:
    """
    Retrieves a specific item's details, exposed as an AI agent tool.
    """
    return await get_item(item_id)  # Reuse your existing business logic


# A new dedicated tool endpoint
@router.post(
    "/tools/text_analyzer/sentiment",
    summary="Analyze Text Sentiment",
    operation_id="analyzeTextSentimentTool",
)
async def text_analyzer_sentiment_endpoint(text: str) -> Dict[str, Union[str, float]]:
    """
    Analyzes the sentiment of a given text.
    """
    return await analyze_text_sentiment_logic(text)


@router.get(
    "/resources/system/status",
    summary="Get System Status",
    operation_id="getSystemStatusResource",
)
async def system_status_resource_endpoint() -> Dict[str, Any]:
    """
    Retrieves the current operational status of the system.
    """
    return await get_system_status_logic()


@router.get("/.well-known/ai-plugin.json", include_in_schema=False)
async def get_ai_plugin_manifest():
    return {
        "schema_version": "v1",
        "name_for_model": "my_unified_api_tools",
        "name_for_human": "My Unified API and AI Tools",
        "description_for_model": "A comprehensive API offering general services and specialized tools for AI agents.",
        "description_for_human": "Unified API with capabilities for AI agents.",
        "auth": {"type": "none"},  # Configure as needed for your auth setup
        "api": {"type": "openapi", "url": "http://localhost:8000/openapi.json"},
        "logo_url": "http://localhost:8000/logo.png",
        "contact_email": "your_email@example.com",
    }


# Root endpoint (can be kept as is or modified)
@router.get("/", summary="Root Endpoint")
async def root():
    return {
        "message": "Welcome to My Integrated FastAPI App! Access /docs for API documentation."
    }


"""
Your FastAPI setup with the MCP router and the ai-plugin.json manifest is a solid foundation for allowing AI agents to use your defined tools. Here's how agents typically interact with such a setup:

Plugin Discovery (via ai-plugin.json):

You provide the URL of your manifest file (e.g., http://your-fastapi-app-url/mcp/.well-known/ai-plugin.json) to the AI agent or the platform it runs on.
The agent fetches this JSON file. It contains metadata about your toolset, including:
name_for_model: How the AI model will refer to your set of tools.
description_for_model: A description the AI uses to understand when to use your tools.
api.url: Crucially, this points to your OpenAPI schema (e.g., http://localhost:8000/openapi.json).
API Specification (via openapi.json):

The agent (or its underlying system) fetches the OpenAPI schema from the URL specified in the manifest.
This schema details all your API endpoints, including those under /mcp/tools/. For each tool endpoint, it describes:
The HTTP method (GET, POST, etc.).
The path (e.g., /mcp/tools/items/get_by_id).
Required and optional parameters (like item_id: int or text: str).
The structure of the expected request and response.
The operation_id, summary, and description you've defined, which help the agent understand the tool's purpose.
Agent Tool Selection and Execution:

When the AI agent processes a user's request or works on a task, its reasoning process might determine that it needs a capability your MCP offers.
Based on the description_for_model from the manifest and the detailed descriptions of each tool from the OpenAPI schema, the agent selects the appropriate tool (e.g., getItemByIdTool or analyzeTextSentimentTool).
The agent then constructs an HTTP request to the chosen endpoint, including the necessary parameters it has gathered or inferred.
Your FastAPI server receives this request, routes it to the correct function in mcp_routes.py, and your logic is executed.
The response (e.g., item details or sentiment analysis results) is returned to the agent as JSON.
Using the Tool's Output:

The agent incorporates the information received from your tool into its ongoing task or uses it to formulate a response to the user.
To enable this:

Ensure Accessibility: Your FastAPI server, including the /mcp/.well-known/ai-plugin.json and /openapi.json endpoints, must be network-accessible to the AI agent. If running locally for development, the agent also needs to run in an environment that can reach localhost.
Agent Configuration: The specific AI agent or platform you're using (e.g., custom LangChain agent, OpenAI's GPTs with plugin support, etc.) will have its own method for registering or being configured with your plugin manifest URL.
Clear Descriptions: The summary and description fields for your tool endpoints in FastAPI (which translate to the OpenAPI schema) are very important. They guide the AI in choosing the correct tool and using it properly. Your current descriptions and operation_ids are good examples.
Authentication (Future Consideration): Your current manifest specifies "auth": {"type": "none"}. For production or sensitive tools, you'd implement an authentication mechanism (e.g., API keys, OAuth) and describe it in the manifest and OpenAPI schema. The agent would then need to handle authentication.
Your server-side code is well-prepared. The next step is to integrate it with an AI agent by providing the agent with the URL to your ai-plugin.json manifest. The agent framework will then handle the interpretation of the OpenAPI spec and the calling of your tool endpoints.
"""
