document.addEventListener("DOMContentLoaded", () => {
    // 1. Initialize TradingView Lightweight Chart
    const chartContainer = document.getElementById("tvChartContainer");
    let chart, candleSeries;

    function initChart() {
        if (!chartContainer) return;
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
    }

    initChart();

    window.addEventListener('resize', () => {
        if (chart && chartContainer) {
            chart.applyOptions({
                width: chartContainer.clientWidth,
                height: chartContainer.clientHeight
            });
        }
    });

    // 2. Fetch and Populate Symbols Dropdown
    async function loadSymbols(selectedSymbol = "") {
        try {
            const res = await fetch("/api/groww/symbols");
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
            console.error("Error loading symbols:", e);
        }
    }

    const refreshBtn = document.getElementById("refreshSymbolsBtn");
    if (refreshBtn) {
        refreshBtn.addEventListener("click", async () => {
            refreshBtn.innerText = "⏳ Loading...";
            await loadSymbols();
            refreshBtn.innerText = "🔄 Refresh";
        });
    }

    // 3. WebSocket Connection for Real-Time Stream
    let socket;
    function connectWebSocket() {
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
            console.warn("[WebSocket] Disconnected. Reconnecting in 3s...");
            setTimeout(connectWebSocket, 3000);
        };
    }

    connectWebSocket();

    // 4. UI Update Logic
    function updateDashboard(data) {
        if (!data) return;

        if (data.forex_price) {
            document.getElementById("forexPrice").innerText = `$${data.forex_price.toFixed(2)}`;
        }
        if (data.mcx_price) {
            document.getElementById("mcxPrice").innerText = `₹${data.mcx_price.toLocaleString('en-IN', {minimumFractionDigits: 2})}`;
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

        if (data.token_status) {
            updateTokenBadges(data.token_status);
        }

        if (data.timeframe) {
            document.getElementById("chartTfLabel").innerText = data.timeframe;
        }
        if (data.strategy) {
            document.getElementById("activeStrategyBadge").innerText = data.strategy;
        }

        if (data.engine_status) {
            const status = data.engine_status;
            document.getElementById("totalEquity").innerText = `₹${status.total_equity.toLocaleString('en-IN', {minimumFractionDigits: 2})}`;
            
            const rPnlEl = document.getElementById("realizedPnl");
            rPnlEl.innerText = `₹${status.realized_pnl.toLocaleString('en-IN', {minimumFractionDigits: 2})}`;
            rPnlEl.className = `value ${status.realized_pnl >= 0 ? 'profit' : 'loss'}`;

            const autoBtn = document.getElementById("toggleAutoTradeBtn");
            const autoLabel = document.getElementById("autoTradeLabel");
            if (data.auto_trade_enabled) {
                autoBtn.className = "btn btn-toggle active";
                autoLabel.innerText = "AUTO TRADING ON";
            } else {
                autoBtn.className = "btn btn-toggle inactive";
                autoLabel.innerText = "AUTO TRADING OFF";
            }

            const noPosMsg = document.getElementById("noPositionMsg");
            const posDetails = document.getElementById("positionDetails");

            if (status.open_position) {
                const pos = status.open_position;
                noPosMsg.classList.add("hidden");
                posDetails.classList.remove("hidden");

                document.getElementById("posInstrument").innerText = pos.instrument;
                document.getElementById("posSideLots").innerText = `${pos.side} (${pos.lots} Lot)`;
                document.getElementById("posEntryPrice").innerText = `₹${pos.entry_price.toFixed(2)}`;

                const uPnlEl = document.getElementById("posUnrealizedPnl");
                uPnlEl.innerText = `₹${pos.unrealized_pnl.toFixed(2)}`;
                uPnlEl.className = `pnl-value ${pos.unrealized_pnl >= 0 ? 'profit' : 'loss'}`;

                const slText = pos.stop_loss ? `₹${pos.stop_loss.toFixed(2)}` : 'None';
                const tpText = pos.take_profit ? `₹${pos.take_profit.toFixed(2)}` : 'None';
                document.getElementById("posSlTp").innerText = `SL: ${slText} | TP: ${tpText}`;
            } else {
                noPosMsg.classList.remove("hidden");
                posDetails.classList.add("hidden");
            }
        }

        if (data.signal) {
            const banner = document.getElementById("signalBanner");
            banner.innerText = data.signal.signal || "NEUTRAL";
            banner.className = `signal-banner ${data.signal.signal || 'NEUTRAL'}`;
            document.getElementById("signalReason").innerText = data.signal.reason || "";
        }

        if (data.candles && data.candles.length > 0 && candleSeries) {
            const formatted = data.candles.map(c => ({
                time: c.time,
                open: c.open,
                high: c.high,
                low: c.low,
                close: c.close
            }));
            candleSeries.setData(formatted);
        }

        if (data.recent_logs) {
            renderActivityLogs(data.recent_logs);
        }
    }

    function renderActivityLogs(logs) {
        const container = document.getElementById("terminalLogsContainer");
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

    function updateTokenBadges(tokenStatus) {
        const growwBadge = document.getElementById("growwTokenBadge");
        const oandaBadge = document.getElementById("oandaTokenBadge");
        if (!tokenStatus) return;

        if (tokenStatus.groww && growwBadge) {
            if (tokenStatus.groww.valid) {
                growwBadge.className = "pill-badge badge-success";
                growwBadge.innerText = "Active / Valid";
            } else {
                growwBadge.className = "pill-badge badge-error";
                growwBadge.innerText = (tokenStatus.groww.message && tokenStatus.groww.message.includes("missing")) ? "Not Set" : "Invalid / Expired";
            }
            growwBadge.title = tokenStatus.groww.message || "";
        }

        if (tokenStatus.oanda && oandaBadge) {
            if (tokenStatus.oanda.valid) {
                oandaBadge.className = "pill-badge badge-success";
                oandaBadge.innerText = "Active / Valid";
            } else {
                oandaBadge.className = "pill-badge badge-error";
                oandaBadge.innerText = (tokenStatus.oanda.message && tokenStatus.oanda.message.includes("missing")) ? "Not Set" : "Invalid / Expired";
            }
            oandaBadge.title = tokenStatus.oanda.message || "";
        }
    }

    async function loadInitialStatus() {
        try {
            const res = await fetch("/api/status");
            const data = await res.json();
            
            if (data.config) {
                const cfg = data.config;
                document.getElementById("timeframeSelect").value = cfg.oanda.timeframe;
                document.getElementById("strategySelect").value = cfg.strategy.selected_strategy;
                document.getElementById("balanceInput").value = cfg.mcx.starting_balance;
                document.getElementById("slInput").value = cfg.strategy.stop_loss_pct;
                document.getElementById("tpInput").value = cfg.strategy.take_profit_pct;
                document.getElementById("oandaToken").value = cfg.oanda.api_token;
                document.getElementById("oandaAccount").value = cfg.oanda.account_id;
                if (cfg.mcx.groww_access_token) {
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

            if (data.token_status) {
                updateTokenBadges(data.token_status);
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

    // Verify Tokens Action
    const verifyBtn = document.getElementById("verifyTokensBtn");
    if (verifyBtn) {
        verifyBtn.addEventListener("click", async () => {
            const feedback = document.getElementById("tokenVerifyFeedback");
            feedback.style.display = "block";
            feedback.className = "verify-feedback";
            feedback.innerHTML = "<em>⏳ Testing credentials with live OANDA and Groww servers...</em>";

            const payload = {
                oanda_api_token: document.getElementById("oandaToken").value,
                oanda_account_id: document.getElementById("oandaAccount").value,
                oanda_environment: "practice",
                groww_access_token: document.getElementById("growwToken").value
            };

            try {
                const res = await fetch("/api/tokens/validate", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                updateTokenBadges(data);

                const oandaOk = data.oanda && data.oanda.valid;
                const growwOk = data.groww && data.groww.valid;

                let html = `<div><strong>OANDA:</strong> ${data.oanda.message}</div>`;
                html += `<div><strong>Groww:</strong> ${data.groww.message}</div>`;

                if (oandaOk && growwOk) {
                    feedback.className = "verify-feedback success";
                    html += `<div style="margin-top:6px; font-weight:bold;">🎉 Both live broker connections verified successfully!</div>`;
                } else {
                    feedback.className = "verify-feedback error";
                    html += `<div style="margin-top:6px; font-weight:bold;">⚠️ Token check reported errors. See details above.</div>`;
                }
                feedback.innerHTML = html;
            } catch (err) {
                feedback.className = "verify-feedback error";
                feedback.innerHTML = `<div>Verification failed: ${err}</div>`;
            }
        });
    }

    function renderTradeLogTable(trades) {
        const tbody = document.getElementById("tradeLogBody");
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
            if (data.token_status) {
                updateTokenBadges(data.token_status);
            }
        } catch (e) {}
    }, 3000);

    // Save Config Form
    document.getElementById("saveConfigBtn").addEventListener("click", async () => {
        const balanceVal = parseFloat(document.getElementById("balanceInput").value) || 25000;
        const selectedSym = document.getElementById("growwSymbol").value;
        const payload = {
            oanda_api_token: document.getElementById("oandaToken").value,
            oanda_account_id: document.getElementById("oandaAccount").value,
            oanda_environment: "practice",
            groww_access_token: document.getElementById("growwToken").value,
            groww_trading_symbol: selectedSym,
            timeframe: document.getElementById("timeframeSelect").value,
            selected_strategy: document.getElementById("strategySelect").value,
            starting_balance: balanceVal,
            stop_loss_pct: parseFloat(document.getElementById("slInput").value),
            take_profit_pct: parseFloat(document.getElementById("tpInput").value),
            live_market_only: document.getElementById("liveMarketOnlyCheckbox") ? document.getElementById("liveMarketOnlyCheckbox").checked : true,
            enforce_market_hours: document.getElementById("enforceMarketHoursCheckbox") ? document.getElementById("enforceMarketHoursCheckbox").checked : true
        };

        try {
            const res = await fetch("/api/config", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (data.status === "SUCCESS") {
                document.getElementById("totalEquity").innerText = `₹${balanceVal.toLocaleString('en-IN', {minimumFractionDigits: 2})}`;
                document.getElementById("realizedPnl").innerText = "₹0.00";
                document.getElementById("realizedPnl").className = "value neutral";
                if (data.token_status) {
                    updateTokenBadges(data.token_status);
                }
                
                const growwStatus = payload.groww_access_token ? "Configured" : "Not Provided";
                const modeStr = payload.live_market_only ? "Strict Live Only (Simulation Disabled)" : "Simulation Allowed";
                alert(`✅ Contract & Settings Saved!\n\n• Contract: ${selectedSym}\n• Mode: ${modeStr}\n• Account Balance reset to: ₹${balanceVal.toLocaleString('en-IN', {minimumFractionDigits: 2})}\n• Groww Token: ${growwStatus}\n• Strategy: ${payload.selected_strategy}\n\nThe engine updated live without needing a restart!`);
            }
        } catch (err) {
            alert("Failed to update settings: " + err);
        }
    });

    // Toggle Auto Trade
    document.getElementById("toggleAutoTradeBtn").addEventListener("click", async () => {
        try {
            await fetch("/api/autotrade/toggle", { method: "POST" });
        } catch (err) {}
    });

    // Manual Trading Actions
    document.getElementById("manualBuyBtn").addEventListener("click", async () => {
        const lots = parseInt(document.getElementById("manualLots").value) || 1;
        await triggerManualTrade("BUY", lots);
    });

    document.getElementById("manualSellBtn").addEventListener("click", async () => {
        const lots = parseInt(document.getElementById("manualLots").value) || 1;
        await triggerManualTrade("SELL", lots);
    });

    document.getElementById("manualSquareOffBtn").addEventListener("click", async () => {
        await triggerManualTrade("SQUARE_OFF", 1);
    });

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
