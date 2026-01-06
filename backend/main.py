"""FastAPI backend for LLM Council."""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import uuid
import json
import asyncio

from . import storage
from .council import (
    generate_conversation_title,
    generate_search_query,
    stage1_collect_responses,
    stage2_collect_rankings,
    stage3_synthesize_final,
    calculate_aggregate_rankings,
    PROVIDERS,
)
from .search import perform_web_search, SearchProvider
from .settings import (
    get_settings,
    update_settings,
    Settings,
    DEFAULT_COUNCIL_MODELS,
    DEFAULT_CHAIRMAN_MODEL,
    AVAILABLE_MODELS,
)
from .error_logger import log_event

app = FastAPI(title="LLM Council Plus API")

# Enable CORS for local development and network access
# Allow requests from any hostname on ports 5173 and 3000 (frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://.*:(5173|3000)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""

    pass


class SendMessageRequest(BaseModel):
    """Request to send a message in a conversation."""

    content: str
    web_search: bool = False
    execution_mode: str = "full"  # 'chat_only', 'chat_ranking', 'full'


class ConversationMetadata(BaseModel):
    """Conversation metadata for list view."""

    id: str
    created_at: str
    title: str
    message_count: int


class Conversation(BaseModel):
    """Full conversation with all messages."""

    id: str
    created_at: str
    title: str
    messages: List[Dict[str, Any]]


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "LLM Council API"}


@app.get("/api/conversations", response_model=List[ConversationMetadata])
async def list_conversations():
    """List all conversations (metadata only)."""
    return storage.list_conversations()


@app.post("/api/conversations", response_model=Conversation)
async def create_conversation(request: CreateConversationRequest):
    """Create a new conversation."""
    conversation_id = str(uuid.uuid4())
    conversation = storage.create_conversation(conversation_id)
    return conversation


@app.get("/api/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str):
    """Get a specific conversation with all its messages."""
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation."""
    deleted = storage.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "deleted"}


@app.post("/api/conversations/{conversation_id}/message/stream")
async def send_message_stream(
    conversation_id: str, body: SendMessageRequest, request: Request
):
    """Send a message and stream the 3-stage council process."""
    # Validate execution_mode
    valid_modes = ["chat_only", "chat_ranking", "full"]
    if body.execution_mode not in valid_modes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid execution_mode. Must be one of: {valid_modes}",
        )

    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    async def event_generator():
        try:
            # Initialize variables for metadata
            stage1_results = []
            stage2_results = []
            stage3_result = None
            label_to_model = {}
            aggregate_rankings = {}

            # Add user message
            storage.add_user_message(conversation_id, body.content)

            # Start title generation in parallel (don't await yet)
            title_task = None
            if is_first_message:
                title_task = asyncio.create_task(
                    generate_conversation_title(body.content)
                )

            # Perform web search if requested
            search_context = ""
            search_query = ""
            if body.web_search:
                # Check for disconnect before starting search
                if await request.is_disconnected():
                    await log_event(
                        conversation_id,
                        "client_disconnect",
                        {"stage": "web_search", "reason": "disconnected"},
                        level="WARN",
                    )
                    raise asyncio.CancelledError("Client disconnected")

                settings = get_settings()
                provider = SearchProvider(settings.search_provider)

                # Set API keys if configured
                if settings.tavily_api_key and provider == SearchProvider.TAVILY:
                    os.environ["TAVILY_API_KEY"] = settings.tavily_api_key
                if settings.brave_api_key and provider == SearchProvider.BRAVE:
                    os.environ["BRAVE_API_KEY"] = settings.brave_api_key

                yield f"data: {json.dumps({'type': 'search_start', 'data': {'provider': provider.value}})}\n\n"

                # Check for disconnect before generating search query
                if await request.is_disconnected():
                    await log_event(
                        conversation_id,
                        "client_disconnect",
                        {"stage": "search_setup", "reason": "disconnected"},
                        level="WARN",
                    )
                    raise asyncio.CancelledError("Client disconnected")

                # Generate search query (passthrough - no AI model needed)
                search_query = generate_search_query(body.content)

                # Check for disconnect before performing search
                if await request.is_disconnected():
                    await log_event(
                        conversation_id,
                        "client_disconnect",
                        {"stage": "search_execution", "reason": "disconnected"},
                        level="WARN",
                    )
                    raise asyncio.CancelledError("Client disconnected")

                # Run search (now fully async for Tavily/Brave, threaded only for DuckDuckGo)
                search_result = await perform_web_search(
                    search_query,
                    5,
                    provider,
                    settings.full_content_results,
                    settings.search_keyword_extraction,
                )
                search_context = search_result["results"]
                extracted_query = search_result["extracted_query"]
                yield f"data: {json.dumps({'type': 'search_complete', 'data': {'search_query': search_query, 'extracted_query': extracted_query, 'search_context': search_context, 'provider': provider.value}})}\n\n"
                await asyncio.sleep(0.05)

            # Stage 1: Collect responses
            yield f"data: {json.dumps({'type': 'stage1_start'})}\n\n"
            await asyncio.sleep(0.05)

            total_models = 0

            async for item in stage1_collect_responses(
                conversation_id, body.content, search_context, request
            ):
                if isinstance(item, int):
                    total_models = item
                    await log_event(
                        conversation_id,
                        "stage1_init",
                        {
                            "total_models": total_models,
                            "query_preview": body.content[:100] + "..."
                            if len(body.content) > 100
                            else body.content,
                            "search_enabled": body.web_search,
                        },
                        level="INFO",
                    )
                    yield f"data: {json.dumps({'type': 'stage1_init', 'total': total_models})}\n\n"
                    continue

                stage1_results.append(item)
                yield f"data: {json.dumps({'type': 'stage1_progress', 'data': item, 'count': len(stage1_results), 'total': total_models})}\n\n"
                await asyncio.sleep(0.01)

            # Calculate success/failure stats for Stage 1
            stage1_success = len([r for r in stage1_results if not r.get("error")])
            stage1_failed = len([r for r in stage1_results if r.get("error")])
            await log_event(
                conversation_id,
                "stage1_complete",
                {
                    "total": len(stage1_results),
                    "success": stage1_success,
                    "failed": stage1_failed,
                },
                level="INFO",
            )
            yield f"data: {json.dumps({'type': 'stage1_complete', 'data': stage1_results})}\n\n"
            await asyncio.sleep(0.05)

            # Check if any models responded successfully in Stage 1
            if not any(r for r in stage1_results if not r.get("error")):
                error_msg = "All models failed to respond in Stage 1, likely due to rate limits or API errors. Please try again or adjust your model selection."
                storage.add_error_message(conversation_id, error_msg)
                yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
                return  # Stop further processing

            # Stage 2: Only if mode is 'chat_ranking' or 'full'
            if body.execution_mode in ["chat_ranking", "full"]:
                yield f"data: {json.dumps({'type': 'stage2_start'})}\n\n"
                await asyncio.sleep(0.05)

                # Iterate over the async generator
                async for item in stage2_collect_rankings(
                    conversation_id,
                    body.content,
                    stage1_results,
                    search_context,
                    request,
                ):
                    # First item is the label mapping
                    if isinstance(item, dict) and not item.get("model"):
                        label_to_model = item
                        # Send init event with total count
                        yield f"data: {json.dumps({'type': 'stage2_init', 'total': len(label_to_model)})}\n\n"
                        continue

                    # Subsequent items are results
                    stage2_results.append(item)

                    # Send progress update
                    await log_event(
                        conversation_id,
                        "stage2_progress",
                        {
                            "progress": f"{len(stage2_results)}/{len(label_to_model)}",
                            "model": item["model"],
                        },
                        level="INFO",
                    )
                    yield f"data: {json.dumps({'type': 'stage2_progress', 'data': item, 'count': len(stage2_results), 'total': len(label_to_model)})}\n\n"
                    await asyncio.sleep(0.01)

                aggregate_rankings = calculate_aggregate_rankings(
                    stage2_results, label_to_model
                )
                yield f"data: {json.dumps({'type': 'stage2_complete', 'data': stage2_results, 'metadata': {'label_to_model': label_to_model, 'aggregate_rankings': aggregate_rankings, 'search_query': search_query, 'search_context': search_context}})}\n\n"
                await asyncio.sleep(0.05)

            # Stage 3: Only if mode is 'full'
            if body.execution_mode == "full":
                yield f"data: {json.dumps({'type': 'stage3_start'})}\n\n"
                await asyncio.sleep(0.05)

                # Check for disconnect before starting Stage 3
                if await request.is_disconnected():
                    await log_event(
                        conversation_id,
                        "client_disconnect",
                        {"stage": "stage3", "reason": "disconnected"},
                        level="WARN",
                    )
                    raise asyncio.CancelledError("Client disconnected")

                stage3_result = await stage3_synthesize_final(
                    conversation_id,
                    body.content,
                    stage1_results,
                    stage2_results,
                    search_context,
                )
                # Log stage3 completion
                await log_event(
                    conversation_id,
                    "stage3_complete",
                    {
                        "success": not stage3_result.get("error"),
                        "chairman_model": stage3_result.get("model", "unknown"),
                        "response_length": len(stage3_result.get("response", "") or ""),
                    },
                    level="INFO",
                )
                yield f"data: {json.dumps({'type': 'stage3_complete', 'data': stage3_result})}\n\n"

            # Wait for title generation if it was started
            if title_task:
                try:
                    title = await title_task
                    storage.update_conversation_title(conversation_id, title)
                    yield f"data: {json.dumps({'type': 'title_complete', 'data': {'title': title}})}\n\n"
                except Exception as e:
                    await log_event(
                        conversation_id, "title_error", {"error": str(e)}, level="ERROR"
                    )

            # Save complete assistant message with metadata
            metadata = {
                "execution_mode": body.execution_mode,  # Save mode for historical context
            }

            # Only include stage2/stage3 metadata if they were executed
            if body.execution_mode in ["chat_ranking", "full"]:
                metadata["label_to_model"] = label_to_model
                metadata["aggregate_rankings"] = aggregate_rankings

            if search_context:
                metadata["search_context"] = search_context
            if search_query:
                metadata["search_query"] = search_query

            storage.add_assistant_message(
                conversation_id,
                stage1_results,
                stage2_results
                if body.execution_mode in ["chat_ranking", "full"]
                else None,
                stage3_result if body.execution_mode == "full" else None,
                metadata,
            )

            # Send completion event
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

        except asyncio.CancelledError:
            await log_event(
                "stream_cancelled", {"conversation_id": conversation_id}, level="INFO"
            )
            # Even if cancelled, try to save the title if it's ready or nearly ready
            if title_task:
                try:
                    # Give it a small grace period to finish if it's close
                    title = await asyncio.wait_for(title_task, timeout=2.0)
                    storage.update_conversation_title(conversation_id, title)
                    await log_event(
                        "title_saved",
                        {"title": title, "despite_cancellation": True},
                        level="INFO",
                    )
                except Exception as e:
                    await log_event(
                        conversation_id,
                        "title_save_error",
                        {"error": str(e)},
                        level="WARN",
                    )
            raise
        except Exception as e:
            await log_event(
                conversation_id, "stream_error", {"error": str(e)}, level="ERROR"
            )
            # Save error to conversation history
            storage.add_error_message(conversation_id, f"Error: {str(e)}")
            # Send error event
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


class UpdateSettingsRequest(BaseModel):
    """Request to update settings."""

    search_provider: Optional[str] = None
    search_keyword_extraction: Optional[str] = None
    ollama_base_url: Optional[str] = None
    full_content_results: Optional[int] = None

    # Custom OpenAI-compatible endpoint
    custom_endpoint_name: Optional[str] = None
    custom_endpoint_url: Optional[str] = None
    custom_endpoint_api_key: Optional[str] = None

    # API Keys
    tavily_api_key: Optional[str] = None
    brave_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    mistral_api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None

    # Enabled Providers
    enabled_providers: Optional[Dict[str, bool]] = None
    direct_provider_toggles: Optional[Dict[str, bool]] = None

    # Council Configuration (unified)
    council_models: Optional[List[str]] = None
    chairman_model: Optional[str] = None

    # Remote/Local filters
    council_member_filters: Optional[Dict[int, str]] = None
    chairman_filter: Optional[str] = None
    search_query_filter: Optional[str] = None

    # Temperature Settings
    council_temperature: Optional[float] = None
    chairman_temperature: Optional[float] = None
    stage2_temperature: Optional[float] = None

    # Execution Mode
    execution_mode: Optional[str] = None

    # System Prompts
    stage1_prompt: Optional[str] = None
    stage2_prompt: Optional[str] = None
    stage3_prompt: Optional[str] = None

    # Logging Settings
    logging_enabled: Optional[bool] = None
    logging_level: Optional[str] = None
    logging_folder: Optional[str] = None


class TestTavilyRequest(BaseModel):
    """Request to test Tavily API key."""

    api_key: str | None = None


@app.get("/api/settings")
async def get_app_settings():
    """Get current application settings."""
    settings = get_settings()
    return {
        "search_provider": settings.search_provider,
        "search_keyword_extraction": settings.search_keyword_extraction,
        "ollama_base_url": settings.ollama_base_url,
        "full_content_results": settings.full_content_results,
        # Custom Endpoint
        "custom_endpoint_name": settings.custom_endpoint_name,
        "custom_endpoint_url": settings.custom_endpoint_url,
        # Don't send the API key to frontend for security
        # API Key Status
        "tavily_api_key_set": bool(settings.tavily_api_key),
        "brave_api_key_set": bool(settings.brave_api_key),
        "openrouter_api_key_set": bool(settings.openrouter_api_key),
        "openai_api_key_set": bool(settings.openai_api_key),
        "anthropic_api_key_set": bool(settings.anthropic_api_key),
        "google_api_key_set": bool(settings.google_api_key),
        "mistral_api_key_set": bool(settings.mistral_api_key),
        "deepseek_api_key_set": bool(settings.deepseek_api_key),
        "groq_api_key_set": bool(settings.groq_api_key),
        "custom_endpoint_api_key_set": bool(settings.custom_endpoint_api_key),
        # Enabled Providers
        "enabled_providers": settings.enabled_providers,
        "direct_provider_toggles": settings.direct_provider_toggles,
        # Council Configuration (unified)
        "council_models": settings.council_models,
        "chairman_model": settings.chairman_model,
        # Remote/Local filters
        "council_member_filters": settings.council_member_filters,
        "chairman_filter": settings.chairman_filter,
        "search_query_filter": settings.search_query_filter,
        # Temperature Settings
        "council_temperature": settings.council_temperature,
        "chairman_temperature": settings.chairman_temperature,
        "stage2_temperature": settings.stage2_temperature,
        # Prompts
        "stage1_prompt": settings.stage1_prompt,
        "stage2_prompt": settings.stage2_prompt,
        "stage3_prompt": settings.stage3_prompt,
        # Logging Settings
        "logging_enabled": settings.logging_enabled,
        "logging_level": settings.logging_level,
        "logging_folder": settings.logging_folder,
    }


@app.get("/api/settings/defaults")
async def get_default_settings():
    """Get default model settings."""
    from .prompts import (
        STAGE1_PROMPT_DEFAULT,
        STAGE2_PROMPT_DEFAULT,
        STAGE3_PROMPT_DEFAULT,
        TITLE_PROMPT_DEFAULT,
    )
    from .settings import DEFAULT_ENABLED_PROVIDERS

    return {
        "council_models": DEFAULT_COUNCIL_MODELS,
        "chairman_model": DEFAULT_CHAIRMAN_MODEL,
        "enabled_providers": DEFAULT_ENABLED_PROVIDERS,
        "stage1_prompt": STAGE1_PROMPT_DEFAULT,
        "stage2_prompt": STAGE2_PROMPT_DEFAULT,
        "stage3_prompt": STAGE3_PROMPT_DEFAULT,
    }


@app.put("/api/settings")
async def update_app_settings(request: UpdateSettingsRequest):
    """Update application settings."""
    updates = {}

    if request.search_provider is not None:
        # Validate provider
        try:
            provider = SearchProvider(request.search_provider)
            updates["search_provider"] = provider
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid search provider. Must be one of: {[p.value for p in SearchProvider]}",
            )

    if request.search_keyword_extraction is not None:
        if request.search_keyword_extraction not in ["direct", "yake"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid keyword extraction mode. Must be 'direct' or 'yake'",
            )
        updates["search_keyword_extraction"] = request.search_keyword_extraction

    if request.ollama_base_url is not None:
        updates["ollama_base_url"] = request.ollama_base_url

    # Custom endpoint
    if request.custom_endpoint_name is not None:
        updates["custom_endpoint_name"] = request.custom_endpoint_name
    if request.custom_endpoint_url is not None:
        updates["custom_endpoint_url"] = request.custom_endpoint_url
    if request.custom_endpoint_api_key is not None:
        updates["custom_endpoint_api_key"] = request.custom_endpoint_api_key

    if request.full_content_results is not None:
        # Validate range
        if request.full_content_results < 0 or request.full_content_results > 10:
            raise HTTPException(
                status_code=400, detail="full_content_results must be between 0 and 10"
            )
        updates["full_content_results"] = request.full_content_results

    # Prompt updates
    if request.stage1_prompt is not None:
        updates["stage1_prompt"] = request.stage1_prompt
    if request.stage2_prompt is not None:
        updates["stage2_prompt"] = request.stage2_prompt
    if request.stage3_prompt is not None:
        updates["stage3_prompt"] = request.stage3_prompt

    if request.tavily_api_key is not None:
        updates["tavily_api_key"] = request.tavily_api_key
        # Also set in environment for immediate use
        if request.tavily_api_key:
            os.environ["TAVILY_API_KEY"] = request.tavily_api_key

    if request.brave_api_key is not None:
        updates["brave_api_key"] = request.brave_api_key
        # Also set in environment for immediate use
        if request.brave_api_key:
            os.environ["BRAVE_API_KEY"] = request.brave_api_key

    if request.openrouter_api_key is not None:
        updates["openrouter_api_key"] = request.openrouter_api_key

    # Direct Provider Keys
    if request.openai_api_key is not None:
        updates["openai_api_key"] = request.openai_api_key
    if request.anthropic_api_key is not None:
        updates["anthropic_api_key"] = request.anthropic_api_key
    if request.google_api_key is not None:
        updates["google_api_key"] = request.google_api_key
    if request.mistral_api_key is not None:
        updates["mistral_api_key"] = request.mistral_api_key
    if request.deepseek_api_key is not None:
        updates["deepseek_api_key"] = request.deepseek_api_key
    if request.groq_api_key is not None:
        updates["groq_api_key"] = request.groq_api_key

    # Enabled Providers
    if request.enabled_providers is not None:
        updates["enabled_providers"] = request.enabled_providers

    if request.direct_provider_toggles is not None:
        updates["direct_provider_toggles"] = request.direct_provider_toggles

    # Council Configuration (unified)
    if request.council_models is not None:
        # Validate that at least two models are selected
        if len(request.council_models) < 2:
            raise HTTPException(
                status_code=400, detail="At least two council models must be selected"
            )
        if len(request.council_models) > 8:
            raise HTTPException(
                status_code=400, detail="Maximum of 8 council models allowed"
            )
        updates["council_models"] = request.council_models

    if request.chairman_model is not None:
        updates["chairman_model"] = request.chairman_model

    # Remote/Local filters
    if request.council_member_filters is not None:
        updates["council_member_filters"] = request.council_member_filters
    if request.chairman_filter is not None:
        updates["chairman_filter"] = request.chairman_filter
    if request.search_query_filter is not None:
        updates["search_query_filter"] = request.search_query_filter

    # Temperature Settings
    if request.council_temperature is not None:
        updates["council_temperature"] = request.council_temperature
    if request.chairman_temperature is not None:
        updates["chairman_temperature"] = request.chairman_temperature
    if request.stage2_temperature is not None:
        updates["stage2_temperature"] = request.stage2_temperature

    # Execution Mode
    if request.execution_mode is not None:
        valid_modes = ["chat_only", "chat_ranking", "full"]
        if request.execution_mode not in valid_modes:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid execution_mode. Must be one of: {valid_modes}",
            )
        updates["execution_mode"] = request.execution_mode

    # Logging Settings
    if request.logging_enabled is not None:
        updates["logging_enabled"] = request.logging_enabled
    if request.logging_level is not None:
        # Validate log level
        if request.logging_level not in ["all", "errors_only", "debug"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid logging level. Must be 'all', 'errors_only', or 'debug'",
            )
        updates["logging_level"] = request.logging_level
    if request.logging_folder is not None:
        updates["logging_folder"] = request.logging_folder

    if updates:
        settings = update_settings(**updates)
    else:
        settings = get_settings()

    return {
        "search_provider": settings.search_provider,
        "search_keyword_extraction": settings.search_keyword_extraction,
        "ollama_base_url": settings.ollama_base_url,
        "full_content_results": settings.full_content_results,
        # Custom Endpoint
        "custom_endpoint_name": settings.custom_endpoint_name,
        "custom_endpoint_url": settings.custom_endpoint_url,
        # API Key Status
        "tavily_api_key_set": bool(settings.tavily_api_key),
        "brave_api_key_set": bool(settings.brave_api_key),
        "openrouter_api_key_set": bool(settings.openrouter_api_key),
        "openai_api_key_set": bool(settings.openai_api_key),
        "anthropic_api_key_set": bool(settings.anthropic_api_key),
        "google_api_key_set": bool(settings.google_api_key),
        "mistral_api_key_set": bool(settings.mistral_api_key),
        "deepseek_api_key_set": bool(settings.deepseek_api_key),
        "groq_api_key_set": bool(settings.groq_api_key),
        "custom_endpoint_api_key_set": bool(settings.custom_endpoint_api_key),
        # Enabled Providers
        "enabled_providers": settings.enabled_providers,
        "direct_provider_toggles": settings.direct_provider_toggles,
        # Council Configuration (unified)
        "council_models": settings.council_models,
        "chairman_model": settings.chairman_model,
        # Remote/Local filters
        "council_member_filters": settings.council_member_filters,
        "chairman_filter": settings.chairman_filter,
        # Prompts
        "stage1_prompt": settings.stage1_prompt,
        "stage2_prompt": settings.stage2_prompt,
        "stage3_prompt": settings.stage3_prompt,
    }


@app.get("/api/models")
async def get_models():
    """Get available models for council selection."""
    from .openrouter import fetch_models

    # Try dynamic fetch first
    dynamic_models = await fetch_models()
    if dynamic_models:
        return {"models": dynamic_models}

    # Fallback to static list
    return {"models": AVAILABLE_MODELS}


@app.get("/api/models/direct")
async def get_direct_models():
    """Get available models from all configured direct providers."""
    all_models = []

    # Iterate over all providers
    for provider_id, provider in PROVIDERS.items():
        # Skip OpenRouter and Ollama as they are handled separately
        if provider_id in ["openrouter", "ollama", "hybrid"]:
            continue

        try:
            # Fetch models from provider
            models = await provider.get_models()
            all_models.extend(models)
        except Exception as e:
            await log_event(
                "model_fetch_error",
                {"provider": provider_id, "error": str(e)},
                level="ERROR",
            )

    return all_models


@app.post("/api/settings/test-tavily")
async def test_tavily_api(request: TestTavilyRequest):
    """Test Tavily API key with a simple search."""
    import httpx

    settings = get_settings()

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": request.api_key or settings.tavily_api_key,
                    "query": "test",
                    "max_results": 1,
                    "search_depth": "basic",
                },
            )

            if response.status_code == 200:
                return {"success": True, "message": "API key is valid"}
            elif response.status_code == 401:
                return {"success": False, "message": "Invalid API key"}
            else:
                return {
                    "success": False,
                    "message": f"API error: {response.status_code}",
                }

    except httpx.TimeoutException:
        return {"success": False, "message": "Request timed out"}
    except Exception as e:
        return {"success": False, "message": str(e)}


class TestBraveRequest(BaseModel):
    """Request to test Brave API key."""

    api_key: str | None = None


@app.post("/api/settings/test-brave")
async def test_brave_api(request: TestBraveRequest):
    """Test Brave API key with a simple search."""
    import httpx

    settings = get_settings()

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": "test", "count": 1},
                headers={
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip",
                    "X-Subscription-Token": request.api_key or settings.brave_api_key,
                },
            )

            if response.status_code == 200:
                return {"success": True, "message": "API key is valid"}
            elif response.status_code == 401 or response.status_code == 403:
                return {"success": False, "message": "Invalid API key"}
            else:
                return {
                    "success": False,
                    "message": f"API error: {response.status_code}",
                }

    except httpx.TimeoutException:
        return {"success": False, "message": "Request timed out"}
    except Exception as e:
        return {"success": False, "message": str(e)}


class TestOpenRouterRequest(BaseModel):
    """Request to test OpenRouter API key."""

    api_key: Optional[str] = None


class TestProviderRequest(BaseModel):
    """Request to test a specific provider's API key."""

    provider_id: str
    api_key: str


@app.post("/api/settings/test-provider")
async def test_provider_api(request: TestProviderRequest):
    """Test an API key for a specific provider."""
    from .council import PROVIDERS
    from .settings import get_settings

    if request.provider_id not in PROVIDERS:
        raise HTTPException(status_code=400, detail="Invalid provider ID")

    api_key = request.api_key
    if not api_key:
        # Try to get from settings
        settings = get_settings()
        # Map provider_id to setting key (e.g. 'openai' -> 'openai_api_key')
        setting_key = f"{request.provider_id}_api_key"
        if hasattr(settings, setting_key):
            api_key = getattr(settings, setting_key)

    if not api_key:
        return {"success": False, "message": "No API key provided or configured"}

    provider = PROVIDERS[request.provider_id]
    return await provider.validate_key(api_key)


class TestOllamaRequest(BaseModel):
    """Request to test Ollama connection."""

    base_url: str


@app.get("/api/ollama/tags")
async def get_ollama_tags(base_url: Optional[str] = None):
    """Fetch available models from Ollama."""
    import httpx
    from .config import get_ollama_base_url

    if not base_url:
        base_url = get_ollama_base_url()

    if base_url.endswith("/"):
        base_url = base_url[:-1]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{base_url}/api/tags")

            if response.status_code != 200:
                return {
                    "models": [],
                    "error": f"Ollama API error: {response.status_code}",
                }

            data = response.json()
            models = []
            for model in data.get("models", []):
                models.append(
                    {
                        "id": model.get("name"),
                        "name": model.get("name"),
                        # Ollama doesn't return context length in tags
                        "context_length": None,
                        "is_free": True,
                        "modified_at": model.get("modified_at"),
                    }
                )

            # Sort by modified_at (newest first), fallback to name
            models.sort(key=lambda x: x.get("modified_at", ""), reverse=True)
            return {"models": models}

    except httpx.ConnectError:
        return {"models": [], "error": "Could not connect to Ollama. Is it running?"}
    except Exception as e:
        return {"models": [], "error": str(e)}


@app.post("/api/settings/test-ollama")
async def test_ollama_connection(request: TestOllamaRequest):
    """Test connection to Ollama instance."""
    import httpx

    base_url = request.base_url
    if base_url.endswith("/"):
        base_url = base_url[:-1]

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{base_url}/api/tags")

            if response.status_code == 200:
                return {"success": True, "message": "Successfully connected to Ollama"}
            else:
                return {
                    "success": False,
                    "message": f"Ollama API error: {response.status_code}",
                }

    except httpx.ConnectError:
        return {
            "success": False,
            "message": "Could not connect to Ollama. Is it running at this URL?",
        }
    except Exception as e:
        return {"success": False, "message": str(e)}


class TestCustomEndpointRequest(BaseModel):
    """Request to test custom OpenAI-compatible endpoint."""

    name: str
    url: str
    api_key: Optional[str] = None


@app.post("/api/settings/test-custom-endpoint")
async def test_custom_endpoint(request: TestCustomEndpointRequest):
    """Test connection to a custom OpenAI-compatible endpoint."""
    from .providers.custom_openai import CustomOpenAIProvider

    provider = CustomOpenAIProvider()
    return await provider.validate_connection(request.url, request.api_key or "")


@app.get("/api/custom-endpoint/models")
async def get_custom_endpoint_models():
    """Fetch available models from the custom endpoint."""
    from .providers.custom_openai import CustomOpenAIProvider
    from .settings import get_settings

    settings = get_settings()
    if not settings.custom_endpoint_url:
        return {"models": [], "error": "No custom endpoint configured"}

    provider = CustomOpenAIProvider()
    models = await provider.get_models()
    return {"models": models}


@app.get("/api/models")
async def get_openrouter_models():
    """Fetch available models from OpenRouter API."""
    import httpx
    from .config import get_openrouter_api_key

    api_key = get_openrouter_api_key()
    if not api_key:
        return {"models": [], "error": "No OpenRouter API key configured"}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )

            if response.status_code != 200:
                return {"models": [], "error": f"API error: {response.status_code}"}

            data = response.json()
            models = []

            # Comprehensive exclusion list for non-text/chat models
            excluded_terms = [
                "embed",
                "audio",
                "whisper",
                "tts",
                "dall-e",
                "realtime",
                "vision-only",
                "voxtral",
                "speech",
                "transcribe",
                "sora",
            ]

            for model in data.get("data", []):
                mid = model.get("id", "").lower()
                name_lower = model.get("name", "").lower()

                if any(term in mid for term in excluded_terms) or any(
                    term in name_lower for term in excluded_terms
                ):
                    continue

                # Extract pricing - free models have 0 cost
                pricing = model.get("pricing", {})
                prompt_price = float(pricing.get("prompt", "0") or "0")
                completion_price = float(pricing.get("completion", "0") or "0")
                is_free = prompt_price == 0 and completion_price == 0

                models.append(
                    {
                        "id": f"openrouter:{model.get('id')}",
                        "name": f"{model.get('name', model.get('id'))} [OpenRouter]",
                        "provider": "OpenRouter",
                        "context_length": model.get("context_length"),
                        "is_free": is_free,
                    }
                )

            # Sort by name
            models.sort(key=lambda x: x["name"].lower())
            return {"models": models}

    except httpx.TimeoutException:
        return {"models": [], "error": "Request timed out"}
    except Exception as e:
        return {"models": [], "error": str(e)}


@app.post("/api/settings/test-openrouter")
async def test_openrouter_api(request: TestOpenRouterRequest):
    """Test OpenRouter API key with a simple request."""
    import httpx
    from .config import get_openrouter_api_key

    # Use provided key or fall back to saved key
    api_key = request.api_key if request.api_key else get_openrouter_api_key()

    if not api_key:
        return {"success": False, "message": "No API key provided or configured"}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                "https://openrouter.ai/api/v1/models",
                headers={
                    "Authorization": f"Bearer {api_key}",
                },
            )

            if response.status_code == 200:
                return {"success": True, "message": "API key is valid"}
            elif response.status_code == 401:
                return {"success": False, "message": "Invalid API key"}
            else:
                return {
                    "success": False,
                    "message": f"API error: {response.status_code}",
                }

    except httpx.TimeoutException:
        return {"success": False, "message": "Request timed out"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.get("/api/logs/recent")
async def get_recent_logs(limit: int = 50):
    """Get recent error logs for UI display."""
    from .error_logger import get_recent_errors

    return {"errors": get_recent_errors(limit)}


@app.get("/api/logs/files")
async def get_log_files():
    """Get list of log files."""
    from .error_logger import get_log_files

    return {"files": get_log_files()}


@app.get("/api/logs/file/{filename}")
async def read_log_file(filename: str, lines: int = 100):
    """Read contents of a specific log file."""
    from .error_logger import read_log_file

    # Basic security check
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    content = read_log_file(filename, lines)
    return {"content": content}


@app.post("/api/logs/client")
async def log_from_client(log_data: dict):
    """Accept log messages from frontend."""
    from .error_logger import log_event

    level = log_data.get("level", "INFO")
    message = log_data.get("message", "")
    data = log_data.get("data", {})

    await log_event(f"client_{level.lower()}", {"message": message, **data}, level)
    return {"status": "logged"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
