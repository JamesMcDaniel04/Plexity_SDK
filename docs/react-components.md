# React Embedding Components

The `@plexity/react` package provides ready-to-use components and hooks for embedding Plexity workflows inside customer-facing applications.

## Installation

```bash
pnpm add @plexity/react @plexity/sdk
```

## Provider Setup

```tsx
import { PlexityProvider } from "@plexity/react";

function App({ children }) {
  return (
    <PlexityProvider
      options={{
        baseUrl: process.env.NEXT_PUBLIC_PLEXITY_API!,
        apiKey: process.env.NEXT_PUBLIC_PLEXITY_KEY,
      }}
    >
      {children}
    </PlexityProvider>
  );
}
```

You can also construct a pre-configured `PlexityClient` and pass it via the `client` prop.

## Launching Workflows

```tsx
import { WorkflowLauncher } from "@plexity/react";

export function LaunchButton() {
  return (
    <WorkflowLauncher
      workflowId="team_task_delegation_default"
      className="btn btn-primary"
      input={() => ({ trigger: { body: { goal: "Draft release notes" } } })}
      onStarted={(id) => console.log("Execution", id)}
    >
      Launch delegation workflow
    </WorkflowLauncher>
  );
}
```

## Status Panels

```tsx
import { ExecutionStatusPanel } from "@plexity/react";

export function ExecutionView({ executionId }: { executionId?: string }) {
  return <ExecutionStatusPanel executionId={executionId} pollIntervalMs={1500} />;
}
```

The panel polls until the execution reaches a terminal status (`succeeded`, `failed`, or `canceled`).

## Hooks

- `usePlexityClient()` – access the underlying SDK client.
- `useExecution(executionId, options)` – fetch + poll an execution; returns `{ execution, loading, error, refresh }`.
- `useWorkflows()` – list workflows for the current org.
- `useExecutionStatus(execution)` – derive `completedSteps` and `totalSteps` counts from an execution payload.

## Styling

Components ship with minimal inline styling to stay brand-agnostic. Override through `className` / `style` props or wrap them with your design system.

## Examples

- `docs/integration-guides/nextjs.md` demonstrates wiring the components into a Next.js route with server-side token minting.
- `docs/integration-guides/react.md` covers a plain Vite + React setup.
