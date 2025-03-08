"""Tests for tool registry and built-in tools."""

import pytest
from app.core.tools import ToolRegistry, ToolCall


@pytest.fixture
def registry():
    return ToolRegistry()


@pytest.mark.asyncio
async def test_calculator_basic(registry):
    result = await registry.execute(ToolCall(name="calculator", arguments={"expression": "2 + 2"}))
    assert result.success
    assert "4" in result.output


@pytest.mark.asyncio
async def test_calculator_expression(registry):
    result = await registry.execute(ToolCall(name="calculator", arguments={"expression": "10 * 5 + 3"}))
    assert result.success
    assert "53" in result.output


@pytest.mark.asyncio
async def test_calculator_invalid(registry):
    result = await registry.execute(ToolCall(name="calculator", arguments={"expression": "import os"}))
    assert not result.success or "Error" in result.output


@pytest.mark.asyncio
async def test_current_time(registry):
    result = await registry.execute(ToolCall(name="current_time", arguments={}))
    assert result.success
    assert len(result.output) > 5  # should be a date string


@pytest.mark.asyncio
async def test_unknown_tool(registry):
    result = await registry.execute(ToolCall(name="nonexistent", arguments={}))
    assert not result.success


def test_parse_tool_calls(registry):
    text = "Let me calculate [TOOL: calculator(expression=2+2)] and get the time [TOOL: current_time()]"
    calls = registry.parse_tool_calls(text)
    assert len(calls) == 2
    assert calls[0].name == "calculator"
    assert calls[1].name == "current_time"


def test_list_tools(registry):
    tools = registry.list_tools()
    names = [t["name"] for t in tools]
    assert "calculator" in names
    assert "current_time" in names
    assert "web_search" in names


def test_format_for_prompt(registry):
    prompt = registry.format_for_prompt()
    assert "calculator" in prompt
    assert "TOOL:" in prompt
