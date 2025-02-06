"""Chat service - orchestrates LLM, memory, RAG, tools, and suggestions."""

from __future__ import annotations

import logging
import uuid

from app.core.llm import LLMProvider
from app.core.memory import MemoryManager
from app.core.rag import RAGPipeline
from app.core.semantic import extract_facts, estimate_importance
from app.core.sentiment import analyze_sentiment, extract_topics
from app.core.suggestions import SuggestionEngine
from app.core.tools import ToolRegistry

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Swiftie, a friendly and intelligent personal assistant.
You remember details about the user across conversations and use them naturally.
Be concise, warm, and genuinely helpful. Adapt your communication style to the user.

When you have context from memory, weave it in naturally — don't explicitly say
"according to my memory". Just use the information as if you naturally know it."""


class ChatService:
    def __init__(
        self,
        llm: LLMProvider,
        memory: MemoryManager,
        rag: RAGPipeline,
        tools: ToolRegistry | None = None,
        suggestions: SuggestionEngine | None = None,
    ):
        self.llm = llm
        self.memory = memory
        self.rag = rag
        self.tools = tools
        self.suggestions = suggestions

    async def respond(self, session_id: str, message: str) -> str:
        # build context
        history = self.memory.get_context(session_id)
        docs = self.rag.retrieve(message)
        context = self.rag.format_context(docs)

        # recalled long-term memories
        recalled = self.memory.recall(message, limit=5)
        mem_context = ""
        if recalled:
            mem_context = "\n\nRelevant memories:\n" + "\n".join(
                f"- {m.content}" for m in recalled
            )

        system = SYSTEM_PROMPT
        if context:
            system += f"\n\n{context}"
        if mem_context:
            system += mem_context

        # tool descriptions
        if self.tools:
            system += "\n\n" + self.tools.format_for_prompt()

        messages = history + [{"role": "user", "content": message}]
        response = await self.llm.generate(messages, system=system)
        reply = response.content

        # handle tool calls in response
        if self.tools:
            tool_calls = self.tools.parse_tool_calls(reply)
            if tool_calls:
                tool_results = []
                for call in tool_calls:
                    result = await self.tools.execute(call)
                    tool_results.append(f"[{call.name}]: {result.output}")
                # add tool results and get final response
                tool_msg = "\n".join(tool_results)
                messages.append({"role": "assistant", "content": reply})
                messages.append({"role": "user", "content": f"Tool results:\n{tool_msg}\n\nNow answer the user."})
                response = await self.llm.generate(messages, system=SYSTEM_PROMPT)
                reply = response.content

        # persist conversation
        self.memory.save(session_id, "user", message)
        self.memory.save(session_id, "assistant", reply)

        # store in RAG corpus
        self.rag.store(
            doc_id=str(uuid.uuid4()),
            text=f"User: {message}\nAssistant: {reply}",
            metadata={"session_id": session_id},
        )

        # extract and store semantic facts
        facts = extract_facts(message)
        for fact in facts:
            self.memory.create_semantic(fact)
            logger.debug("Extracted fact: %s", fact)

        # episodic memory for important messages
        importance = estimate_importance(message)
        if importance > 0.4:
            self.memory.create_episodic(
                content=f"User said: {message}",
                importance=importance,
                session_id=session_id,
            )

        # track topics for suggestions
        if self.suggestions:
            topics = extract_topics(message)
            self.suggestions.record_interaction(topics)

        return reply

    async def stream_respond(self, session_id: str, message: str):
        """Stream response tokens."""
        history = self.memory.get_context(session_id)
        docs = self.rag.retrieve(message)
        context = self.rag.format_context(docs)

        system = SYSTEM_PROMPT
        if context:
            system += f"\n\n{context}"

        messages = history + [{"role": "user", "content": message}]
        full_reply = ""
        async for chunk in self.llm.stream(messages, system=system):
            if chunk.delta:
                full_reply += chunk.delta
                yield chunk.delta

        # persist after streaming completes
        self.memory.save(session_id, "user", message)
        self.memory.save(session_id, "assistant", full_reply)
        self.rag.store(
            doc_id=str(uuid.uuid4()),
            text=f"User: {message}\nAssistant: {full_reply}",
            metadata={"session_id": session_id},
        )
