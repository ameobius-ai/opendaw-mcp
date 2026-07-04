# Agent Skills

8 bundled skills that teach LLM agents how to use opendaw-mcp effectively.

## What are skills?

Skills are markdown documents that provide procedural knowledge to LLM agents.
They're not runtime code — they're documentation that an agent loads when it
needs to understand how to accomplish a specific task.

## Available skills

| Skill | Description |
|-------|-------------|
| `opendaw-automation` | How to create automation: events, interpolation, sweeps |
| `opendaw-effect-routing` | Effect chains, sidechain, sends, buses, routing topology |
| `opendaw-genres` | Genre templates: house, techno, lofi, dnb, trap, ambient |
| `opendaw-sound-design` | Synth programming, patch design, sound creation |
| `opendaw-track-architecture` | Track layout, song structure, arrangement |
| `adaptive-mix-mastering` | Adaptive mixing and mastering with LUFS targeting |
| `dsp-script-authoring` | Writing custom DSP scripts for Werkstatt/Apparat/Spielwerk |
| `suno-to-opendaw` | Pipeline: Suno track → stem split → import → remix in DAW |

## Using skills with Hermes Agent

Skills are installed to `~/.hermes/profiles/producers/skills/creative/` and
loaded automatically by Hermes when relevant:

```bash
# List available skills
hermes skills list

# View a skill
hermes skills view opendaw-genres
```

## Using skills with other MCP clients

The skill markdown files can be loaded directly into any LLM context as
system prompts or reference documents:

```python
# Load a skill as context
with open("skills/opendaw-genres/SKILL.md") as f:
    genre_skill = f.read()

# Pass to your LLM as system context
system_prompt = f"""
You are a music production assistant.
Use the following skill guide for genre creation:

{genre_skill}
"""
```

## Skill structure

Each skill contains a `SKILL.md` with:

- **Trigger conditions** — when to use this skill
- **Numbered steps** — exact workflow with tool calls
- **Pitfalls** — common mistakes and how to avoid them
- **Verification** — how to confirm the result is correct

## Example: suno-to-opendaw

The `suno-to-opendaw` skill describes the full pipeline:

1. Generate a track with Suno (via chirp_generate)
2. Export the audio
3. Split into stems using `split_stems` (bs6 mode)
4. Import stems into openDAW as audio regions
5. Add effects, adjust levels, remix
6. Render the final mix

This is a unique workflow that combines AI music generation with DAW-based
production — no other tool provides this pipeline.
