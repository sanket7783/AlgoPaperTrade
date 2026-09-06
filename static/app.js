// Global helper functions attached immediately to window so inline onclick handlers always work
window.updateTokenBadges = function(tokenStatus) {
    if (!tokenStatus) return;
    const growwBadge = document.getElementById("growwTokenBadge");
    const oandaBadge = document.getElementById("oandaTokenBadge");

    if (tokenStatus.groww && growwBadge) {
        if (tokenStatus.groww.valid) {
            growwBadge.className = "pill-badge badge-success";
            growwBadge.innerText = "Active / Valid";
        } else {
            growwBadge.className = "pill-badge badge-error";
            const isMissing = tokenStatus.groww.message && tokenStatus.groww.message.includes("missing");
            growwBadge.innerText = isMissing ? "Not Set" : "Invalid / Expired";
        }
        growwBadge.title = tokenStatus.groww.message || "";
    }

    if (tokenStatus.oanda && oandaBadge) {
        if (tokenStatus.oanda.valid) {
            oandaBadge.className = "pill-badge badge-success";
            oandaBadge.innerText = "Active / Valid";
        } else {
            oandaBadge.className = "pill-badge badge-error";
            const isMissing = tokenStatus.oanda.message && tokenStatus.oanda.message.includes("missing");
            oandaBadge.innerText = isMissing ? "Not Set" : "Invalid / Expired";
        }
        oandaBadge.title = tokenStatus.oanda.message || "";
    }
};

window.handleVerifyTokens = async function() {
    console.log("[AlgoPaperTrade] handleVerifyTokens triggered");
    const verifyBtn = document.getElementById("verifyTokensBtn");
    const feedback = document.getElementById("tokenVerifyFeedback");
    
    if (feedback) {
        feedback.style.display = "block";
        feedback.className = "verify-feedback";
        feedback.innerHTML = "<em>⏳ Testing credentials with live OANDA & Groww APIs...</em>";
    }
    if (verifyBtn) {
        verifyBtn.disabled = true;
        verifyBtn.innerText = "⏳ Verifying...";
    }

    const payload = {
        oanda_api_token: (document.getElementById("oandaToken")?.value || "").trim(),
        oanda_account_id: (document.getElementById("oandaAccount")?.value || "").trim(),
        oanda_environment: "practice",
        groww_access_token: (document.getElementById("growwToken")?.value || "").trim()
    };

    try {
        const res = await fetch("/api/tokens/validate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        console.log("[AlgoPaperTrade] Verify result:", data);

        if (window.updateTokenBadges) {
            window.updateTokenBadges(data);
        }

        const oandaOk = data.oanda && data.oanda.valid;
        const growwOk = data.groww && data.groww.valid;

        let html = `<div><strong>OANDA:</strong> ${data.oanda ? data.oanda.message : "Not tested"}</div>`;
        html += `<div><strong>Groww:</strong> ${data.groww ? data.groww.message : "Not tested"}</div>`;

        if (feedback) {
            if (oandaOk && growwOk) {
                feedback.className = "verify-feedback success";
                html += `<div style="margin-top:6px; font-weight:bold;">🎉 Both live broker connections verified!</div>`;
            } else {
                feedback.className = "verify-feedback error";
                html += `<div style="margin-top:6px; font-weight:bold;">⚠️ Token check reported issues. Review messages above.</div>`;
            }
            feedback.innerHTML = html;
        }
    } catch (err) {
        console.error("[AlgoPaperTrade] Verify Tokens Error:", err);
        if (feedback) {
            feedback.className = "verify-feedback error";
            feedback.innerHTML = `<div>❌ Network or server error: ${err.message || err}</div>`;
        }
    } finally {
        if (verifyBtn) {
            verifyBtn.disabled = false;
            verifyBtn.innerText = "🔍 Test & Verify Tokens";
        }
    }
};

window.handleSaveConfig = async function() {
    console.log("[AlgoPaperTrade] handleSaveConfig triggered");
    const saveBtn = document.getElementById("saveConfigBtn");
    const feedback = document.getElementById("configSaveFeedback");

    if (feedback) {
        feedback.style.display = "block";
        feedback.className = "verify-feedback";
        feedback.innerHTML = "<em>⏳ Saving and updating live trading engine...</em>";
    }
    if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.innerText = "⏳ Saving...";
    }

    const balanceInput = document.getElementById("balanceInput");
    const balanceVal = balanceInput ? (parseFloat(balanceInput.value) || 25000) : 25000;
    const selectedSym = document.getElementById("growwSymbol")?.value || "GOLDGUINEA26OCTFUT";
    const slInput = document.getElementById("slInput");
    const tpInput = document.getElementById("tpInput");
    const liveMarketCheckbox = document.getElementById("liveMarketOnlyCheckbox");
    const enforceHoursCheckbox = document.getElementById("enforceMarketHoursCheckbox");

    const payload = {
        oanda_api_token: (document.getElementById("oandaToken")?.value || "").trim(),
        oanda_account_id: (document.getElementById("oandaAccount")?.value || "").trim(),
        oanda_environment: "practice",
        groww_access_token: (document.getElementById("growwToken")?.value || "").trim(),
        groww_trading_symbol: selectedSym,
        timeframe: document.getElementById("timeframeSelect")?.value || "M5",
        selected_strategy: document.getElementById("strategySelect")?.value || "EMA_CROSSOVER",
        starting_balance: balanceVal,
        stop_loss_pct: slInput ? (parseFloat(slInput.value) || 0.5) : 0.5,
        take_profit_pct: tpInput ? (parseFloat(tpInput.value) || 1.0) : 1.0,
        fast_ema: 9,
        slow_ema: 21,
        live_market_only: liveMarketCheckbox ? liveMarketCheckbox.checked : true,
        enforce_market_hours: enforceHoursCheckbox ? enforceHoursCheckbox.checked : true
    };

    try {
        const res = await fetch("/api/config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        
        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || `Server returned HTTP ${res.status}`);
        }

        const data = await res.json();
        console.log("[AlgoPaperTrade] Config saved:", data);

        const totalEquityEl = document.getElementById("totalEquity");
        if (totalEquityEl) {
            totalEquityEl.innerText = `₹${balanceVal.toLocaleString('en-IN', {minimumFractionDigits: 2})}`;
        }
        const rPnlEl = document.getElementById("realizedPnl");
        if (rPnlEl) {
            rPnlEl.innerText = "₹0.00";
            rPnlEl.className = "value neutral";
        }

        if (data.token_status && window.updateTokenBadges) {
            window.updateTokenBadges(data.token_status);
        }

        const modeStr = payload.live_market_only ? "Strict Live Only" : "Simulation Enabled";
        const growwStatus = payload.groww_access_token ? "Active Token Provided" : "No Token";

        if (feedback) {
            feedback.className = "verify-feedback success";
            feedback.innerHTML = `
                <div><strong>✅ Settings Applied Live!</strong></div>
                <div style="font-size:11px; margin-top:4px;">
                    • Contract: <strong>${selectedSym}</strong><br>
                    • Mode: <strong>${modeStr}</strong><br>
                    • Paper Balance: <strong>₹${balanceVal.toLocaleString('en-IN')}</strong><br>
                    • Groww Token: <strong>${growwStatus}</strong>
                </div>
            `;
        }
    } catch (err) {
        console.error("[AlgoPaperTrade] Save Config Error:", err);
        if (feedback) {
            feedback.className = "verify-feedback error";
            feedback.innerHTML = `<div>❌ Failed to save settings: ${err.message || err}</div>`;
        }
    } finally {
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.innerText = "💾 Save & Apply Live";
        }
    }
};

document.addEventListener("DOMContentLoaded", () => {
    // 1. Initialize TradingView Lightweight Chart with safety checks
    const chartContainer = document.getElementById("tvChartContainer");
    let chart, candleSeries;

    function initChart() {
        if (!chartContainer) return;
        if (typeof LightweightCharts === "undefined") {
            console.warn("[AlgoPaperTrade] LightweightCharts CDN not loaded; skipping chart render");
            chartContainer.innerHTML = "<div style='color:#8A99AD;padding:40px;text-align:center;'>Candlestick chart loading or offline. Trading and settings remain fully active.</div>";
            return;
        }

        try {
            chartContainer.innerHTML = "";
            chart = LightweightCharts.createChart(chartContainer, {
                layout: {
                    backgroundColor: 'transparent',
                    textColor: '#8A99AD',
                },
                grid: {
                    vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
                    horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
                },
                crosshair: {
                    mode: LightweightCharts.CrosshairMode.Normal,
                },
                rightPriceScale: {
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                },
                timeScale: {
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    timeVisible: true,
                    secondsVisible: false,
                },
            });

            candleSeries = chart.addCandlestickSeries({
                upColor: '#10B981',
                downColor: '#EF4444',
                borderDownColor: '#EF4444',
                borderUpColor: '#10B981',
                wickDownColor: '#EF4444',
                wickUpColor: '#10B981',
            });
        } catch (e) {
            console.error("[AlgoPaperTrade] Chart initialization error:", e);
        }
    }

    initChart();

    window.addEventListener('resize', () => {
        if (chart && chartContainer) {
            try {
                chart.applyOptions({
                    width: chartContainer.clientWidth,
                    height: chartContainer.clientHeight
                });
            } catch (e) {}
        }
    });

    // 2. Fetch and Populate Symbols Dropdown directly from Groww
    async function loadSymbols(selectedSymbol = "", forceRefresh = false) {
        try {
            const url = forceRefresh ? "/api/groww/symbols?refresh=true" : "/api/groww/symbols";
            const res = await fetch(url);
            const data = await res.json();
            const symbolsSelect = document.getElementById("growwSymbol");
            if (data.symbols && symbolsSelect) {
                const currentVal = selectedSymbol || symbolsSelect.value;
                symbolsSelect.innerHTML = data.symbols.map(s => {
                    const isSel = s.symbol === currentVal ? "selected" : "";
                    return `<option value="${s.symbol}" ${isSel}>${s.display_name}</option>`;
                }).join("");
            }
        } catch (e) {
            console.error("[AlgoPaperTrade] Error loading symbols from Groww:", e);
        }
    }

    const refreshBtn = document.getElementById("refreshSymbolsBtn");
    if (refreshBtn) {
        refreshBtn.addEventListener("click", async () => {
            refreshBtn.innerText = "⏳ Fetching from Groww...";
            await loadSymbols("", true);
            refreshBtn.innerText = "🔄 Refresh";
        });
    }

    // 3. WebSocket Connection for Real-Time Stream
    let socket;
    function connectWebSocket() {
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws/stream`;
            socket = new WebSocket(wsUrl);

            socket.onopen = () => {
                console.log("[WebSocket] Connected to market stream");
            };

            socket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    updateDashboard(data);
                } catch (err) {
                    console.error("[WebSocket Error]", err);
                }
            };

            socket.onclose = () => {
                setTimeout(connectWebSocket, 3000);
            };
        } catch (e) {
            console.error("[WebSocket Init Error]", e);
        }
    }

    connectWebSocket();

    // 4. Update UI Dashboard Elements
    function updateDashboard(data) {
        if (!data) return;

        if (data.forex_price) {
            const el = document.getElementById("forexPrice");
            if (el) el.innerText = `$${data.forex_price.toFixed(2)}`;
        }
        if (data.mcx_price) {
            const el = document.getElementById("mcxPrice");
            if (el) el.innerText = `₹${data.mcx_price.toLocaleString('en-IN', {minimumFractionDigits: 2})}`;
        }

        if (data.mcx_source) {
            const badge = document.getElementById("mcxSourceBadge");
            if (badge) {
                if (data.mcx_source === 'GROWW_LIVE_API') {
                    badge.innerText = 'GROWW LIVE';
                    badge.style.color = '#10B981';
                } else if (data.mcx_source === 'GROWW_UNAVAILABLE') {
                    badge.innerText = 'GROWW OFFLINE';
                    badge.style.color = '#EF4444';
                } else {
                    badge.innerText = 'DERIVED';
                    badge.style.color = '#E5C158';
                }
            }
        }

        if (data.token_status && window.updateTokenBadges) {
            window.updateTokenBadges(data.token_status);
        }

        if (data.timeframe) {
            const el = document.getElementById("chartTfLabel");
            if (el) el.innerText = data.timeframe;
        }
        if (data.strategy) {
            const el = document.getElementById("activeStrategyBadge");
            if (el) el.innerText = data.strategy;
        }

        if (data.engine_status) {
            const status = data.engine_status;
            const eqEl = document.getElementById("totalEquity");
            if (eqEl) eqEl.innerText = `₹${status.total_equity.toLocaleString('en-IN', {minimumFractionDigits: 2})}`;
            
            const rPnlEl = document.getElementById("realizedPnl");
            if (rPnlEl) {
                rPnlEl.innerText = `₹${status.realized_pnl.toLocaleString('en-IN', {minimumFractionDigits: 2})}`;
                rPnlEl.className = `value ${status.realized_pnl >= 0 ? 'profit' : 'loss'}`;
            }

            const autoBtn = document.getElementById("toggleAutoTradeBtn");
            const autoLabel = document.getElementById("autoTradeLabel");
            if (autoBtn && autoLabel) {
                if (data.auto_trade_enabled) {
                    autoBtn.className = "btn btn-toggle active";
                    autoLabel.innerText = "AUTO TRADING ON";
                } else {
                    autoBtn.className = "btn btn-toggle inactive";
                    autoLabel.innerText = "AUTO TRADING OFF";
                }
            }

            const noPosMsg = document.getElementById("noPositionMsg");
            const posDetails = document.getElementById("positionDetails");

            if (status.open_position) {
                const pos = status.open_position;
                if (noPosMsg) noPosMsg.classList.add("hidden");
                if (posDetails) posDetails.classList.remove("hidden");

                const instEl = document.getElementById("posInstrument");
                if (instEl) instEl.innerText = pos.instrument;
                const sideEl = document.getElementById("posSideLots");
                if (sideEl) sideEl.innerText = `${pos.side} (${pos.lots} Lot)`;
                const entryEl = document.getElementById("posEntryPrice");
                if (entryEl) entryEl.innerText = `₹${pos.entry_price.toFixed(2)}`;

                const uPnlEl = document.getElementById("posUnrealizedPnl");
                if (uPnlEl) {
                    uPnlEl.innerText = `₹${pos.unrealized_pnl.toFixed(2)}`;
                    uPnlEl.className = `pnl-value ${pos.unrealized_pnl >= 0 ? 'profit' : 'loss'}`;
                }

                const slText = pos.stop_loss ? `₹${pos.stop_loss.toFixed(2)}` : 'None';
                const tpText = pos.take_profit ? `₹${pos.take_profit.toFixed(2)}` : 'None';
                const sltpEl = document.getElementById("posSlTp");
                if (sltpEl) sltpEl.innerText = `SL: ${slText} | TP: ${tpText}`;
            } else {
                if (noPosMsg) noPosMsg.classList.remove("hidden");
                if (posDetails) posDetails.classList.add("hidden");
            }
        }

        if (data.signal) {
            const banner = document.getElementById("signalBanner");
            if (banner) {
                banner.innerText = data.signal.signal || "NEUTRAL";
                banner.className = `signal-banner ${data.signal.signal || 'NEUTRAL'}`;
            }
            const reasonEl = document.getElementById("signalReason");
            if (reasonEl) reasonEl.innerText = data.signal.reason || "";
        }

        // Render Candles on chart
        if (candleSeries && data.candles && data.candles.length > 0) {
            try {
                candleSeries.setData(data.candles);
            } catch (err) {}
        }

        if (data.recent_logs) {
            renderActivityLogs(data.recent_logs);
        }
    }

    function renderActivityLogs(logs) {
        const container = document.getElementById("activityLogsContainer");
        if (!container || !logs || logs.length === 0) return;

        container.innerHTML = logs.map(l => {
            const catClass = l.category || 'SYSTEM';
            return `
                <div class="log-item ${catClass}">
                    <span class="time">[${l.timestamp}]</span>
                    <span class="msg">[${catClass}] ${l.message}</span>
                </div>
            `;
        }).join("");

        container.scrollTop = container.scrollHeight;
    }

    async function loadInitialStatus() {
        try {
            const res = await fetch("/api/status");
            const data = await res.json();
            
            if (data.config) {
                const cfg = data.config;
                if (document.getElementById("timeframeSelect")) document.getElementById("timeframeSelect").value = cfg.oanda.timeframe;
                if (document.getElementById("strategySelect")) document.getElementById("strategySelect").value = cfg.strategy.selected_strategy;
                if (document.getElementById("balanceInput")) document.getElementById("balanceInput").value = cfg.mcx.starting_balance;
                if (document.getElementById("slInput")) document.getElementById("slInput").value = cfg.strategy.stop_loss_pct;
                if (document.getElementById("tpInput")) document.getElementById("tpInput").value = cfg.strategy.take_profit_pct;
                if (document.getElementById("oandaToken")) document.getElementById("oandaToken").value = cfg.oanda.api_token;
                if (document.getElementById("oandaAccount")) document.getElementById("oandaAccount").value = cfg.oanda.account_id;
                if (cfg.mcx.groww_access_token && document.getElementById("growwToken")) {
                    document.getElementById("growwToken").value = cfg.mcx.groww_access_token;
                }
                if (document.getElementById("liveMarketOnlyCheckbox") && cfg.live_market_only !== undefined) {
                    document.getElementById("liveMarketOnlyCheckbox").checked = cfg.live_market_only;
                }
                if (document.getElementById("enforceMarketHoursCheckbox") && cfg.enforce_market_hours !== undefined) {
                    document.getElementById("enforceMarketHoursCheckbox").checked = cfg.enforce_market_hours;
                }
                await loadSymbols(cfg.mcx.groww_trading_symbol);
            } else {
                await loadSymbols();
            }

            if (data.token_status && window.updateTokenBadges) {
                window.updateTokenBadges(data.token_status);
            }

            if (data.trade_history) {
                renderTradeLogTable(data.trade_history);
            }

            if (data.recent_logs) {
                renderActivityLogs(data.recent_logs);
            }
        } catch (err) {
            console.error("[Init Status Error]", err);
            await loadSymbols();
        }
    }

    loadInitialStatus();

    // Attach Event Listeners defensively
    const verifyBtn = document.getElementById("verifyTokensBtn");
    if (verifyBtn) {
        verifyBtn.addEventListener("click", window.handleVerifyTokens);
    }

    const saveBtn = document.getElementById("saveConfigBtn");
    if (saveBtn) {
        saveBtn.addEventListener("click", window.handleSaveConfig);
    }

    function renderTradeLogTable(trades) {
        const tbody = document.getElementById("tradeLogBody");
        if (!tbody) return;
        if (!trades || trades.length === 0) {
            tbody.innerHTML = `<tr><td colspan="11" class="text-center">No trades logged yet. Engine running...</td></tr>`;
            return;
        }

        tbody.innerHTML = trades.slice().reverse().map(t => {
            const actionStr = t.Action || "";
            const isBuy = actionStr.includes("BUY");
            const isOpened = t.Status === "OPENED";
            
            let actionBadgeClass = isBuy ? "tag-buy" : "tag-sell";
            let pnlClass = "neutral";
            const pnlVal = parseFloat(t["Trade PnL (INR)"]) || 0;
            if (pnlVal > 0) pnlClass = "profit";
            else if (pnlVal < 0) pnlClass = "loss";

            return `
                <tr>
                    <td>${t.Date} ${t.Time}</td>
                    <td><strong>${t["Instrument Name"]}</strong></td>
                    <td>${t.Strategy}</td>
                    <td class="${actionBadgeClass}">${actionStr}</td>
                    <td>${t.Lots}</td>
                    <td>₹${parseFloat(t["Entry Price (INR)"]).toFixed(2)}</td>
                    <td>${isOpened ? '-' : '₹' + parseFloat(t["Exit Price (INR)"]).toFixed(2)}</td>
                    <td>$${parseFloat(t["Forex Ref Price ($)"]).toFixed(2)}</td>
                    <td class="${pnlClass}">${isOpened ? 'Active' : (pnlVal >= 0 ? '+₹' : '-₹') + Math.abs(pnlVal).toFixed(2)}</td>
                    <td>₹${parseFloat(t["Account Balance (INR)"]).toLocaleString('en-IN', {minimumFractionDigits: 2})}</td>
                    <td><span class="status-badge ${t.Status}">${t.Status}</span></td>
                </tr>
            `;
        }).join("");
    }

    setInterval(async () => {
        try {
            const res = await fetch("/api/status");
            const data = await res.json();
            if (data.trade_history) {
                renderTradeLogTable(data.trade_history);
            }
            if (data.token_status && window.updateTokenBadges) {
                window.updateTokenBadges(data.token_status);
            }
        } catch (e) {}
    }, 3000);

    // Toggle Auto Trade
    const autoTradeBtn = document.getElementById("toggleAutoTradeBtn");
    if (autoTradeBtn) {
        autoTradeBtn.addEventListener("click", async () => {
            try {
                await fetch("/api/autotrade/toggle", { method: "POST" });
            } catch (err) {}
        });
    }

    // Manual Trading Actions
    const buyBtn = document.getElementById("manualBuyBtn");
    if (buyBtn) {
        buyBtn.addEventListener("click", async () => {
            const lots = parseInt(document.getElementById("manualLots")?.value) || 1;
            await triggerManualTrade("BUY", lots);
        });
    }

    const sellBtn = document.getElementById("manualSellBtn");
    if (sellBtn) {
        sellBtn.addEventListener("click", async () => {
            const lots = parseInt(document.getElementById("manualLots")?.value) || 1;
            await triggerManualTrade("SELL", lots);
        });
    }

    const sqBtn = document.getElementById("manualSquareOffBtn");
    if (sqBtn) {
        sqBtn.addEventListener("click", async () => {
            await triggerManualTrade("SQUARE_OFF", 1);
        });
    }

    // Test Auto Signal Execution (Toggles between BUY and SELL)
    let nextSignalSide = "BUY";
    const testBtn = document.getElementById("testAutoSignalBtn");
    if (testBtn) {
        testBtn.addEventListener("click", async () => {
            try {
                const res = await fetch("/api/trade/simulate_signal", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ signal: nextSignalSide })
                });
                const data = await res.json();
                alert(`Auto Signal Simulated: ${data.status} for ${data.side} @ ₹${data.entry_price}\n(Next test signal will be ${nextSignalSide === "BUY" ? "SELL" : "BUY"})`);
                nextSignalSide = nextSignalSide === "BUY" ? "SELL" : "BUY";
            } catch (err) {
                alert("Error triggering auto signal test: " + err);
            }
        });
    }

    async function triggerManualTrade(action, lots) {
        try {
            const res = await fetch("/api/trade/manual", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ action, lots })
            });
            const data = await res.json();
            if (data.reason) {
                alert(`Order Status: ${data.status} (${data.reason})`);
            }
        } catch (err) {
            alert("Error sending trade request: " + err);
        }
    }
});
