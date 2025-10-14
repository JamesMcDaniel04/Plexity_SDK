# React Integration Guide

This guide covers integrating Plexity workflows into a vanilla React (Vite) application using the React components and SDK.

## 1. Install

```bash
pnpm create vite my-app --template react-ts
cd my-app
pnpm add @plexity/sdk @plexity/react
```

## 2. Configure environment

Create `.env.local`:

```
VITE_PLEXITY_API=https://api.plexity.ai
VITE_PLEXITY_API_KEY=...
```

## 3. Bootstrap the provider

```tsx
// src/main.tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { PlexityProvider } from "@plexity/react";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <PlexityProvider
      options={{
        baseUrl: import.meta.env.VITE_PLEXITY_API,
        apiKey: import.meta.env.VITE_PLEXITY_API_KEY,
      }}
    >
      <App />
    </PlexityProvider>
  </React.StrictMode>
);
```

## 4. Compose UI

```tsx
// src/App.tsx
import { useState } from "react";
import { WorkflowLauncher, ExecutionStatusPanel } from "@plexity/react";

export default function App() {
  const [executionId, setExecutionId] = useState<string | null>(null);

  return (
    <main style={{ maxWidth: 640, margin: "40px auto", fontFamily: "Inter, sans-serif" }}>
      <h1>Automated Delegation</h1>
      <WorkflowLauncher
        workflowId="team_task_delegation_default"
        input={() => ({ trigger: { body: { goal: "Draft QBR summaries" } } })}
        onStarted={id => setExecutionId(id)}
        className="launch"
      >
        Run delegation workflow
      </WorkflowLauncher>
      <ExecutionStatusPanel executionId={executionId} style={{ marginTop: 24 }} />
    </main>
  );
}
```

## 5. Styling

Add custom CSS or wrap components with your design system. The exporter only sets light inline styles to stay brand-neutral.

## 6. Advanced

- Use `useWorkflows()` to render a dynamic picker.
- Fetch per-user JWTs from your backend and call `client.setToken(jwt)`.
- Handle `WorkflowLauncher` errors by passing an `onError` callback.

## 7. Local testing

Seed the sandbox (`pnpm sandbox:seed`) and point `VITE_PLEXITY_API` to `http://localhost:8080`. The seed script prints an API key and JWT for your local org.
