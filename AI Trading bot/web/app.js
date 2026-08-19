const state = {
  settings: null,
};

const elements = {
  toast: document.getElementById("toast"),
  statusMode: document.getElementById("status-mode"),
  statusInstrument: document.getElementById("status-instrument"),
  statusCloud: document.getElementById("status-cloud"),
  strategyContent: document.getElementById("strategy-content"),
  learningContent: document.getElementById("learning-content"),
  marketSummary: document.getElementById("market-summary"),
  marketCandles: document.getElementById("market-candles"),
  accountSummary: document.getElementById("account-summary"),
  ledgerStats: document.getElementById("ledger-stats"),
  ledgerTable: document.getElementById("ledger-table"),
  orderResult: document.getElementById("order-result"),
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || payload.message || "Request failed.");
  }
  return payload;
}

function showToast(message) {
  elements.toast.textContent = message;
  elements.toast.classList.remove("hidden");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => {
    elements.toast.classList.add("hidden");
  }, 2600);
}

function setValue(id, value) {
  const el = document.getElementById(id);
  if (!el) return;
  if (el.type === "checkbox") {
    el.checked = Boolean(value);
    return;
  }
  el.value = value ?? "";
}

function getValue(id) {
  const el = document.getElementById(id);
  if (el.type === "checkbox") {
    return el.checked;
  }
  return el.value;
}

function renderMetrics(target, pairs) {
  target.innerHTML = "";
  for (const [label, value] of pairs) {
    const item = document.createElement("div");
    item.className = "metric";
    item.innerHTML = `<span class="metric-label">${label}</span><span class="metric-value">${value}</span>`;
    target.appendChild(item);
  }
}

function localDateInputValue(value) {
  if (!value) return "";
  return value.replace("Z", "").slice(0, 16);
}

function toIsoMaybe(value) {
  return value ? new Date(value).toISOString() : "";
}

function collectSettings() {
  return {
    mode: getValue("mode"),
    dry_run: getValue("dry-run"),
    default_instrument: getValue("default-instrument"),
    poll_seconds: Number(getValue("poll-seconds") || 30),
    blofin: {
      api_key: getValue("api-key"),
      api_secret: getValue("api-secret"),
      passphrase: getValue("passphrase"),
      base_url: getValue("base-url"),
    },
    strategy_profile: {
      ...state.settings.strategy_profile,
      risk_per_trade_pct: Number(getValue("risk-per-trade") || 1),
      max_open_positions: Number(getValue("max-open-positions") || 1),
    },
    cloud_memory: {
      ...state.settings.cloud_memory,
      enabled: getValue("cloud-enabled"),
      provider: getValue("cloud-provider"),
      supabase_url: getValue("supabase-url"),
      supabase_service_role: getValue("supabase-service-role"),
      supermemory_api_key: getValue("supermemory-api-key"),
    },
  };
}

function fillSettings(settings) {
  state.settings = settings;
  setValue("mode", settings.mode);
  setValue("dry-run", settings.dry_run);
  setValue("default-instrument", settings.default_instrument);
  setValue("poll-seconds", settings.poll_seconds);
  setValue("api-key", settings.blofin.api_key);
  setValue("api-secret", settings.blofin.api_secret);
  setValue("passphrase", settings.blofin.passphrase);
  setValue("base-url", settings.blofin.base_url);
  setValue("risk-per-trade", settings.strategy_profile.risk_per_trade_pct);
  setValue("max-open-positions", settings.strategy_profile.max_open_positions);
  setValue("cloud-enabled", settings.cloud_memory.enabled);
  setValue("cloud-provider", settings.cloud_memory.provider);
  setValue("supabase-url", settings.cloud_memory.supabase_url);
  setValue("supabase-service-role", settings.cloud_memory.supabase_service_role);
  setValue("supermemory-api-key", settings.cloud_memory.supermemory_api_key);
  setValue("market-inst", settings.default_instrument);
  setValue("order-inst", settings.default_instrument);
  setValue("ledger-symbol", settings.default_instrument);
}

async function loadStatus() {
  const status = await api("/api/status");
  elements.statusMode.textContent = `${status.mode} / ${status.dry_run ? "dry-run" : "live"}`;
  elements.statusInstrument.textContent = status.default_instrument;
  elements.statusCloud.textContent = `${status.cloud_memory.provider} (${status.cloud_memory.status})`;
}

async function loadSettings() {
  const payload = await api("/api/config");
  fillSettings(payload.settings);
}

async function saveSettings() {
  const payload = await api("/api/config", {
    method: "POST",
    body: JSON.stringify({ settings: collectSettings() }),
  });
  fillSettings(payload.settings);
  await loadStatus();
  showToast(payload.message);
}

async function loadStrategy() {
  const payload = await api("/api/strategy");
  elements.strategyContent.value = payload.content;
}

async function saveStrategy() {
  await api("/api/strategy", {
    method: "POST",
    body: JSON.stringify({ content: elements.strategyContent.value }),
  });
  showToast("Strategy file updated.");
}

async function loadMarket() {
  const instId = getValue("market-inst") || getValue("default-instrument");
  const payload = await api(`/api/market?instId=${encodeURIComponent(instId)}`);
  renderMetrics(elements.marketSummary, [
    ["Last", payload.ticker.last || "-"],
    ["Bid", payload.ticker.bidPrice || "-"],
    ["Ask", payload.ticker.askPrice || "-"],
    ["24h High", payload.ticker.high24h || "-"],
    ["24h Low", payload.ticker.low24h || "-"],
    ["Mark", payload.mark_price.markPrice || "-"],
    ["Max Leverage", payload.instrument_meta.maxLeverage || "-"],
  ]);
  elements.marketCandles.textContent = JSON.stringify(payload.candles.slice(0, 8), null, 2);
}

async function loadAccount() {
  const instId = getValue("market-inst") || getValue("default-instrument");
  const payload = await api(`/api/account?instId=${encodeURIComponent(instId)}`);
  if (!payload.configured) {
    renderMetrics(elements.accountSummary, [["Account", "Not configured"], ["Hint", "Add API credentials"]]);
    return;
  }
  const balances = Array.isArray(payload.balances) ? payload.balances : [];
  const firstBalance = balances[0] || {};
  renderMetrics(elements.accountSummary, [
    ["Balances", balances.length],
    ["Available", firstBalance.available || "-"],
    ["Equity", firstBalance.balance || "-"],
    ["Positions", Array.isArray(payload.positions) ? payload.positions.length : 0],
    ["Open orders", Array.isArray(payload.open_orders) ? payload.open_orders.length : 0],
    ["API name", payload.apikey.apiName || "-"],
  ]);
}

function collectOrder() {
  return {
    instId: getValue("order-inst"),
    side: getValue("order-side"),
    orderType: getValue("order-type"),
    positionSide: getValue("position-side"),
    marginMode: getValue("margin-mode"),
    size: getValue("order-size"),
    price: getValue("order-price"),
    clientOrderId: getValue("client-order-id"),
  };
}

async function sendOrder() {
  const payload = await api("/api/order", {
    method: "POST",
    body: JSON.stringify(collectOrder()),
  });
  elements.orderResult.textContent = JSON.stringify(payload, null, 2);
  showToast(payload.message);
}

function collectLedgerTrade() {
  return {
    symbol: getValue("ledger-symbol"),
    side: getValue("ledger-side"),
    setup: getValue("ledger-setup"),
    entry_price: getValue("ledger-entry"),
    exit_price: getValue("ledger-exit"),
    size: getValue("ledger-size"),
    opened_at: toIsoMaybe(getValue("ledger-opened")),
    closed_at: toIsoMaybe(getValue("ledger-closed")),
    pnl_usd: getValue("ledger-pnl-usd"),
    pnl_r: getValue("ledger-pnl-r"),
    timeframe: getValue("ledger-timeframe"),
    session: getValue("ledger-session"),
    notes: getValue("ledger-notes"),
  };
}

async function addTrade() {
  const payload = await api("/api/ledger", {
    method: "POST",
    body: JSON.stringify(collectLedgerTrade()),
  });
  showToast(payload.message);
  await loadLedger();
  await loadLearning();
}

async function loadLedger() {
  const payload = await api("/api/ledger");
  renderMetrics(elements.ledgerStats, [
    ["Trades", payload.stats.trade_count],
    ["Closed", payload.stats.closed_trade_count],
    ["Win rate", `${payload.stats.win_rate}%`],
    ["Total PnL", payload.stats.total_pnl_usd],
    ["Avg PnL", payload.stats.average_pnl_usd],
    ["Avg R", payload.stats.average_r],
  ]);
  elements.ledgerTable.textContent = payload.markdown;
}

async function loadLearning() {
  const payload = await api("/api/learning");
  elements.learningContent.value = payload.content;
}

async function refreshLearning() {
  const payload = await api("/api/learning/refresh", {
    method: "POST",
    body: JSON.stringify({}),
  });
  elements.learningContent.value = payload.content;
  showToast(payload.message);
}

async function bootstrap() {
  try {
    await loadSettings();
    const tasks = [
      loadStatus(),
      loadStrategy(),
      loadLedger(),
      loadLearning(),
      loadMarket().catch((error) => {
        renderMetrics(elements.marketSummary, [["Market data", "Unavailable"], ["Reason", error.message]]);
        elements.marketCandles.textContent = "Live BloFin market data is unavailable right now.";
      }),
      loadAccount().catch((error) => {
        renderMetrics(elements.accountSummary, [["Account data", "Unavailable"], ["Reason", error.message]]);
      }),
    ];
    await Promise.allSettled(tasks);
    setValue("ledger-opened", localDateInputValue(new Date().toISOString()));
  } catch (error) {
    showToast(error.message);
  }
}

document.getElementById("save-settings").addEventListener("click", () => saveSettings().catch((error) => showToast(error.message)));
document.getElementById("save-strategy").addEventListener("click", () => saveStrategy().catch((error) => showToast(error.message)));
document.getElementById("refresh-market").addEventListener("click", () => loadMarket().catch((error) => showToast(error.message)));
document.getElementById("refresh-account").addEventListener("click", () => loadAccount().catch((error) => showToast(error.message)));
document.getElementById("send-order").addEventListener("click", () => sendOrder().catch((error) => showToast(error.message)));
document.getElementById("add-trade").addEventListener("click", () => addTrade().catch((error) => showToast(error.message)));
document.getElementById("refresh-ledger").addEventListener("click", () => loadLedger().catch((error) => showToast(error.message)));
document.getElementById("refresh-learning").addEventListener("click", () => refreshLearning().catch((error) => showToast(error.message)));

bootstrap();
