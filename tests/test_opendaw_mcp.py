"""Unit tests for the opendaw_mcp package."""
import importlib

import opendaw_mcp
import opendaw_mcp.constants
import opendaw_mcp.genre_profiles
import opendaw_mcp.lite_tools
import opendaw_mcp.phase_tools


def test_package_exports() -> None:
    """Public names exported by opendaw_mcp.__init__ are present and match __all__."""
    expected = set(opendaw_mcp.__all__)
    for name in opendaw_mcp.__all__:
        assert hasattr(opendaw_mcp, name), f"{name} missing from package"
    # __all__ should not contain duplicates
    assert len(opendaw_mcp.__all__) == len(expected)


def test_constants_maps() -> None:
    """Constants maps contain expected keys and values."""
    assert opendaw_mcp.constants.TIDAL_RATE_MAP["1/4"] == 3
    assert opendaw_mcp.constants.DELAY_SYNC_MAP["1/4"] == 14
    assert "tanh" in opendaw_mcp.constants.WAVESHAPER_FUNCS
    assert "highPass" in opendaw_mcp.constants.REVAMP_SECTIONS
    assert opendaw_mcp.constants.REVAMP_SECTIONS == (
        "highPass",
        "lowShelf",
        "lowBell",
        "midBell",
        "highBell",
        "highShelf",
        "lowPass",
    )


def test_lite_tools_curated_list() -> None:
    """LITE_TOOLS is a list of 39 unique MCP tool names."""
    tools = opendaw_mcp.lite_tools.LITE_TOOLS
    assert isinstance(tools, list)
    assert len(tools) == 39
    assert len(set(tools)) == 39
    for tool in tools:
        assert isinstance(tool, str)
        assert tool.startswith("mcp_opendaw_")


def test_phase_tools_structure() -> None:
    """PHASE_TOOLS groups tool names by phase and ALL_PHASE_TOOLS is a set."""
    for phase, tools in opendaw_mcp.phase_tools.PHASE_TOOLS.items():
        assert phase in {"inspect", "compose", "mix", "render"}
        assert isinstance(tools, set)
        for tool in tools:
            assert isinstance(tool, str)
            assert tool.startswith("mcp_opendaw_")
    assert isinstance(opendaw_mcp.phase_tools.ALL_PHASE_TOOLS, set)
    assert all(isinstance(tool, str) for tool in opendaw_mcp.phase_tools.ALL_PHASE_TOOLS)


def test_genre_profiles() -> None:
    """Genre profile lookups and listing behave correctly."""
    pop = opendaw_mcp.genre_profiles.get_profile("pop")
    assert pop is not None
    assert pop["target_lufs"] == -10
    assert opendaw_mcp.genre_profiles.get_profile("POP") == pop
    assert opendaw_mcp.genre_profiles.get_profile("non-existent") is None
    genres = opendaw_mcp.genre_profiles.list_genres()
    assert isinstance(genres, list)
    assert "pop" in genres
    assert genres == sorted(genres)


def test_module_imports() -> None:
    """The opendaw_mcp package and submodules are importable."""
    for module_name in [
        "opendaw_mcp.constants",
        "opendaw_mcp.genre_profiles",
        "opendaw_mcp.lite_tools",
        "opendaw_mcp.music_theory",
        "opendaw_mcp.phase_tools",
        "opendaw_mcp.utils",
    ]:
        module = importlib.import_module(module_name)
        assert module.__name__ == module_name
