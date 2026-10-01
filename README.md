# AI Subscription Burn Rate Tracker & Model Matrix

A local-first, continuously updated tracking dashboard for your AI subscriptions and frontier model ecosystem.

## Your Active Stack
- **ChatGPT Plus / Codex**: `$20.00 / mo` (OpenAI reasoning suite, Canvas, Voice, Code Interpreter)
- **Gemini Pro / Antigravity**: `$19.99 / mo` (Google One AI Premium, 2M context window, Antigravity IDE, 2TB cloud storage)
- **Cursor Pro (w/ Grok Bot)**: `$20.00 / mo` (Claude 3.5 Sonnet, Grok 2 / Grok Bot, GPT-4o, Cursor Tab, 500 fast requests/mo + unlimited slow requests)
- **Total Fixed Monthly Burn Rate**: **`$59.99 / mo`** (~`$1.97 / day`, `$719.88 / yr`)

### Free Tiers & Value Multipliers
- **NousResearch**: Free access to Hermes 3 (405B, 70B, 8B) open reasoning & portal.
- **NVIDIA NIM**: 1,000 free inference credits on TensorRT-LLM GPU infrastructure (`build.nvidia.com`, Llama 3.3 Nemotron).
- **Free Compute Value Realized**: **`+$50.00 / mo`** in estimated API value.

---

## Quickstart

### 1. View Dashboard Locally
Start the built-in zero-dependency server:
```bash
python3 serve.py
```
Open [http://localhost:8787](http://localhost:8787) in your browser.

### 2. Sync Latest Model Releases & Prices
Fetch the freshest pricing, token limits, and newly released frontier models from community feeds (LiteLLM 4,100+ & OpenRouter 450+ models):
```bash
python3 sync_models.py
```

### 3. Check CLI Summary
Print an instant burn rate & overlap report in the terminal:
```bash
python3 calculator.py
```

### 4. Continuous Auto-Update (Cron or Antigravity Schedule)
To keep models and pricing updated every morning at 8 AM, you can add a simple cron job:
```bash
0 8 * * * /usr/bin/python3 /path/to/omniburn/sync_models.py >> /tmp/ai_burn_sync.log 2>&1

```
Or use the Antigravity `/schedule` command inside this chat!

---

## File Overview
- `subscriptions.json`: Config file storing active plans, billing amounts, features, and model inclusions.
- `sync_models.py`: Real-time ingestion engine pulling from LiteLLM and OpenRouter.
- `calculator.py`: Analytics engine calculating burn rates, overlap indices, and breakeven stats.
- `serve.py`: Lightweight API and web server (`localhost:8787`).
- `index.html`: Modern Tailwind dashboard with charts, table, and interactive simulator.
