# Next.js Integration Guide

Integrate Plexity workflows into a Next.js application using the JavaScript SDK and React components.

## 1. Install dependencies

```bash
pnpm add @plexity/sdk @plexity/react
```

## 2. Configure environment variables

```
NEXT_PUBLIC_PLEXITY_API=https://api.plexity.ai
PLEXITY_API_KEY=...
```

Expose only non-sensitive values to the browser. Use a server-side token minting endpoint when you need per-user JWTs.

## 3. Create an API route for proxying executions (optional)

```ts
// pages/api/plexity/start.ts
import type { NextApiRequest, NextApiResponse } from "next";
import { PlexityClient } from "@plexity/sdk";

const client = new PlexityClient({
  baseUrl: process.env.NEXT_PUBLIC_PLEXITY_API!,
  apiKey: process.env.PLEXITY_API_KEY,
});

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== "POST") return res.status(405).end();
  const { workflowId, input } = req.body || {};
  const execution = await client.startExecution({ workflowId, input });
  res.status(200).json(execution);
}
```

## 4. Wrap your app with the provider

```tsx
// pages/_app.tsx
import type { AppProps } from "next/app";
import { PlexityProvider } from "@plexity/react";

export default function App({ Component, pageProps }: AppProps) {
  return (
    <PlexityProvider options={{
      baseUrl: process.env.NEXT_PUBLIC_PLEXITY_API!,
      apiKey: process.env.PLEXITY_PUBLIC_KEY,
    }}>
      <Component {...pageProps} />
    </PlexityProvider>
  );
}
```

## 5. Render workflow controls

```tsx
// components/WorkflowCard.tsx
import { useState } from "react";
import { WorkflowLauncher, ExecutionStatusPanel } from "@plexity/react";

export function WorkflowCard() {
  const [executionId, setExecutionId] = useState<string | null>(null);

  return (
    <div className="card">
      <h2>Process Customer Escalation</h2>
      <WorkflowLauncher
        workflowId="customer_escalation"
        input={{ trigger: { body: { ticketId: "T-42" } } }}
        onStarted={(id) => setExecutionId(id)}
      >
        Run Workflow
      </WorkflowLauncher>
      <ExecutionStatusPanel executionId={executionId} style={{ marginTop: 16 }} />
    </div>
  );
}
```

## 6. Secure webhooks

When hosting your own HTTP endpoint for Plexity to invoke, validate signatures using the SDK helpers.

```ts
import type { NextApiRequest, NextApiResponse } from "next";
import { parseIncomingWebhook, verifyWebhookSignature } from "@plexity/sdk";

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const { signature, timestamp, payload } = parseIncomingWebhook({
    headers: req.headers as Record<string, any>,
    body: req.body,
    rawBody: (req as any).rawBody,
  });

  const secret = process.env.PLEXITY_WEBHOOK_SECRET!;
  if (!verifyWebhookSignature({ secret, payload, timestamp, signature })) {
    return res.status(401).json({ error: "invalid_signature" });
  }

  // handle payload...
  res.status(200).json({ ok: true });
}
```

Enable `bodyParser: { sizeLimit: "1mb", verify: (req, res, buf) => (req as any).rawBody = buf }` in the API route config to retain the raw payload for signature validation.

## 7. Deployment checklist

- Store secrets using Next.js runtime config or Vercel project secrets.
- Enable HTTPS for inbound webhooks.
- Rotate API keys through the Plexity Admin portal or the SDK (`createApiKey`).
- Deploy workers or rely on Plexity-managed workers depending on your plan.
