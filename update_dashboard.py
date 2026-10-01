import json

html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI Subscription Task Yield & Burn Rate Tracker (Reconciled v6)</title>
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
  <style>
    :root {
      --background: #090d16;
      --card: #111827;
      --card-inner: #1a2234;
      --border: #23304a;
      --foreground: #f8fafc;
      --muted-foreground: #94a3b8;
      --primary: #3b82f6;
      --accent: #10b981;
    }
  </style>
</head>
<body class="bg-[var(--background)] text-[var(--foreground)] antialiased min-h-screen p-4 md:p-8">
  <div class="max-w-7xl mx-auto space-y-6">

    <!-- Header -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[var(--border)] pb-6">
      <div>
        <div class="flex items-center gap-3">
          <div class="p-2.5 rounded-xl bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg>
          </div>
          <div>
            <div class="flex items-center gap-2">
              <h1 class="text-2xl font-bold tracking-tight text-[var(--foreground)]">AI Subscription Burn Tracker — Empirical v6</h1>
              <span class="px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">Reconciliation v6</span>
              <span class="px-2 py-0.5 rounded text-[11px] font-bold bg-blue-500/20 text-blue-300 border border-blue-500/30">Local telemetry only</span>
            </div>
            <p class="text-sm text-[var(--muted-foreground)]">Cross-model empirical telemetry reconciling Google AI Pro, ChatGPT Plus Work / Codex, and Cursor Pro</p>
          </div>
        </div>
      </div>

      <!-- Quick Download & Spend Bar -->
      <div class="flex flex-wrap items-center gap-2">
        <a href="/AI_Subscription_Burn_Rate_Reconciled_v6_2026-09-23.xlsx" download class="px-3 py-1.5 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/30 border border-emerald-500/40 text-emerald-300 text-xs font-semibold flex items-center gap-1.5 transition">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
          Excel Workbook (v6)
        </a>
        <div class="bg-[var(--card)] px-3 py-1.5 rounded-lg border border-[var(--border)] text-xs text-[var(--muted-foreground)]">
          Monthly Spend: <span class="font-bold text-white">$59.99/mo</span>
        </div>
      </div>
    </div>

    <!-- Pass 5 Matched-Task Empirical Telemetry Section -->
    <div class="bg-[var(--card)] border border-blue-500/30 rounded-xl p-6 shadow-sm space-y-6">
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[var(--border)] pb-4">
        <div>
          <div class="flex items-center gap-2">
            <span class="text-xs font-bold text-blue-400 uppercase tracking-wider">Ground-Truth Empirical Telemetry (Pass 5)</span>
            <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30">Controlled Matched Pairs (N=194)</span>
          </div>
          <h2 class="text-lg font-bold text-white mt-1">Antigravity Quota Burn & First-Pass Success Telemetry</h2>
          <p class="text-xs text-[var(--muted-foreground)]">All confounders removed: 40 identical tasks tested across both models in each independent 5-hour pool.</p>
        </div>

        <!-- Tier Switcher -->
        <div class="flex items-center bg-slate-900 border border-slate-700 p-1 rounded-lg">
          <button id="btnTier2" onclick="setTierView('tier2')" class="px-3 py-1 text-xs font-semibold rounded-md bg-blue-600 text-white transition">
            Tier 2: Standard Engineering
          </button>
          <button id="btnTier3" onclick="setTierView('tier3')" class="px-3 py-1 text-xs font-semibold rounded-md text-slate-400 hover:text-white transition">
            Tier 3: Long-Horizon Agent
          </button>
        </div>
      </div>

      <!-- Telemetry Table -->
      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs">
          <thead class="border-b border-[var(--border)] text-[var(--muted-foreground)] uppercase text-[10px] tracking-wider">
            <tr>
              <th class="py-3 px-3">Model</th>
              <th class="py-3 px-3">Quota Pool</th>
              <th class="py-3 px-3 text-center">Attempts (N)</th>
              <th class="py-3 px-3 text-center">1st Pass % (Wilson 95% CI)</th>
              <th class="py-3 px-3 text-center">5h Quota / Task</th>
              <th class="py-3 px-3 text-right">Tasks / 1% Visible</th>
              <th class="py-3 px-3 text-right">Tasks / 100% Pool</th>
              <th class="py-3 px-3 text-right">Mean Tokens</th>
              <th class="py-3 px-3 text-right">Mean Latency</th>
            </tr>
          </thead>
          <tbody id="telemetryBody" class="divide-y divide-slate-800">
            <!-- Dynamically populated -->
          </tbody>
        </table>
      </div>

      <!-- Causal Comparisons Callout Box -->
      <div id="causalAnalysisBox" class="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-3">
        <!-- Dynamically rendered insights -->
      </div>
    </div>

    <!-- Reconciled Multi-Subscription Master Matrix -->
    <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl p-6 shadow-sm space-y-4">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 class="text-lg font-bold text-white">Reconciled Subscription Harness Yield Comparison</h2>
          <p class="text-xs text-[var(--muted-foreground)]">Comparing true usable capacity per reset cycle across all 3 active developer subscriptions</p>
        </div>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs">
          <thead class="border-b border-[var(--border)] text-[var(--muted-foreground)] uppercase text-[10px] tracking-wider">
            <tr>
              <th class="py-3 px-3">Subscription</th>
              <th class="py-3 px-3">Harness & Quota Pool</th>
              <th class="py-3 px-3">Top Workload Model</th>
              <th class="py-3 px-3">Optimal Tier</th>
              <th class="py-3 px-3 text-right">Reset Window</th>
              <th class="py-3 px-3 text-right">Usable Tasks / Cycle</th>
              <th class="py-3 px-3">Quota Model Architecture</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-800">
            <tr class="hover:bg-slate-800/40">
              <td class="py-3 px-3 font-semibold text-white">Google AI Pro ($19.99)</td>
              <td class="py-3 px-3 text-blue-400 font-mono">Pool A: Gemini</td>
              <td class="py-3 px-3 font-bold text-emerald-400">Gemini 3.8 Flash Medium</td>
              <td class="py-3 px-3"><span class="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300">Tier 1 & 2 Standard</span></td>
              <td class="py-3 px-3 text-right text-slate-300">5-hour rolling</td>
              <td class="py-3 px-3 text-right font-bold text-emerald-400">~2,000 tasks</td>
              <td class="py-3 px-3 text-slate-400">Independent pool. Whole % UI decrement. 20 tasks per visible 1%.</td>
            </tr>
            <tr class="hover:bg-slate-800/40">
              <td class="py-3 px-3 font-semibold text-white">Google AI Pro ($19.99)</td>
              <td class="py-3 px-3 text-blue-400 font-mono">Pool A: Gemini</td>
              <td class="py-3 px-3 font-bold text-blue-300">Gemini 3.1 Pro High</td>
              <td class="py-3 px-3"><span class="px-2 py-0.5 rounded bg-purple-500/20 text-purple-300">Tier 3 Long-Horizon</span></td>
              <td class="py-3 px-3 text-right text-slate-300">5-hour rolling</td>
              <td class="py-3 px-3 text-right font-bold text-blue-300">~200 tasks</td>
              <td class="py-3 px-3 text-slate-400">High reasoning reliability (60% 1st pass); avoids token explosion.</td>
            </tr>
            <tr class="hover:bg-slate-800/40">
              <td class="py-3 px-3 font-semibold text-white">Google AI Pro ($19.99)</td>
              <td class="py-3 px-3 text-purple-400 font-mono">Pool B: Claude/GPT</td>
              <td class="py-3 px-3 font-bold text-indigo-300">Claude Sonnet 4.6</td>
              <td class="py-3 px-3"><span class="px-2 py-0.5 rounded bg-blue-500/20 text-blue-300">Tier 2 Standard</span></td>
              <td class="py-3 px-3 text-right text-slate-300">5-hour rolling</td>
              <td class="py-3 px-3 text-right font-bold text-indigo-300">~333 tasks</td>
              <td class="py-3 px-3 text-slate-400">Independent 5h pool from Gemini. 3.33 tasks per visible 1%.</td>
            </tr>
            <tr class="hover:bg-slate-800/40">
              <td class="py-3 px-3 font-semibold text-white">Google AI Pro ($19.99)</td>
              <td class="py-3 px-3 text-purple-400 font-mono">Pool B: Claude/GPT</td>
              <td class="py-3 px-3 font-bold text-purple-300">Claude Opus 4.6 Thinking</td>
              <td class="py-3 px-3"><span class="px-2 py-0.5 rounded bg-purple-500/20 text-purple-300">Tier 3 Long-Horizon</span></td>
              <td class="py-3 px-3 text-right text-slate-300">5-hour rolling</td>
              <td class="py-3 px-3 text-right font-bold text-purple-300">~100 tasks</td>
              <td class="py-3 px-3 text-slate-400">Highest single-turn agent completion rate (60% 1st pass).</td>
            </tr>
            <tr class="hover:bg-slate-800/40">
              <td class="py-3 px-3 font-semibold text-white">Cursor Pro ($20.00)</td>
              <td class="py-3 px-3 text-amber-400 font-mono">Cursor Models Pool</td>
              <td class="py-3 px-3 font-bold text-amber-300">Composer 2.5 (Normal)</td>
              <td class="py-3 px-3"><span class="px-2 py-0.5 rounded bg-blue-500/20 text-blue-300">Tier 2 & 3 Coding</span></td>
              <td class="py-3 px-3 text-right text-slate-300">Monthly billing</td>
              <td class="py-3 px-3 text-right font-bold text-amber-300">~300–450 tasks</td>
              <td class="py-3 px-3 text-slate-400">Avoid Composer Fast (~6x burn multiplier for same model).</td>
            </tr>
            <tr class="hover:bg-slate-800/40">
              <td class="py-3 px-3 font-semibold text-white">Cursor Pro ($20.00)</td>
              <td class="py-3 px-3 text-amber-400 font-mono">Other Models Pool</td>
              <td class="py-3 px-3 font-bold text-pink-300">Claude Opus 5.5</td>
              <td class="py-3 px-3"><span class="px-2 py-0.5 rounded bg-pink-500/20 text-pink-300">Tier 3 & 4 Complex</span></td>
              <td class="py-3 px-3 text-right text-slate-300">Monthly billing</td>
              <td class="py-3 px-3 text-right font-bold text-pink-300">~120 tasks</td>
              <td class="py-3 px-3 text-slate-400">1.88x–1.99x burn of Sonnet 5; high value on greenfield architecture.</td>
            </tr>
            <tr class="hover:bg-slate-800/40">
              <td class="py-3 px-3 font-semibold text-white">ChatGPT Plus ($20.00)</td>
              <td class="py-3 px-3 text-emerald-400 font-mono">OpenAI Work / Codex</td>
              <td class="py-3 px-3 font-bold text-emerald-300">GPT-5.6 Sol / Terra</td>
              <td class="py-3 px-3"><span class="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300">Tier 2 General</span></td>
              <td class="py-3 px-3 text-right text-slate-300">5-hour rolling</td>
              <td class="py-3 px-3 text-right font-bold text-emerald-300">~50–100 msgs</td>
              <td class="py-3 px-3 text-slate-400">5-hour capacity: Sol=10–100, Terra=25–200, Astra=5–45.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Optimization Recommendations -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div class="p-5 rounded-xl bg-[var(--card)] border border-slate-800 space-y-2">
        <div class="flex items-center gap-2 text-blue-400 font-bold text-sm">
          <span>⚡</span> Rule 1: The Tier-3 Flash Crossover Trap
        </div>
        <p class="text-xs text-[var(--muted-foreground)] leading-relaxed">
          Do NOT use Flash Medium for complex multi-step agent coding (Tier 3). Flash exhibits token explosion (<strong>71.9k tokens</strong> vs Pro's <strong>35.4k</strong>) and plunges to <strong>41.4%</strong> first-pass reliability, taking <strong>309 seconds</strong> per attempt. Switch to <strong>Gemini 3.1 Pro High</strong> or <strong>Claude Opus 4.6</strong>.
        </p>
      </div>

      <div class="p-5 rounded-xl bg-[var(--card)] border border-slate-800 space-y-2">
        <div class="flex items-center gap-2 text-purple-400 font-bold text-sm">
          <span>🛡️</span> Rule 2: The Sonnet Reliability Cliff
        </div>
        <p class="text-xs text-[var(--muted-foreground)] leading-relaxed">
          Claude Sonnet 4.6 is 2x cheaper on raw quota, but on Tier-3 tasks its first-pass completion drops to <strong>37.9%</strong> (requiring 18 retries across 20 tasks). When writing high-risk greenfield code or complex multi-file diffs, use <strong>Opus 4.6 Thinking</strong> (60.0% first-pass success).
        </p>
      </div>

      <div class="p-5 rounded-xl bg-[var(--card)] border border-slate-800 space-y-2">
        <div class="flex items-center gap-2 text-amber-400 font-bold text-sm">
          <span>🎯</span> Rule 3: Avoid Composer "Fast" in Cursor
        </div>
        <p class="text-xs text-[var(--muted-foreground)] leading-relaxed">
          Composer Fast burns quota at ~6x the rate of Composer Normal for the exact same intelligence. Keep Composer in Normal mode, and spend the Other Models pool on <strong>Claude Opus 5.5</strong> for maximum leverage.
        </p>
      </div>
    </div>

  </div>

  <script>
    const TELEMETRY_DATA = {
      tier2: [
        {
          model: 'Gemini 3.8 Flash Medium',
          pool: 'Pool A (Gemini)',
          attempts: 22,
          completed: 20,
          firstPassRate: '81.8%',
          ci: '61.5%–92.7%',
          quotaPerTask: '0.050%',
          tasksPer1Pct: '20.0',
          tasksPer100Pct: '2,000.0',
          tokens: '6,984',
          latency: '64.5s',
          badge: 'bg-emerald-500/20 text-emerald-300'
        },
        {
          model: 'Gemini 3.1 Pro High',
          pool: 'Pool A (Gemini)',
          attempts: 21,
          completed: 20,
          firstPassRate: '90.5%',
          ci: '71.1%–97.3%',
          quotaPerTask: '0.250%',
          tasksPer1Pct: '4.0',
          tasksPer100Pct: '400.0',
          tokens: '10,459',
          latency: '107.8s',
          badge: 'bg-blue-500/20 text-blue-300'
        },
        {
          model: 'Claude Sonnet 4.6',
          pool: 'Pool B (Claude/GPT)',
          attempts: 22,
          completed: 20,
          firstPassRate: '81.8%',
          ci: '61.5%–92.7%',
          quotaPerTask: '0.300%',
          tasksPer1Pct: '3.33',
          tasksPer100Pct: '333.3',
          tokens: '16,460',
          latency: '94.0s',
          badge: 'bg-indigo-500/20 text-indigo-300'
        },
        {
          model: 'Claude Opus 4.6 Thinking',
          pool: 'Pool B (Claude/GPT)',
          attempts: 21,
          completed: 20,
          firstPassRate: '90.5%',
          ci: '71.1%–97.3%',
          quotaPerTask: '0.650%',
          tasksPer1Pct: '1.54',
          tasksPer100Pct: '153.8',
          tokens: '18,351',
          latency: '120.9s',
          badge: 'bg-purple-500/20 text-purple-300'
        }
      ],
      tier3: [
        {
          model: 'Gemini 3.8 Flash Medium',
          pool: 'Pool A (Gemini)',
          attempts: 29,
          completed: 20,
          firstPassRate: '41.4%',
          ci: '25.5%–59.3%',
          quotaPerTask: '0.200%',
          tasksPer1Pct: '5.0',
          tasksPer100Pct: '500.0',
          tokens: '71,866',
          latency: '309.2s',
          badge: 'bg-amber-500/20 text-amber-300'
        },
        {
          model: 'Gemini 3.1 Pro High',
          pool: 'Pool A (Gemini)',
          attempts: 25,
          completed: 20,
          firstPassRate: '60.0%',
          ci: '40.7%–76.6%',
          quotaPerTask: '0.500%',
          tasksPer1Pct: '2.0',
          tasksPer100Pct: '200.0',
          tokens: '35,427',
          latency: '228.0s',
          badge: 'bg-blue-500/20 text-blue-300'
        },
        {
          model: 'Claude Sonnet 4.6',
          pool: 'Pool B (Claude/GPT)',
          attempts: 29,
          completed: 20,
          firstPassRate: '37.9%',
          ci: '22.7%–56.0%',
          quotaPerTask: '0.500%',
          tasksPer1Pct: '2.0',
          tasksPer100Pct: '200.0',
          tokens: '31,444',
          latency: '217.3s',
          badge: 'bg-rose-500/20 text-rose-300'
        },
        {
          model: 'Claude Opus 4.6 Thinking',
          pool: 'Pool B (Claude/GPT)',
          attempts: 25,
          completed: 20,
          firstPassRate: '60.0%',
          ci: '40.7%–76.6%',
          quotaPerTask: '1.000%',
          tasksPer1Pct: '1.0',
          tasksPer100Pct: '100.0',
          tokens: '35,290',
          latency: '240.2s',
          badge: 'bg-purple-500/20 text-purple-300'
        }
      ]
    };

    let currentTier = 'tier2';

    function setTierView(tier) {
      currentTier = tier;
      document.getElementById('btnTier2').className = tier === 'tier2' 
        ? 'px-3 py-1 text-xs font-semibold rounded-md bg-blue-600 text-white transition'
        : 'px-3 py-1 text-xs font-semibold rounded-md text-slate-400 hover:text-white transition';
      document.getElementById('btnTier3').className = tier === 'tier3'
        ? 'px-3 py-1 text-xs font-semibold rounded-md bg-blue-600 text-white transition'
        : 'px-3 py-1 text-xs font-semibold rounded-md text-slate-400 hover:text-white transition';

      renderTelemetryTable();
    }

    function renderTelemetryTable() {
      const rows = TELEMETRY_DATA[currentTier];
      const tbody = document.getElementById('telemetryBody');
      tbody.innerHTML = rows.map(r => `
        <tr class="hover:bg-slate-800/40">
          <td class="py-3 px-3 font-bold text-white flex items-center gap-2">
            <span class="w-2 h-2 rounded-full ${r.badge.includes('emerald') ? 'bg-emerald-400' : r.badge.includes('blue') ? 'bg-blue-400' : r.badge.includes('indigo') ? 'bg-indigo-400' : r.badge.includes('purple') ? 'bg-purple-400' : r.badge.includes('rose') ? 'bg-rose-400' : 'bg-amber-400'}"></span>
            ${r.model}
          </td>
          <td class="py-3 px-3 text-slate-300 font-mono text-[11px]">${r.pool}</td>
          <td class="py-3 px-3 text-center text-slate-300">${r.attempts}</td>
          <td class="py-3 px-3 text-center">
            <span class="font-bold text-white">${r.firstPassRate}</span>
            <span class="text-[10px] text-slate-400 ml-1">(${r.ci})</span>
          </td>
          <td class="py-3 px-3 text-center font-mono text-slate-300">${r.quotaPerTask}</td>
          <td class="py-3 px-3 text-right font-mono font-semibold text-white">${r.tasksPer1Pct}</td>
          <td class="py-3 px-3 text-right font-bold text-emerald-400 font-mono">${r.tasksPer100Pct}</td>
          <td class="py-3 px-3 text-right text-slate-300 font-mono">${r.tokens}</td>
          <td class="py-3 px-3 text-right text-slate-400 font-mono">${r.latency}</td>
        </tr>
      `).join('');

      const box = document.getElementById('causalAnalysisBox');
      if (currentTier === 'tier2') {
        box.innerHTML = `
          <div class="text-xs font-bold text-blue-300 flex items-center gap-1.5">
            <span>🔬</span> Causal Analysis for Tier 2: Standard Engineering (20 Matched Tasks)
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-3 text-[11px] text-slate-300">
            <div class="p-3 bg-slate-950/60 rounded-lg border border-slate-800">
              <div class="font-bold text-white mb-1">Pool A: Flash Medium vs. Pro High</div>
              <ul class="list-disc list-inside space-y-1 text-slate-400">
                <li><strong class="text-emerald-400">Quota burn ratio: 0.20x</strong> (1% vs 5% visible delta)</li>
                <li>Flash completes <strong class="text-white">5.0x</strong> more tasks per 100% pool (2,000 vs 400).</li>
                <li>Pro offers slightly higher first pass (90.5% vs 81.8%), but Flash is 1.67x faster (64.5s vs 107.8s).</li>
                <li><span class="text-emerald-300 font-semibold">Takeaway:</span> Flash Medium is the unambiguous winner for Tier 2.</li>
              </ul>
            </div>
            <div class="p-3 bg-slate-950/60 rounded-lg border border-slate-800">
              <div class="font-bold text-white mb-1">Pool B: Sonnet 4.6 vs. Opus 4.6 Thinking</div>
              <ul class="list-disc list-inside space-y-1 text-slate-400">
                <li><strong class="text-indigo-400">Quota burn ratio: 0.462x</strong> (6% vs 13% visible delta)</li>
                <li>Sonnet yields <strong class="text-white">2.17x</strong> more completed tasks (333 vs 154).</li>
                <li>First-pass success is high on both (81.8% vs 90.5%).</li>
                <li><span class="text-indigo-300 font-semibold">Takeaway:</span> Sonnet 4.6 is the cost-effective default for standard refactors.</li>
              </ul>
            </div>
          </div>
        `;
      } else {
        box.innerHTML = `
          <div class="text-xs font-bold text-amber-300 flex items-center gap-1.5">
            <span>⚠️</span> Causal Analysis for Tier 3: Long-Horizon Agent Coding (20 Matched Tasks)
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-3 text-[11px] text-slate-300">
            <div class="p-3 bg-slate-950/60 rounded-lg border border-slate-800">
              <div class="font-bold text-white mb-1">Pool A: The Flash Crossover Effect</div>
              <ul class="list-disc list-inside space-y-1 text-slate-400">
                <li>Flash first-pass success plunges to <strong class="text-amber-400">41.4%</strong> (9 retries across 20 tasks).</li>
                <li><strong class="text-rose-400">Token explosion:</strong> Flash consumes <strong>71,866 tokens</strong>/attempt vs Pro's <strong>35,427</strong> (2.03x bloat!).</li>
                <li>Flash execution latency rises to <strong>309.2s</strong> vs Pro's <strong>228.0s</strong> due to endless repair loops.</li>
                <li><span class="text-amber-300 font-semibold">Takeaway:</span> Pro High provides 60% first-pass reliability and finishes faster.</li>
              </ul>
            </div>
            <div class="p-3 bg-slate-950/60 rounded-lg border border-slate-800">
              <div class="font-bold text-white mb-1">Pool B: The Sonnet Reliability Cliff</div>
              <ul class="list-disc list-inside space-y-1 text-slate-400">
                <li>Sonnet first-pass success drops to <strong class="text-rose-400">37.9%</strong> (18 retry loops needed).</li>
                <li>Opus 4.6 Thinking maintains <strong class="text-purple-300">60.0%</strong> first-pass completion.</li>
                <li>While Sonnet yields 2x raw quota capacity (200 vs 100), Opus eliminates the high developer tax of manual repairs.</li>
                <li><span class="text-purple-300 font-semibold">Takeaway:</span> Opus 4.6 is 1.58x more reliable for complex greenfield autonomy.</li>
              </ul>
            </div>
          </div>
        `;
      }
    }

    renderTelemetryTable();
  </script>
</body>
</html>
'''

with open('index.html', 'w') as f:
    f.write(html_content)

print("Dashboard index.html successfully updated.")
