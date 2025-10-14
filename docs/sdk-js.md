# Plexity JavaScript SDK

The `@plexity/sdk` package wraps the orchestrator API with friendly TypeScript types and sensible defaults for Node.js and browser runtimes.

## Installation

```bash
pnpm add @plexity/sdk
# or
yarn add @plexity/sdk
# or
npm install @plexity/sdk
```

## Quickstart

```ts
import { PlexityClient } from "@plexity/sdk";

const client = new PlexityClient({
  baseUrl: "https://api.plexity.ai",
  apiKey: process.env.PLEXITY_API_KEY,
});

const executions = await client.listExecutions({ limit: 10 });
console.log(executions);
```

## Authentication

- **API keys** – pass the key via `apiKey`.
- **JWT** – pass the token via `token`. Combine with `apiKey` when you need both.
- **Custom headers** – supply via `defaultHeaders` in the constructor or by calling `setDefaultHeader(name, value)`.

## API Surface

All methods return JSON responses typed with the SDK interfaces.

| Method | Description |
| ------ | ----------- |
| `listWorkflows()` | List published workflow revisions for the authenticated organization. |
| `getWorkflow(id)` | Fetch the latest workflow spec and metadata. |
| `saveWorkflow(spec, opts?)` | Persist a workflow revision; defaults to publishing immediately. |
| `deleteWorkflow(id)` | Remove a workflow and associated triggers. |
| `startExecution({ workflowId, input, kind })` | Kick off a workflow execution. |
| `listExecutions(params?)` | Filter executions by status, time window, or limit. |
| `getExecution(id)` | Fetch execution detail with steps. |
| `listExecutionSteps(id, params?)` | Paginate execution steps. |
| `cancelExecution(id)` | Cancel a running execution and purge queued jobs. |
| `resumeStep({ token, payload })` | Resume a paused step with input payload. |
| `listTriggers()` | Enumerate workflow triggers and webhook endpoints (includes secrets). |
| `listEvents(executionId)` | Fetch the execution event timeline. |

## Webhook Helpers

The SDK ships with utilities for validating webhook requests emitted by Plexity.

```ts
import { parseIncomingWebhook, verifyWebhookSignature } from "@plexity/sdk";

export async function handler(req, res) {
  const { signature, timestamp, payload } = parseIncomingWebhook({
    headers: req.headers,
    body: req.body,
    rawBody: req.rawBody,
  });

  const isValid = verifyWebhookSignature({
    secret: process.env.PLEXITY_WEBHOOK_SECRET!,
    signature,
    timestamp,
    payload,
  });

  if (!isValid) {
    return res.status(401).send("invalid signature");
  }

  // handle payload
}
```

## Error Handling

Requests throw an `HttpError` when the API responds with a non-success status. The error exposes `status` and `body` for debugging.

```ts
try {
  await client.startExecution({ workflowId: "rag_ingest_answer" });
} catch (err) {
  if (err instanceof HttpError && err.status === 404) {
    console.error("Workflow not found");
  }
}
```

## Node & Browser Compatibility

- Node 18+ – uses the built-in `fetch` API. Provide `fetchImpl` when running on older runtimes.
- Browser / Edge functions – pass a custom `fetchImpl` that adapts headers to your environment.

## Examples

See `docs/sandbox.md` for an end-to-end walkthrough that combines the SDK with the sandbox environment.
