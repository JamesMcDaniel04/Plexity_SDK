# FastAPI Integration Guide

This guide shows how to plug the Plexity Python SDK into a FastAPI application for both webhook validation and orchestrator calls.

## Installation

```bash
pip install plexity-sdk[async]
```

Add extras such as `langchain`, `llamaindex`, or `haystack` if you plan to use the GraphRAG integrations.

## Application Structure

```python
from fastapi import Depends, FastAPI, HTTPException, Request, status

from plexity_sdk import AsyncPlexityClient, extract_webhook_request, verify_webhook_signature

app = FastAPI()


async def get_client() -> AsyncPlexityClient:
    client = AsyncPlexityClient(
        base_url="https://api.plexity.ai",
        api_key="sqk_your-key",
        max_retries=2,
    )
    try:
        yield client
    finally:
        await client.close()


@app.get("/workflows")
async def list_workflows(client: AsyncPlexityClient = Depends(get_client)):
    return await client.list_workflows()


@app.post("/webhooks/plexity")
async def handle_webhook(request: Request):
    body = await request.body()
    extracted = extract_webhook_request(dict(request.headers), body, raw_body=body)
    if not verify_webhook_signature(
        secret="your-shared-secret",
        payload=extracted["payload"],
        timestamp=extracted["timestamp"],
        signature=extracted["signature"],
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    payload = request.json()
    # TODO: handle webhook payload
    return {"status": "ok"}
```

## GraphRAG Search Endpoint

```python
from plexity_sdk import GraphRAGClient


@app.get("/search")
async def search(query: str, client: AsyncPlexityClient = Depends(get_client)):
    rag = GraphRAGClient(await client.unwrap(), org_id="org_default", environment="prod")
    return await client.run_in_executor(rag.search, query)
```

`AsyncPlexityClient.unwrap()` exposes the underlying synchronous client if you need direct access to helper classes. `run_in_executor` executes synchronous helpers without blocking the main event loop.

## Tips

- Configure the async client with `max_retries` to handle transient network issues gracefully.
- Store shared secrets, API keys, and base URLs in configuration management or environment variables.
- Combine telemetry ingestion (`GraphRAGTelemetry`) with FastAPI background tasks for non-blocking logging.
