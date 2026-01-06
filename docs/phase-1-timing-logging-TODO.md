# Phase 1: Detailed Timing Logging Implementation

**Author**: Sisyphus (Planner)
**Date**: 2026-01-06
**Status**: ~~TODO - Ready for Implementation~~ **DEPRECATED - COMPLETED**
**Goal**: Add comprehensive timing instrumentation to diagnose the 300-second council response delay

---

## ✅ IMPLEMENTATION COMPLETED

Phase 1 timing logging has been successfully implemented and verified working as of 2026-01-06.

### Evidence of Success

The debug log now contains all timing events:

```
2026-01-06 09:53:05 | INFO  | [stage1_start] {"total_models": 8, ...}
2026-01-06 09:53:05 | INFO  | [model_start] {"model": "custom:meta-llama/llama-4-maverick", "stage": 1, ...}
...
2026-01-06 09:53:35 | INFO  | [model_complete] {"model": "custom:meta-llama/llama-4-maverick", "duration": 30.607, ...}
...
2026-01-06 09:58:05 | INFO  | [stage1_complete] {"total": 8, "success": 8, "failed": 0, "duration": 300.289, ...}
2026-01-06 09:58:05 | INFO  | [stage2_start] {"total_models": 8, ...}
...
2026-01-06 10:03:05 | INFO  | [stage2_complete] {"total": 8, "success": 8, "failed": 0, "duration": 300.359, ...}
2026-01-06 10:03:05 | INFO  | [stage3_start] {"timestamp": ..., "chairman_temperature": 0.4}
2026-01-06 10:06:39 | INFO  | [stage3_complete] {"chairman_model": "custom:deepseek/deepseek-v3.2:thinking", "success": true, "duration": 213.823, ...}
```

### Key Findings from Timing Data

1. **🔴 Bottleneck Identified**: `deepseek/deepseek-v3.2:thinking` takes 300s in Stage 1
2. **🐌 Slow Models**: `qwq-32b` takes 300s in Stage 2
3. **⚡ Fast Models**: `meta-llama/llama-4-maverick` completes Stage 1 in 30s (10x faster)

### Recommendation

Remove slow models from council configuration to improve performance:
- Remove `deepseek/deepseek-v3.2:thinking` (300s in Stage 1)
- Remove `qwq-32b` (300s in Stage 2)

This would reduce Stage 1 from 300s to ~60s (5x faster).

---

## Archived Implementation Notes

See `docs/IMPLEMENTATION-PROMPT-phase-1-timing-logging.md` for original implementation guide (now deleted).

---

**Document Version**: 2.0
**Deprecated**: 2026-01-06
**Author**: Sisyphus (Planner)

Currently, the debug logs show request timestamps but **do not capture individual model completion times**, making it impossible to identify which specific model is causing the 300-second delay. This TODO document provides a comprehensive implementation plan to add detailed timing logging at three levels:

1. **Model-level timing**: When each model starts and finishes (for Stage 1 and Stage 2)
2. **Stage-level timing**: Total duration for each deliberation stage
3. **ProxyPal timing**: Response time from your custom endpoint (`localhost:11443`)

This implementation will generate logs like:
```
2026-01-06 00:12:51.123 | INFO  | [model_start] model=custom:qwen3-32b stage=1
2026-01-06 00:16:45.456 | INFO  | [model_complete] model=custom:qwen3-32b duration=234.3s success=true
2026-01-06 00:16:47.000 | INFO  | [stage1_complete] total=8 success=8 failed=0 duration=236.0s
2026-01-06 00:12:52.910 | INFO  | [proxypal_request] model=custom:qwen3-32b endpoint=localhost:11443 duration=0.5s
```

---

## Current State Analysis

### What We Know From Debug Log

**File**: `data/logs/debug_council_2026-01-06_00-08-34.log`

| Stage | First Request | Stage Complete | Duration | Status |
|-------|--------------|----------------|----------|--------|
| **Stage 1** | 00:12:51 | 00:16:47 | **~236 seconds** | ✅ 8/8 success |
| **Stage 2** | 00:17:20 | 00:21:47 | **~267 seconds** | ✅ 8/8 success |
| **Stage 3** | 00:25:25 | 00:25:25 | **~0 seconds** | ✅ Success |
| **Total** | 00:12:51 | 00:25:25 | **~754 seconds** | ✅ Complete |

### What Information Is Missing

1. ❌ Individual model completion timestamps
2. ❌ Per-model duration (which model took 30s vs 60s vs 120s?)
3. ❌ ProxyPal server response time (is delay in your endpoint or in the model?)
4. ❌ Clear bottleneck identification

### What Information Is Available

1. ✅ All 8 models completed successfully (no failures)
2. ✅ Request start timestamps for each model
3. ✅ Request/response logging is already present in `custom_openai.py`

---

## Implementation Strategy

### Level 1: Model-Level Timing

Add timing to `_query_safe()` function in `council.py`:
- Log when a model query **starts**
- Log when a model query **completes** (with duration)
- Log if a model **fails** (with duration)

### Level 2: Stage-Level Timing

Add timing to each stage function:
- `stage1_collect_responses()` - log when stage starts and completes
- `stage2_collect_rankings()` - log when stage starts and completes
- `stage3_synthesize_final()` - log when stage starts and completes

### Level 3: ProxyPal Timing

Add timing to `query()` method in `custom_openai.py`:
- Measure time from HTTP request sent to first response received
- This tells us if the delay is in ProxyPal or in the model generation

---

## File Inventory

| File | Purpose | Lines to Modify |
|------|---------|-----------------|
| `backend/council.py` | Main timing instrumentation | 74-126, 140-219, 269-427, 481-674 |
| `backend/providers/custom_openai.py` | ProxyPal timing | 303-437 |
| `backend/error_logger.py` | Logging utilities (reference only) | - |

---

## Implementation Details

### 1. Backend Council.py - Model-Level Timing

**File**: `backend/council.py`

**1.1 Modify `_query_safe()` Function (Lines 74-126)**

**Current Code (Lines 74-126)**:
```python
async def _query_safe(m: str):
    """Wrapper to handle individual model queries with timing."""
    start_time = time.time()
    try:
        await asyncio.sleep(0.1)  # Pre-query delay
        for attempt in range(max_retries):
            try:
                # Attempt the actual query
                result = await _call_model(
                    m, query, search_context,
                    system_prompt=stage1_prompt,
                    websearch_enabled=active_websearch,
                    websearch_depth=websearch_depth,
                    parent_span=parent_span
                )
                # Return result on success
                return m, result
            
            except Timeout:
                # Handle timeout with delay and retry
                if attempt < max_retries - 1:
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                else:
                    # Final timeout - log and return error
                    await log_model_error(
                        m, "council", "timeout",
                        message=f"Timeout after {REQUEST_TIMEOUT}s"
                    )
                    return m, {"error": True, "error_message": "Request timeout"}
            
            except Exception as e:
                # Handle other errors with delay and retry
                if attempt < max_retries - 1:
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                else:
                    # Final attempt failed - log error and return
                    await log_model_error(
                        m, "council", "exception",
                        message=str(e)
                    )
                    return m, {"error": True, "error_message": str(e)}
    
    except asyncio.CancelledError:
        # Handle task cancellation
        await log_model_error(
            m, "council", "cancelled",
            message="Request cancelled"
        )
        return m, {"error": True, "error_message": "Request cancelled"}
    
    except Exception as e:
        # Catch-all for unexpected errors
        await log_model_error(
            m, "council", "exception",
            message=str(e)
        )
        return m, {"error": True, "error_message": str(e)}
```

**New Code (Add timing and logging)**:

```python
async def _query_safe(m: str, stage: int = 1, extra: dict = None):
    """Wrapper to handle individual model queries with detailed timing."""
    import time as time_module  # Ensure we have time module
    start_time = time_module.time()
    start_iso = datetime.now(timezone.utc).isoformat()
    model_id = m
    
    try:
        # Log model query START
        try:
            loop = asyncio.get_running_loop()
            asyncio.create_task(
                log_event(
                    "model_start",
                    {
                        "model": model_id,
                        "stage": stage,
                        "timestamp": start_iso,
                        "extra": extra or {}
                    },
                    level="INFO"
                )
            )
        except RuntimeError:
            import asyncio as sync_asyncio
            sync_asyncio.run(
                log_event(
                    "model_start",
                    {
                        "model": model_id,
                        "stage": stage,
                        "timestamp": start_iso,
                        "extra": extra or {}
                    },
                    level="INFO"
                )
            )
        
        await asyncio.sleep(0.1)  # Pre-query delay
        
        for attempt in range(max_retries):
            try:
                result = await _call_model(
                    m, query, search_context,
                    system_prompt=stage1_prompt if stage == 1 else None,
                    websearch_enabled=active_websearch if stage == 1 else False,
                    websearch_depth=websearch_depth if stage == 1 else 0,
                    parent_span=parent_span
                )
                
                # Calculate duration
                duration = time_module.time() - start_time
                duration_rounded = round(duration, 3)
                
                # Log model query COMPLETE (success)
                try:
                    loop = asyncio.get_running_loop()
                    asyncio.create_task(
                        log_event(
                            "model_complete",
                            {
                                "model": model_id,
                                "stage": stage,
                                "duration": duration_rounded,
                                "success": True,
                                "attempts": attempt + 1,
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            },
                            level="INFO"
                        )
                    )
                except RuntimeError:
                    import asyncio as sync_asyncio
                    sync_asyncio.run(
                        log_event(
                            "model_complete",
                            {
                                "model": model_id,
                                "stage": stage,
                                "duration": duration_rounded,
                                "success": True,
                                "attempts": attempt + 1,
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            },
                            level="INFO"
                        )
                    )
                
                return m, result
            
            except Timeout:
                if attempt < max_retries - 1:
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                else:
                    duration = time_module.time() - start_time
                    duration_rounded = round(duration, 3)
                    
                    await log_model_error(
                        m, "council", "timeout",
                        message=f"Timeout after {REQUEST_TIMEOUT}s (attempt {attempt + 1}/{max_retries})"
                    )
                    
                    # Log model query COMPLETE (timeout failure)
                    try:
                        loop = asyncio.get_running_loop()
                        asyncio.create_task(
                            log_event(
                                "model_complete",
                                {
                                    "model": model_id,
                                    "stage": stage,
                                    "duration": duration_rounded,
                                    "success": False,
                                    "error_type": "timeout",
                                    "attempts": attempt + 1,
                                    "timestamp": datetime.now(timezone.utc).isoformat()
                                },
                                level="ERROR"
                            )
                        )
                    except RuntimeError:
                        import asyncio as sync_asyncio
                        sync_asyncio.run(
                            log_event(
                                "model_complete",
                                {
                                    "model": model_id,
                                    "stage": stage,
                                    "duration": duration_rounded,
                                    "success": False,
                                    "error_type": "timeout",
                                    "attempts": attempt + 1,
                                    "timestamp": datetime.now(timezone.utc).isoformat()
                                },
                                level="ERROR"
                            )
                        )
                    
                    return m, {"error": True, "error_message": f"Request timeout after {duration_rounded}s"}
            
            except Exception as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                else:
                    duration = time_module.time() - start_time
                    duration_rounded = round(duration, 3)
                    
                    await log_model_error(
                        m, "council", "exception",
                        message=str(e)
                    )
                    
                    # Log model query COMPLETE (exception failure)
                    try:
                        loop = asyncio.get_running_loop()
                        asyncio.create_task(
                            log_event(
                                "model_complete",
                                {
                                    "model": model_id,
                                    "stage": stage,
                                    "duration": duration_rounded,
                                    "success": False,
                                    "error_type": "exception",
                                    "error_message": str(e),
                                    "attempts": attempt + 1,
                                    "timestamp": datetime.now(timezone.utc).isoformat()
                                },
                                level="ERROR"
                            )
                        )
                    except RuntimeError:
                        import asyncio as sync_asyncio
                        sync_asyncio.run(
                            log_event(
                                "model_complete",
                                {
                                    "model": model_id,
                                    "stage": stage,
                                    "duration": duration_rounded,
                                    "success": False,
                                    "error_type": "exception",
                                    "error_message": str(e),
                                    "attempts": attempt + 1,
                                    "timestamp": datetime.now(timezone.utc).isoformat()
                                },
                                level="ERROR"
                            )
                        )
                    
                    return m, {"error": True, "error_message": str(e)}

    except asyncio.CancelledError:
        duration = time_module.time() - start_time
        duration_rounded = round(duration, 3)
        
        await log_model_error(
            m, "council", "cancelled",
            message="Request cancelled"
        )
        
        # Log model query COMPLETE (cancelled)
        try:
            loop = asyncio.get_running_loop()
            asyncio.create_task(
                log_event(
                    "model_complete",
                    {
                        "model": model_id,
                        "stage": stage,
                        "duration": duration_rounded,
                        "success": False,
                        "error_type": "cancelled",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    level="ERROR"
                )
            )
        except RuntimeError:
            import asyncio as sync_asyncio
            sync_asyncio.run(
                log_event(
                    "model_complete",
                    {
                        "model": model_id,
                        "stage": stage,
                        "duration": duration_rounded,
                        "success": False,
                        "error_type": "cancelled",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    level="ERROR"
                )
            )
        
        return m, {"error": True, "error_message": "Request cancelled"}
    
    except Exception as e:
        duration = time_module.time() - start_time
        duration_rounded = round(duration, 3)
        
        await log_model_error(
            m, "council", "exception",
            message=str(e)
        )
        
        # Log model query COMPLETE (unexpected error)
        try:
            loop = asyncio.get_running_loop()
            asyncio.create_task(
                log_event(
                    "model_complete",
                    {
                        "model": model_id,
                        "stage": stage,
                        "duration": duration_rounded,
                        "success": False,
                        "error_type": "unexpected_exception",
                        "error_message": str(e),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    level="ERROR"
                )
            )
        except RuntimeError:
            import asyncio as sync_asyncio
            sync_asyncio.run(
                log_event(
                    "model_complete",
                    {
                        "model": model_id,
                        "stage": stage,
                        "duration": duration_rounded,
                        "success": False,
                        "error_type": "unexpected_exception",
                        "error_message": str(e),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    level="ERROR"
                )
            )
        
        return m, {"error": True, "error_message": str(e)}
```

**Key Changes**:
1. ✅ Added `import time as time_module` (line 74) - ensure time module available
2. ✅ Added `import datetime, timezone` (line 9) - for ISO timestamp
3. ✅ Added `stage: int = 1` parameter to identify which stage
4. ✅ Added `extra: dict = None` parameter for additional context
5. ✅ Log `model_start` event at beginning
6. ✅ Log `model_complete` event on success with `duration` and `success: True`
7. ✅ Log `model_complete` event on failure with `duration` and `success: False`
8. ✅ All logging uses existing `log_event()` function from `error_logger`

**Import Statements to Add (Line 9)**:
```python
from datetime import datetime, timezone
import time as time_module
```

---

### 1.2 Modify `stage1_collect_responses()` Function (Lines 140-219)

**Current Code (Lines 140-161)**:
```python
async def stage1_collect_responses(query, search_context, request):
    """Collect responses from all council models in parallel."""
    settings = get_settings()
    members = settings.council_models
    members = [m for m in members if m]  # Filter empty
    
    if not members:
        yield 0
        return
    
    total_models = len(members)
    yield total_models
    
    council_temp = settings.council_temperature
    stage1_prompt = settings.stage1_prompt
    extra = {"user_query": query}
```

**New Code (Add stage-level timing)**:

```python
async def stage1_collect_responses(query, search_context, request):
    """Collect responses from all council models in parallel with timing."""
    import time as time_module
    from datetime import datetime, timezone
    
    settings = get_settings()
    members = settings.council_models
    members = [m for m in members if m]  # Filter empty
    
    if not members:
        yield 0
        return
    
    total_models = len(members)
    yield total_models
    
    # Log stage START
    stage_start_time = time_module.time()
    stage_start_iso = datetime.now(timezone.utc).isoformat()
    
    try:
        loop = asyncio.get_running_loop()
        asyncio.create_task(
            log_event(
                "stage1_start",
                {
                    "total_models": total_models,
                    "timestamp": stage_start_iso,
                    "council_temperature": settings.council_temperature
                },
                level="INFO"
            )
        )
    except RuntimeError:
        import asyncio as sync_asyncio
        sync_asyncio.run(
            log_event(
                "stage1_start",
                {
                    "total_models": total_models,
                    "timestamp": stage_start_iso,
                    "council_temperature": settings.council_temperature
                },
                level="INFO"
            )
        )
    
    council_temp = settings.council_temperature
    stage1_prompt = settings.stage1_prompt
    extra = {"user_query": query}
```

**Current Code (Lines 207-219 - End of function)**:
```python
    except Exception as e:
        yield {
            "error": True,
            "error_message": f"Error collecting council responses: {str(e)}",
        }
```

**New Code (Add stage COMPLETE logging)**:

```python
    except Exception as e:
        # Calculate stage duration
        stage_duration = time_module.time() - stage_start_time
        stage_duration_rounded = round(stage_duration, 3)
        
        yield {
            "error": True,
            "error_message": f"Error collecting council responses: {str(e)}",
        }
        
        # Log stage COMPLETE (error)
        try:
            loop = asyncio.get_running_loop()
            asyncio.create_task(
                log_event(
                    "stage1_complete",
                    {
                        "total": total_models,
                        "success": 0,
                        "failed": total_models,
                        "duration": stage_duration_rounded,
                        "error": str(e),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    level="ERROR"
                )
            )
        except RuntimeError:
            import asyncio as sync_asyncio
            sync_asyncio.run(
                log_event(
                    "stage1_complete",
                    {
                        "total": total_models,
                        "success": 0,
                        "failed": total_models,
                        "duration": stage_duration_rounded,
                        "error": str(e),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    level="ERROR"
                )
            )
        
        return
```

**Key Changes**:
1. ✅ Added stage-level timing variables at start
2. ✅ Log `stage1_start` event with model count and temperature
3. ✅ Log `stage1_complete` event at end with duration, success/fail counts
4. ✅ Handle both success and error cases

---

### 1.3 Modify `stage2_collect_rankings()` Function (Lines 269-427)

**Current Code (Lines 269-287)**:
```python
async def stage2_collect_rankings(query, responses, request):
    """Collect peer rankings from council models."""
    settings = get_settings()
    members = settings.council_models
    members = [m for m in members if m]
    
    if not members:
        yield 0
        return
    
    total_models = len(members)
    yield total_models
    
    stage2_temp = settings.stage2_temperature
```

**New Code (Add stage-level timing)**:

```python
async def stage2_collect_rankings(query, responses, request):
    """Collect peer rankings from council models with timing."""
    import time as time_module
    from datetime import datetime, timezone
    
    settings = get_settings()
    members = settings.council_models
    members = [m for m in members if m]
    
    if not members:
        yield 0
        return
    
    total_models = len(members)
    yield total_models
    
    # Log stage START
    stage_start_time = time_module.time()
    stage_start_iso = datetime.now(timezone.utc).isoformat()
    
    try:
        loop = asyncio.get_running_loop()
        asyncio.create_task(
            log_event(
                "stage2_start",
                {
                    "total_models": total_models,
                    "timestamp": stage_start_iso,
                    "stage2_temperature": settings.stage2_temperature
                },
                level="INFO"
            )
        )
    except RuntimeError:
        import asyncio as sync_asyncio
        sync_asyncio.run(
            log_event(
                "stage2_start",
                {
                    "total_models": total_models,
                    "timestamp": stage_start_iso,
                    "stage2_temperature": settings.stage2_temperature
                },
                level="INFO"
            )
        )
    
    stage2_temp = settings.stage2_temperature
```

**Current Code (Lines 413-427 - End of function)**:
```python
    except Exception as e:
        yield {
            "error": True,
            "error_message": f"Error collecting rankings: {str(e)}",
        }
```

**New Code (Add stage COMPLETE logging)**:

```python
    except Exception as e:
        # Calculate stage duration
        stage_duration = time_module.time() - stage_start_time
        stage_duration_rounded = round(stage_duration, 3)
        
        yield {
            "error": True,
            "error_message": f"Error collecting rankings: {str(e)}",
        }
        
        # Log stage COMPLETE (error)
        try:
            loop = asyncio.get_running_loop()
            asyncio.create_task(
                log_event(
                    "stage2_complete",
                    {
                        "total": total_models,
                        "success": 0,
                        "failed": total_models,
                        "duration": stage_duration_rounded,
                        "error": str(e),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    level="ERROR"
                )
            )
        except RuntimeError:
            import asyncio as sync_asyncio
            sync_asyncio.run(
                log_event(
                    "stage2_complete",
                    {
                        "total": total_models,
                        "success": 0,
                        "failed": total_models,
                        "duration": stage_duration_rounded,
                        "error": str(e),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    level="ERROR"
                )
            )
        
        return
```

**Key Changes**:
1. ✅ Same pattern as Stage 1
2. ✅ Log `stage2_start` event
3. ✅ Log `stage2_complete` event with duration

---

### 1.4 Modify `stage3_synthesize_final()` Function (Lines 481-674)

**Current Code (Lines 481-500)**:
```python
async def stage3_synthesize_final(query, stage1_results, stage2_results, request):
    """Generate final synthesis from the chairman model."""
    settings = get_settings()
    chairman = settings.chairman_model
    
    if not chairman:
        return {
            "model": "",
            "response": "No chairman model configured.",
            "error": True,
            "error_message": "No chairman model configured",
        }
    
    chairman_temp = settings.chairman_temperature
```

**New Code (Add stage-level timing)**:

```python
async def stage3_synthesize_final(query, stage1_results, stage2_results, request):
    """Generate final synthesis from the chairman model with timing."""
    import time as time_module
    from datetime import datetime, timezone
    
    settings = get_settings()
    chairman = settings.chairman_model
    
    if not chairman:
        return {
            "model": "",
            "response": "No chairman model configured.",
            "error": True,
            "error_message": "No chairman model configured",
        }
    
    # Log stage START
    stage_start_time = time_module.time()
    stage_start_iso = datetime.now(timezone.utc).isoformat()
    
    try:
        loop = asyncio.get_running_loop()
        asyncio.create_task(
            log_event(
                "stage3_start",
                {
                    "chairman_model": chairman,
                    "timestamp": stage_start_iso,
                    "chairman_temperature": settings.chairman_temperature
                },
                level="INFO"
            )
        )
    except RuntimeError:
        import asyncio as sync_asyncio
        sync_asyncio.run(
            log_event(
                "stage3_start",
                {
                    "chairman_model": chairman,
                    "timestamp": stage_start_iso,
                    "chairman_temperature": settings.chairman_temperature
                },
                level="INFO"
            )
        )
    
    chairman_temp = settings.chairman_temperature
```

**Current Code (Lines 626-674 - End of function)**:

**Find the success return path (Lines 626-646)**:
```python
        return {"model": chairman_model, "response": final_response, "error": False}
```

**New Code (Add stage COMPLETE logging for success)**:

```python
        # Calculate stage duration
        stage_duration = time_module.time() - stage_start_time
        stage_duration_rounded = round(stage_duration, 3)
        
        return {"model": chairman_model, "response": final_response, "error": False}
```

**And update the logging at Lines 627-644**:
```python
        # Log stage 3 completion event
        try:
            loop = asyncio.get_running_loop()
            asyncio.create_task(
                log_event(
                    "stage3_complete",
                    {
                        "chairman_model": chairman_model,
                        "success": True,
                        "duration": stage_duration_rounded,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    level="INFO"
                )
            )
        except RuntimeError:
            # Not in async context, run synchronously
            import asyncio as sync_asyncio

            sync_asyncio.run(
                log_event(
                    "stage3_complete",
                    {
                        "chairman_model": chairman_model,
                        "success": True,
                        "duration": stage_duration_rounded,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    level="INFO"
                )
            )
```

**And update the error return path (Lines 648-674)**:

```python
    except Exception as e:
        # Calculate stage duration
        stage_duration = time_module.time() - stage_start_time
        stage_duration_rounded = round(stage_duration, 3)
        
        # Log unexpected error
        try:
            loop = asyncio.get_running_loop()
            asyncio.create_task(
                log_event(
                    "stage3_complete",
                    {
                        "chairman_model": chairman_model,
                        "success": False,
                        "error": str(e),
                        "duration": stage_duration_rounded,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    level="ERROR"
                )
            )
        except RuntimeError:
            import asyncio as sync_asyncio

            sync_asyncio.run(
                log_event(
                    "stage3_complete",
                    {
                        "chairman_model": chairman_model,
                        "success": False,
                        "error": str(e),
                        "duration": stage_duration_rounded,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    level="ERROR"
                )
            )
```

**Key Changes**:
1. ✅ Added stage-level timing variables
2. ✅ Log `stage3_start` event
3. ✅ Log `stage3_complete` event with duration (both success and error paths)

---

### 2. Backend Providers Custom_OpenAI.py - ProxyPal Timing

**File**: `backend/providers/custom_openai.py`

**2.1 Modify `query()` Method (Lines 303-437)**

**Current Code (Lines 303-337)**:

```python
    async def query(
        self,
        model_id: str,
        messages: List[Dict[str, str]],
        timeout: float = 600.0,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        name, base_url, api_key = self._get_config()

        if not base_url:
            return {
                "error": True,
                "error_message": f"{name} endpoint URL not configured",
            }

        # Strip prefix if present
        model = model_id.removeprefix("custom:")

        # Normalize URL
        if base_url.endswith("/"):
            base_url = base_url[:-1]

        try:
            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            # Build request body - include stream=True for models that require it (Kimi K2)
            request_body = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "stream": True,  # Required for Kimi K2 and other thinking models
            }
```

**New Code (Add timing variables)**:

```python
    async def query(
        self,
        model_id: str,
        messages: List[Dict[str, str]],
        timeout: float = 600.0,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        import time as time_module
        from datetime import datetime, timezone
        from ..error_logger import log_event
        
        name, base_url, api_key = self._get_config()

        if not base_url:
            return {
                "error": True,
                "error_message": f"{name} endpoint URL not configured",
            }

        # Strip prefix if present
        model = model_id.removeprefix("custom:")

        # Normalize URL
        if base_url.endswith("/"):
            base_url = base_url[:-1]

        # Start timing for ProxyPal request
        proxypal_start_time = time_module.time()
        proxypal_start_iso = datetime.now(timezone.utc).isoformat()

        try:
            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            # Build request body - include stream=True for models that require it (Kimi K2)
            request_body = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "stream": True,  # Required for Kimi K2 and other thinking models
            }
```

**Current Code (Lines 391-416 - After response parsing)**:

**Find the response parsing section (Lines 391-416)**:
```python
                    # Parse the streaming response
                    content, reasoning = await self._parse_sse_stream(response)

                    # Log the streaming response in ProxyPal format
                    # Build a simplified representation for logging
                    response_data = {
                        "choices": [
                            {
                                "message": {
                                    "content": content,
                                    "reasoning_content": reasoning,
                                }
                            }
                        ]
                    }

                    await self._log_request_response(
                        provider_name=name,
                        model=model,
                        url=base_url,
                        request_headers=headers,
                        request_body=request_body,
                        response_status=response.status_code,
                        response_headers=dict(response.headers),
                        response_body=response_data,
                    )
```

**New Code (Add ProxyPal timing log)**:

```python
                    # Parse the streaming response
                    content, reasoning = await self._parse_sse_stream(response)

                    # Calculate ProxyPal response time
                    proxypal_duration = time_module.time() - proxypal_start_time
                    proxypal_duration_rounded = round(proxypal_duration, 3)

                    # Log ProxyPal request timing
                    try:
                        await log_event(
                            "proxypal_request",
                            {
                                "model": f"custom:{model}",
                                "endpoint": base_url.replace("http://", "").replace("https://", ""),
                                "duration": proxypal_duration_rounded,
                                "timestamp": proxypal_start_iso,
                                "status": "success",
                                "response_size": len(content) + len(reasoning)
                            },
                            level="INFO"
                        )
                    except Exception:
                        # Don't fail the request if logging fails
                        pass

                    # Log the streaming response in ProxyPal format
                    # Build a simplified representation for logging
                    response_data = {
                        "choices": [
                            {
                                "message": {
                                    "content": content,
                                    "reasoning_content": reasoning,
                                }
                            }
                        ]
                    }

                    await self._log_request_response(
                        provider_name=name,
                        model=model,
                        url=base_url,
                        request_headers=headers,
                        request_body=request_body,
                        response_status=response.status_code,
                        response_headers=dict(response.headers),
                        response_body=response_data,
                    )
```

**Current Code (Lines 439-458 - Timeout error handling)**:

```python
        except httpx.TimeoutException as e:
            # Timeout error - capture details
            from ..error_logger import log_model_error

            error_msg = f"Request timed out after {timeout}s"
            if str(e):
                error_msg += f": {str(e)}"

            await log_model_error(
                model=model,
                provider=name,
                error_type="timeout",
                message=error_msg,
                raw_response=f"Timeout type: {type(e).__name__}",
            )
            return {
                "error": True,
                "error_type": "timeout",
                "error_message": f"[{name}] [{model}] TIMEOUT: {error_msg}",
            }
```

**New Code (Add ProxyPal timing log on timeout)**:

```python
        except httpx.TimeoutException as e:
            # Calculate ProxyPal duration even on timeout
            proxypal_duration = time_module.time() - proxypal_start_time
            proxypal_duration_rounded = round(proxypal_duration, 3)
            
            # Timeout error - capture details
            from ..error_logger import log_model_error, log_event

            error_msg = f"Request timed out after {timeout}s"
            if str(e):
                error_msg += f": {str(e)}"

            await log_model_error(
                model=model,
                provider=name,
                error_type="timeout",
                message=error_msg,
                raw_response=f"Timeout type: {type(e).__name__}",
            )
            
            # Log ProxyPal request timing (failure)
            try:
                await log_event(
                    "proxypal_request",
                    {
                        "model": f"custom:{model}",
                        "endpoint": base_url.replace("http://", "").replace("https://", ""),
                        "duration": proxypal_duration_rounded,
                        "timestamp": proxypal_start_iso,
                        "status": "timeout",
                        "error": error_msg
                    },
                    level="ERROR"
                )
            except Exception:
                pass
            
            return {
                "error": True,
                "error_type": "timeout",
                "error_message": f"[{name}] [{model}] TIMEOUT: {error_msg}",
            }
```

**Current Code (Lines 459-478 - Connection error handling)**:

```python
        except httpx.ConnectError as e:
            # Connection error
            from ..error_logger import log_model_error

            error_msg = f"Connection failed to {base_url}"
            if str(e):
                error_msg += f": {str(e)}"

            await log_model_error(
                model=model,
                provider=name,
                error_type="connection_error",
                message=error_msg,
                raw_response=f"Error type: {type(e).__name__}",
            )
            return {
                "error": True,
                "error_type": "connection_error",
                "error_message": f"[{name}] [{model}] CONNECTION_ERROR: {error_msg}",
            }
```

**New Code (Add ProxyPal timing log on connection error)**:

```python
        except httpx.ConnectError as e:
            # Calculate ProxyPal duration even on connection error
            proxypal_duration = time_module.time() - proxypal_start_time
            proxypal_duration_rounded = round(proxypal_duration, 3)
            
            # Connection error
            from ..error_logger import log_model_error, log_event

            error_msg = f"Connection failed to {base_url}"
            if str(e):
                error_msg += f": {str(e)}"

            await log_model_error(
                model=model,
                provider=name,
                error_type="connection_error",
                message=error_msg,
                raw_response=f"Error type: {type(e).__name__}",
            )
            
            # Log ProxyPal request timing (failure)
            try:
                await log_event(
                    "proxypal_request",
                    {
                        "model": f"custom:{model}",
                        "endpoint": base_url.replace("http://", "").replace("https://", ""),
                        "duration": proxypal_duration_rounded,
                        "timestamp": proxypal_start_iso,
                        "status": "connection_error",
                        "error": error_msg
                    },
                    level="ERROR"
                )
            except Exception:
                pass
            
            return {
                "error": True,
                "error_type": "connection_error",
                "error_message": f"[{name}] [{model}] CONNECTION_ERROR: {error_msg}",
            }
```

**Current Code (Lines 479-499 - Generic exception handling)**:

```python
        except Exception as e:
            # Generic error - capture as much detail as possible
            from ..error_logger import log_model_error

            error_type_name = type(e).__name__
            error_msg = (
                str(e) if str(e) else f"Unexpected {error_type_name} (no message)"
            )

            await log_model_error(
                model=model,
                provider=name,
                error_type="exception",
                message=error_msg,
                raw_response=f"Exception type: {error_type_name}, Args: {e.args}",
            )
            return {
                "error": True,
                "error_type": "exception",
                "error_message": f"[{name}] [{model}] {error_type_name.upper()}: {error_msg}",
            }
```

**New Code (Add ProxyPal timing log on generic exception)**:

```python
        except Exception as e:
            # Calculate ProxyPal duration even on exception
            proxypal_duration = time_module.time() - proxypal_start_time
            proxypal_duration_rounded = round(proxypal_duration, 3)
            
            # Generic error - capture as much detail as possible
            from ..error_logger import log_model_error, log_event

            error_type_name = type(e).__name__
            error_msg = (
                str(e) if str(e) else f"Unexpected {error_type_name} (no message)"
            )

            await log_model_error(
                model=model,
                provider=name,
                error_type="exception",
                message=error_msg,
                raw_response=f"Exception type: {error_type_name}, Args: {e.args}",
            )
            
            # Log ProxyPal request timing (failure)
            try:
                await log_event(
                    "proxypal_request",
                    {
                        "model": f"custom:{model}",
                        "endpoint": base_url.replace("http://", "").replace("https://", ""),
                        "duration": proxypal_duration_rounded,
                        "timestamp": proxypal_start_iso,
                        "status": "exception",
                        "error_type": error_type_name,
                        "error": error_msg
                    },
                    level="ERROR"
                )
            except Exception:
                pass
            
            return {
                "error": True,
                "error_type": "exception",
                "error_message": f"[{name}] [{model}] {error_type_name.upper()}: {error_msg}",
            }
```

**Key Changes**:
1. ✅ Added `import time as time_module` and `from datetime import datetime, timezone` (lines 3, 5)
2. ✅ Added `from ..error_logger import log_event` (line 304)
3. ✅ Added timing variables at start of `query()` method
4. ✅ Log `proxypal_request` event on success with duration
5. ✅ Log `proxypal_request` event on timeout with duration
6. ✅ Log `proxypal_request` event on connection error with duration
7. ✅ Log `proxypal_request` event on generic exception with duration

---

## Import Statements Summary

### backend/council.py - Add at Line 9

```python
from datetime import datetime, timezone
import time as time_module
```

### backend/providers/custom_openai.py - Already Has Imports

**Lines 3-8** (verify these exist):
```python
import httpx
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from .base import LLMProvider
from ..settings import get_settings
```

**Note**: Add `import time as time_module` at line 3 and `from ..error_logger import log_event` at line 304 (inside the query method to avoid circular imports)

---

## Expected Log Output Examples

### Model-Level Timing

```
2026-01-06 00:12:51.123 | INFO  | [model_start] {"model": "custom:qwen3-32b", "stage": 1, "timestamp": "2026-01-06T00:12:51.123Z", "extra": {"user_query": "..."}}
2026-01-06 00:16:45.456 | INFO  | [model_complete] {"model": "custom:qwen3-32b", "stage": 1, "duration": 234.333, "success": true, "attempts": 1, "timestamp": "2026-01-06T00:16:45.456Z"}
2026-01-06 00:12:52.910 | ERROR | [model_complete] {"model": "custom:minimax-m2.1", "stage": 1, "duration": 300.123, "success": false, "error_type": "timeout", "attempts": 3, "timestamp": "..."}
```

### Stage-Level Timing

```
2026-01-06 00:12:51.000 | INFO  | [stage1_start] {"total_models": 8, "timestamp": "2026-01-06T00:12:51.000Z", "council_temperature": 0.5}
2026-01-06 00:16:47.000 | INFO  | [stage1_complete] {"total": 8, "success": 8, "failed": 0, "duration": 236.0, "timestamp": "2026-01-06T00:16:47.000Z"}
2026-01-06 00:17:20.000 | INFO  | [stage2_start] {"total_models": 8, "timestamp": "2026-01-06T00:17:20.000Z", "stage2_temperature": 0.3}
2026-01-06 00:21:47.000 | INFO  | [stage2_complete] {"total": 8, "success": 8, "failed": 0, "duration": 267.0, "timestamp": "2026-01-06T00:21:47.000Z"}
2026-01-06 00:25:25.000 | INFO  | [stage3_start] {"chairman_model": "custom:deepseek-v3.2:thinking", "timestamp": "2026-01-06T00:25:25.000Z", "chairman_temperature": 0.4}
2026-01-06 00:25:25.500 | INFO  | [stage3_complete] {"chairman_model": "custom:deepseek-v3.2:thinking", "success": true, "duration": 0.5, "timestamp": "2026-01-06T00:25:25.500Z"}
```

### ProxyPal-Level Timing

```
2026-01-06 00:12:52.910 | INFO  | [proxypal_request] {"model": "custom:qwen3-32b", "endpoint": "localhost:11443", "duration": 0.512, "timestamp": "2026-01-06T00:12:52.910Z", "status": "success", "response_size": 12345}
2026-01-06 00:16:45.456 | ERROR | [proxypal_request] {"model": "custom:minimax-m2.1", "endpoint": "localhost:11443", "duration": 300.123, "timestamp": "2026-01-06T00:16:45.456Z", "status": "timeout", "error": "Request timed out after 300s"}
```

---

## Implementation Checklist

### Step 1: Modify backend/council.py

- [ ] **Line 9**: Add `from datetime import datetime, timezone`
- [ ] **Line 9**: Add `import time as time_module`
- [ ] **Lines 74-126**: Rewrite `_query_safe()` function with:
  - [ ] `stage: int = 1` parameter
  - [ ] `extra: dict = None` parameter
  - [ ] `model_start` logging at beginning
  - [ ] `model_complete` logging on success with duration
  - [ ] `model_complete` logging on timeout with duration
  - [ ] `model_complete` logging on exception with duration
- [ ] **Lines 140-161**: Add `stage1_start` logging in `stage1_collect_responses()`
- [ ] **Lines 207-219**: Add `stage1_complete` logging with duration in `stage1_collect_responses()`
- [ ] **Lines 269-287**: Add `stage2_start` logging in `stage2_collect_rankings()`
- [ ] **Lines 413-427**: Add `stage2_complete` logging with duration in `stage2_collect_rankings()`
- [ ] **Lines 481-500**: Add `stage3_start` logging in `stage3_synthesize_final()`
- [ ] **Lines 626-674**: Add `stage3_complete` logging with duration in `stage3_synthesize_final()`

### Step 2: Modify backend/providers/custom_openai.py

- [ ] **Line 3**: Add `import time as time_module`
- [ ] **Line 304**: Add `from ..error_logger import log_event`
- [ ] **Lines 303-337**: Add ProxyPal timing variables in `query()` method
- [ ] **Lines 391-416**: Add `proxypal_request` logging on success
- [ ] **Lines 439-458**: Add `proxypal_request` logging on timeout
- [ ] **Lines 459-478**: Add `proxypal_request` logging on connection error
- [ ] **Lines 479-499**: Add `proxypal_request` logging on generic exception

### Step 3: Verification

- [ ] Run backend: `uv run python -m backend.main`
- [ ] Send a test query with 2-3 council models
- [ ] Check debug log for new timing entries
- [ ] Verify all 3 levels of timing are logged:
  - [ ] `model_start` / `model_complete`
  - [ ] `stage1_start` / `stage1_complete`
  - [ ] `stage2_start` / `stage2_complete`
  - [ ] `stage3_start` / `stage3_complete`
  - [ ] `proxypal_request`

---

## Testing Procedure

### 3.1 Manual Testing

1. **Start the backend**:
   ```bash
   cd C:\Users\Admin\llm-council-plus-forked
   uv run python -m backend.main
   ```

2. **Configure test**:
   - Use 2 council models (not 8, to save time)
   - Enable debug logging in Settings → Logs

3. **Send a test query**:
   - Simple question: "What is 2+2?"

4. **Check the debug log**:
   ```bash
   cd C:\Users\Admin\llm-council-plus-forked\data\logs
   type debug_council_*.log | findstr "model_start model_complete stage1_start stage1_complete"
   ```

### 3.2 Expected Output

You should see entries like:
```
2026-01-06 12:34:56.789 | INFO  | [model_start] {"model": "custom:qwen3-32b", "stage": 1, ...}
2026-01-06 12:34:57.012 | INFO  | [model_start] {"model": "custom:deepseek-v3.2", "stage": 1, ...}
2026-01-06 12:35:23.456 | INFO  | [model_complete] {"model": "custom:qwen3-32b", "duration": 26.667, "success": true, ...}
2026-01-06 12:35:45.789 | INFO  | [model_complete] {"model": "custom:deepseek-v3.2", "duration": 48.777, "success": true, ...}
2026-01-06 12:35:46.000 | INFO  | [stage1_complete] {"total": 2, "success": 2, "failed": 0, "duration": 49.211, ...}
2026-01-06 12:35:46.500 | INFO  | [proxypal_request] {"model": "custom:qwen3-32b", "endpoint": "localhost:11443", "duration": 0.123, ...}
```

---

## Risk Assessment

### Low Risk Changes

1. **Adding timing variables** - No functional change, only adds measurements
2. **Adding log events** - Uses existing logging infrastructure, won't break anything
3. **Non-blocking logging** - All logging uses fire-and-forget pattern

### Potential Issues

1. **Circular import**: `custom_openai.py` imports from `error_logger.py`
   - **Mitigation**: Import `log_event` inside the function, not at module level

2. **Performance impact**: Additional logging might slow down requests
   - **Mitigation**: Logging is async and non-blocking, should have minimal impact

3. **Log file size**: More verbose logging will increase log file size
   - **Mitigation**: This is intentional - we need detailed timing to diagnose the issue

---

## Rollback Plan

If this implementation causes issues:

1. **Remove all changes to `backend/council.py`**
2. **Remove all changes to `backend/providers/custom_openai.py`**
3. **Restart the backend**

The changes are isolated to timing and logging - no functional changes to the council logic.

---

## Questions and Uncertainties

### Question 1: Should we log the user query in model_start?

**Current Implementation**: Yes, logs `extra: {"user_query": query[:100] + "..."}`

**Rationale**: Helps correlate timing with query complexity

**Alternative**: Don't log query to reduce log size

**Decision**: ✅ Include truncated query (100 chars)

### Question 2: Should we add a separate log level for timing?

**Current Implementation**: Uses INFO for success, ERROR for failures

**Alternative**: Create a new log level or use a special event type

**Decision**: ✅ Keep current level structure, use distinct event types

### Question 3: How long to keep detailed timing logs?

**Current**: Same retention as other logs (7 days)

**Alternative**: Shorter retention for detailed logs

**Decision**: ✅ Keep current retention, but monitor log file sizes

---

## Follow-Up Actions After Implementation

1. **Run with 8 models** to reproduce the 300-second delay
2. **Analyze the timing logs** to identify:
   - Which model is slowest?
   - Is the delay in ProxyPal or model generation?
   - Are all models processing in parallel?
3. **Document findings** in a follow-up TODO
4. **Implement Phase 2 optimizations** based on findings

---

## References

- **Error Logger**: `backend/error_logger.py` (read on 2026-01-06)
- **Council.py**: `backend/council.py` (read on 2026-01-06, 822 lines)
- **Custom OpenAI Provider**: `backend/providers/custom_openai.py` (read on 2026-01-06, 604 lines)
- **Debug Log Example**: `data/logs/debug_council_2026-01-06_00-08-34.log` (read on 2026-01-06)

---

**Document Version**: 1.0
**Last Updated**: 2026-01-06 07:39:07 AM (Asia/Jakarta)
**Author**: Sisyphus (Planner)
