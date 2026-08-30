# vLLM Setup (Sidequest)

How to run the LLM endpoint for the Project Offer Assistant with vLLM on a
GPU machine. The app and the notebooks only need an **OpenAI-compatible API**
— vLLM provides one out of the box.

## What you need

| Requirement | Notes |
|---|---|
| GPU machine | NVIDIA GPU with enough VRAM for the model (27B → ~60 GB for FP16, less with quantization / tensor parallelism) |
| CUDA + drivers | matching the vLLM build |
| vLLM | `pip install vllm` (or the Docker image `vllm/vllm-openai`) |
| Model weights | e.g. a Qwen 27B checkpoint (Hugging Face) |

## Starting the server

```bash
vllm serve <model-name-or-path> \
    --host 0.0.0.0 \
    --port 8000 \
    --served-model-name qwen3.8:27b \
    --max-model-len 8192
```

The server exposes the OpenAI API under `/v1`:

```
GET  /v1/models
POST /v1/chat/completions
```

## Wiring it into this repository

1. `.env` (local, git-ignored):

   ```bash
   LLM_BASE_URL=http://<gpu-host>:8000/v1
   LLM_MODEL=qwen3.8:27b
   ```

2. API key (if the server is behind auth) goes into the **secrets file**
   outside the workspace — never into `.env` or the repo:

   ```bash
   mkdir -p ~/.config/rag-quote-history
   printf 'LLM_API_KEY=your-key\n' > ~/.config/rag-quote-history/secrets.env
   chmod 600 ~/.config/rag-quote-history/secrets.env
   ```

   The app (`app/src/rag_system/config.py`) and the notebook setup cells load
   it with highest priority.

## Model-specific quirks

### Thinking mode (Qwen3)

Qwen3 models have a "thinking" mode that is **on by default** and wastes
tokens on internal reasoning. For RAG answer generation you want it off.
The app already sends this via the OpenAI client's `extra_body`:

```python
client.chat.completions.create(
    model="qwen3.8:27b",
    messages=[...],
    extra_body={"chat_template_kwargs": {"enable_thinking": False}},
)
```

If you add a new Qwen3 model, keep this flag.

### System message position

The system message must be the **first** message in the list — some
chat templates misbehave otherwise. `app/src/rag_system/llm.py` already
orders the messages correctly.

## Health check

```bash
curl -s http://<gpu-host>:8000/v1/models
```

A minimal chat completion test:

```bash
curl -s http://<gpu-host>:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "qwen3.8:27b", "messages": [{"role": "user", "content": "ping"}], "max_tokens": 8}'
```

## Alternative: Ollama (no GPU)

For local development without a GPU machine, Ollama serves the same
OpenAI-compatible API:

```bash
ollama serve                      # default: http://localhost:11434
ollama pull qwen3.5:0.8b
ollama pull nomic-embed-text
```

```bash
# .env
LLM_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=ollama                # any non-empty value
LLM_MODEL=qwen3.5:0.8b
EMBED_BASE_URL=http://localhost:11434
EMBED_MODEL=nomic-embed-text
```
