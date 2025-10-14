# Plexity Quickstart (5 Minutes)

The goal of this guide is to get a GraphRAG optimization loop running end-to-end with the unified SDK. You will provision an in-memory GraphRAG instance, evaluate a prompt variant, and synchronize the run back to the platform for tracking.

## 1. Install Dependencies

```bash
pnpm install
pnpm --filter @plexity/graphrag-core build
pnpm --filter @plexity/graphrag-optimization build
```

You only need a valid LLM API key (OpenAI, Anthropic, etc.) exposed via the environment. The quickstart assumes `OPENAI_API_KEY`.

## 2. Generate a Project Skeleton

```bash
cp -R examples/plexity-quickstart ./tmp/plexity-quickstart
cd tmp/plexity-quickstart
pnpm install
```

The folder contains:

- `optimize.yaml` – CLI configuration
- `create-context.mjs` – factory for `GraphRAG` + LLM provider
- `README.md` – walk-through

## 3. Configure Environment Variables

```bash
export OPENAI_API_KEY="sk-..."
export PLEXITY_PLATFORM_API_KEY="development-secret"
export PLEXITY_PLATFORM_ENDPOINT="http://localhost:3000"
```

The platform credentials are optional, but the sync step will noop without them.

## 4. Run Optimization

```bash
pnpm optimize
```

The command executes:

1. Loads the config file.
2. Instantiates `GraphRAG` using memory storage.
3. Evaluates the prompt variant against the selected dataset.
4. Prints metrics and (optionally) uploads the experiment run via telemetry + REST.

## 5. Inspect Results

- CLI output surfaces pass rate, quality, grounding, latency, and cost metrics.
- Synchronized runs show up under `/graphrag/experiments` API endpoints.
- The `tmp/plexity-quickstart/results` directory stores raw JSON if an `output` path is provided in the config.

## Advanced Options

- Update `optimize.yaml` to point at a custom dataset file.
- Toggle streaming token previews with `streaming: true`.
- Wire multiple variants and use `EvaluationHarness.runBatchOptimization` from a custom script to orchestrate large-scale tests.

Happy shipping!
