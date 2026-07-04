# Agent Framework Integration

opendaw-mcp provides tool wrappers for popular agent frameworks. All wrappers
share the same underlying MCP server — pick the one that matches your stack.

## LangChain

```python
from opendaw_mcp.langchain_tools import OpendawToolkit

toolkit = OpendawToolkit()
tools = toolkit.get_tools()  # or filter by category
# tools = toolkit.get_tools(categories=["transport", "orchestration"])

# Use with any LangChain agent
from langchain.agents import create_react_agent, AgentExecutor
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
agent = create_react_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

executor.invoke({
    "input": "Create a dark techno track at 130 BPM with a driving kick, "
             "hypnotic bass, and reverb on the lead. Render to WAV."
})
```

### Category filtering

| Category | Tools | What's included |
|----------|-------|-----------------|
| `transport` | 3 | BPM, playback, time signature |
| `tracks` | 4 | Create synth/audio/note tracks, list tracks |
| `effects` | 4 | Add, configure, list, remove effects |
| `notes` | 3 | Create, list, quantize MIDI notes |
| `mixer` | 4 | Volume, pan, mute, mixer state |
| `export` | 4 | Render, export stems, measure LUFS, auto-gain |
| `orchestration` | 7 | Drum patterns, chord progressions, mastering, song structure |
| `stems` | 1 | Stem separation |

→ See [`examples/langchain_integration.py`](https://github.com/AMEOBIUS/opendaw-mcp/blob/main/examples/langchain_integration.py)

## AutoGen

```python
from opendaw_mcp.autogen_tools import get_autogen_tools, cleanup

tools = get_autogen_tools()

from autogen import AssistantAgent, UserProxyAgent

assistant = AssistantAgent(
    "producer",
    llm_config=llm_config,
    tools=tools,
    system_message=(
        "You are a music producer agent. Use the opendaw tools to "
        "create, mix, and render music. Always set BPM first."
    ),
)

user = UserProxyAgent("user", human_input_mode="NEVER")
user.initiate_chat(
    assistant,
    message="Create a house track at 124 BPM with 4-on-floor drums and render it"
)

# Clean up when done
import asyncio
asyncio.run(cleanup())
```

→ See [`examples/autogen_integration.py`](https://github.com/AMEOBIUS/opendaw-mcp/blob/main/examples/autogen_integration.py)

## MCP protocol (direct)

The server speaks MCP natively — no wrapper needed. Add to your MCP client config:

```json
{
  "mcpServers": {
    "opendaw": {
      "command": "opendaw-mcp",
      "env": {
        "OPENDAW_URL": "http://localhost:5174"
      }
    }
  }
}
```

Works with Claude Desktop, Cursor, Hermes Agent, and any MCP-compatible client.
All 263 tools are available directly.

## Hermes Agent

```yaml
# ~/.hermes/config.yaml
mcp:
  opendaw:
    command: opendaw-mcp
    env:
      OPENDAW_URL: http://localhost:5174
```

## Which should I use?

| Framework | When to use |
|-----------|-------------|
| **MCP direct** | Claude Desktop, Cursor, or any MCP client — all 263 tools |
| **LangChain** | Building agents with LangChain's tool-calling ecosystem |
| **AutoGen** | Multi-agent conversations with Microsoft AutoGen |
| **Hermes** | Hermes Agent framework with skill-based workflows |
