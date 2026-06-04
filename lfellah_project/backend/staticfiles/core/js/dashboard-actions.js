/**
 * L'Fellah IoT — Dashboard Actions v2
 * Gere TOUS les boutons, onglets, API calls, exports.
 * Charge depuis /static/core/js/dashboard-actions.js
 */
console.log('Dashboard v2 loaded');
(function () {
    'use strict';

    /* ================================================================
       CONFIG
       ================================================================ */
    const API = {
        LATEST:  '/api/iot/sensor-latest/',
        CHART:   '/api/iot/sensor-chart/',
        UPLOAD:  '/api/upload/',
        SCANS:   '/api/scans/',
        EXPORT:  '/api/iot/sensor-export/',
        SCANS_EXPORT: '/api/scans/export/',
    };
    const POLL_INTERVAL  = 5000;  // 5s — mise a jour capteurs toutes les 5s
    const CHART_INTERVAL = 60000;  // 60s

    /* ================================================================
       HELPERS
       ================================================================ */
    const $ = id => document.getElementById(id);

    function safeNum(v) {
        if (v === null || v === undefined || v === '' || isNaN(v)) return null;
        return Number(v);
    }

    function safeJson(r) {
        var ct = r.headers.get('content-type') || '';
        if (!ct.includes('application/json')) {
            console.warn('[API] Reponse non-JSON (status=' + r.status + ', ct=' + ct + ')');
            return Promise.reject(new Error('Reponse non-JSON : ' + r.status));
        }
        return r.json();
    }

    function safeJsonOrNull(r) {
        if (!r.ok) return Promise.resolve(null);
        return safeJson(r);
    }

    /* ================================================================
       RUNTIME DEBUG — intercepteur de fetch avec logging complet
       ================================================================ */
    (function() {
        var origFetch = window.fetch;
        window.fetch = function(url, opts) {
            var fullUrl = url;
            // Ajouter timestamp cache-busting si URL relative
            if (typeof url === 'string' && url.startsWith('/')) {
                var sep = url.indexOf('?') >= 0 ? '&' : '?';
                fullUrl = url + sep + '_t=' + new Date().getTime();
            }
            console.log('[FETCH] origin=' + window.location.origin + ' | url=' + fullUrl);
            return origFetch(fullUrl, opts).then(function(r) {
                var ct = r.headers.get('content-type') || 'N/A';
                console.log('[FETCH] response status=' + r.status + ' | content-type=' + ct + ' | url=' + fullUrl);
                if (!r.ok) {
                    console.warn('[FETCH] HTTP ' + r.status + ' sur ' + fullUrl);
                }
                return r;
            }).catch(function(err) {
                console.error('[FETCH] ERREUR reseau sur ' + fullUrl + ' :', err.message);
                throw err;
            });
        };
    })();

    function getFetchOpts() {
        return {
            method: 'GET',
            headers: { 'Accept': 'application/json', 'Cache-Control': 'no-cache', 'Pragma': 'no-cache' },
            credentials: 'same-origin',
            cache: 'no-store',
        };
    }

    let espcamReady = false;
    let selectedPlantFile = null;
    let lastModeChange = 0;

    /* ================================================================
       TAB SWITCHING (avec support URL ?tab=xxx)
       ================================================================ */
    function switchTab(tabName) {
        document.querySelectorAll('.tab-panel').forEach(p => p.classList.add('hidden'));
        var panel = $('panel-' + tabName);
        if (panel) panel.classList.remove('hidden');
        // Mise a jour etat actif sidebar
        document.querySelectorAll('.nav-item').forEach(function(el) {
            el.classList.remove('text-forest-700', 'bg-forest-50');
            el.classList.add('text-stone-500');
        });
        var activeNav = document.querySelector('.nav-item[data-nav="' + tabName + '"]');
        if (activeNav) {
            activeNav.classList.remove('text-stone-500');
            activeNav.classList.add('text-forest-700', 'bg-forest-50');
        }
        try {
            var url = new URL(window.location);
            url.searchParams.set('tab', tabName);
            window.history.replaceState({}, '', url);
        } catch (_) {}
    }

    // Expose globalement pour le menu overlay
    window.switchTab = switchTab;

    function initTabs() {
        var initialTab = 'sensors';
        try {
            var params = new URLSearchParams(window.location.search);
            var t = params.get('tab');
            if (t && ['sensors', 'plants', 'espcam', 'export'].indexOf(t) !== -1) initialTab = t;
        } catch (_) {}
        // Mise a jour etat initial sidebar
        document.querySelectorAll('.nav-item').forEach(function(el) {
            el.classList.remove('text-forest-700', 'bg-forest-50');
            el.classList.add('text-stone-500');
        });
        var activeNav = document.querySelector('.nav-item[data-nav="' + initialTab + '"]');
        if (activeNav) {
            activeNav.classList.remove('text-stone-500');
            activeNav.classList.add('text-forest-700', 'bg-forest-50');
        }
        switchTab(initialTab);
    }

    /* ================================================================
       ALERTS & THRESHOLDS
       ================================================================ */
    function setLiveStatus(status, text) {
        const el = $('live-status');
        if (!el) return;
        const dot = el.querySelector('span');
        if (!dot) return;
        if (status === 'online') {
            dot.setAttribute('style', 'width:10px;height:10px;border-radius:50%;background:#22c55e;display:inline-block;animation:pulse 1.5s infinite');
            el.setAttribute('style', 'font-size:0.75rem;font-weight:700;color:#15803d;display:flex;align-items:center;gap:0.5rem');
        } else if (status === 'error' || status === 'stale') {
            dot.setAttribute('style', 'width:10px;height:10px;border-radius:50%;background:#ef4444;display:inline-block');
            el.setAttribute('style', 'font-size:0.75rem;font-weight:700;color:#b91c1c;display:flex;align-items:center;gap:0.5rem');
        } else {
            dot.setAttribute('style', 'width:10px;height:10px;border-radius:50%;background:#d6d3d1;display:inline-block');
            el.setAttribute('style', 'font-size:0.75rem;font-weight:700;color:#a8a29e;display:flex;align-items:center;gap:0.5rem');
        }
        while (el.childNodes.length > 1) {
            el.removeChild(el.lastChild);
        }
        el.appendChild(document.createTextNode(' ' + text));
    }

    function applyThreshold(sensor, value) {
        const t = { temp: { max: 40 }, hum: { min: 30 }, tds: { max: 1000 }, ph: { min: 5.5, max: 7.5 } }[sensor] || {};
        const v = safeNum(value);
        if (v === null) return false;
        return (t.max !== undefined && v > t.max) || (t.min !== undefined && v < t.min);
    }

    function updateCard(sensor, value, unit, decimals) {
        var valEl = $('val-' + sensor);
        if (!valEl) return;
        var v = safeNum(value);
        if (v === null) { valEl.textContent = '--'; valEl.classList.remove('text-red-500'); valEl.classList.add('text-stone-800'); return; }
        var critical = applyThreshold(sensor, value);
        valEl.textContent = v.toFixed(decimals);
        if (critical) {
            valEl.classList.remove('text-stone-800');
            valEl.classList.add('text-red-500');
        } else {
            valEl.classList.remove('text-red-500');
            valEl.classList.add('text-stone-800');
        }
    }

    function resetAllCards(msg) {
        ['temp', 'hum', 'soil', 'tds', 'ph'].forEach(function (s) {
            var el = $('val-' + s);
            if (el) { el.textContent = msg || '--'; el.classList.remove('text-red-500'); el.classList.add('text-stone-800'); }
        });
    }

    /* ================================================================
       SENSOR DATA — fetch & display
       ================================================================ */
    function updateDashboard(data) {
        if (!data || typeof data !== 'object' || data.has_data === false) {
            setLiveStatus('error', 'Deconnecte');
            resetAllCards('--');
            return;
        }

        // Vert = connecte et frais ; Rouge = perime ou offline
        if (data.stale_warning) {
            setLiveStatus('error', 'Donnees perimees');
        } else if (data.offline_mode) {
            setLiveStatus('error', 'Deconnecte');
        } else {
            setLiveStatus('online', 'Connecte');
        }

        updateCard('temp', data.temperature, '\u00b0C', 1);
        updateCard('hum', data.humidity, '%', 1);
        updateCard('soil', data.soil_moisture, '%', 0);
        updateCard('tds', data.tds, 'ppm', 0);
        updateCard('ph', data.ph, null, 1);

        // ── Sync irrigation button + mode switch depuis les donnees API ─
        updateIrrigationButton(data.relay, data.mode);
        updateModeButton(data.mode);

        // Alerts API — protection complete null/undefined
        var alerts = [];
        if (data && data.alerts && Array.isArray(data.alerts)) {
            alerts = data.alerts;
        }
        const container = $('alerts-container');
        if (container) {
            if (alerts.length > 0) {
                container.innerHTML = alerts.map(function (a) {
                    if (!a) return '';
                    const cls = a.type === 'critical' ? 'bg-red-50 border-red-200 text-red-700'
                        : a.type === 'warning' ? 'bg-amber-50 border-amber-200 text-amber-700'
                            : 'bg-blue-50 border-blue-200 text-blue-700';
                    return '<div class="px-4 py-3 rounded-xl border ' + cls + ' text-sm font-semibold">' +
                        (a.type === 'critical' ? '\u26a0' : '\u2139') + ' ' + (a.msg || '') + '</div>';
                }).join('');
            } else {
                container.innerHTML = '';
            }
        }
    }

    /* ── Irrigation button sync depuis l'API ───────────────────────── */
    function updateIrrigationButton(relay, mode, force) {
        // Ne pas annuler la mise à jour optimiste pendant 6s (sauf force=true)
        if (!force && Date.now() - lastModeChange < 6000) return;

        var btn  = $('irrigation-btn');
        var dot  = $('irrigation-dot');
        var lbl  = $('irrigation-label');
        if (!btn || !dot || !lbl) return;

        if (!relay || !mode) {
            // Pas de donnee — etat inconnu
            dot.className = 'w-2 h-2 rounded-full bg-stone-300 inline-block';
            lbl.textContent = 'Irrigation --';
            btn.style.background = '#fff';
            btn.style.borderColor = '#e5e7eb';
            btn.style.color = '#6b7280';
            btn.disabled = true;
            btn.style.opacity = '0.5';
            btn.style.cursor = 'not-allowed';
            if (window.irrigationOn !== undefined) window.irrigationOn = false;
            return;
        }

        if (mode === 'AUTO') {
            // Mode AUTO : bouton desactive, pas de forçage manuel
            btn.disabled = true;
            btn.style.opacity = '0.6';
            btn.style.cursor = 'not-allowed';
            if (relay === 'ON') {
                dot.className = 'w-2 h-2 rounded-full bg-sky-500 inline-block';
                lbl.textContent = 'Auto ON';
                btn.style.background = '#f0f9ff';
                btn.style.borderColor = '#7dd3fc';
                btn.style.color = '#0284c7';
            } else {
                dot.className = 'w-2 h-2 rounded-full bg-stone-300 inline-block';
                lbl.textContent = 'Auto OFF';
                btn.style.background = '#f5f5f4';
                btn.style.borderColor = '#d6d3d1';
                btn.style.color = '#78716c';
            }
            if (window.irrigationOn !== undefined) window.irrigationOn = false;
            return;
        }

        // Mode MANUAL : bouton actif, forçage manuel possible
        btn.disabled = false;
        btn.style.opacity = '1';
        btn.style.cursor = 'pointer';
        if (relay === 'ON') {
            dot.className = 'w-2 h-2 rounded-full bg-sky-500 animate-pulse inline-block';
            lbl.textContent = 'Irrigation ON';
            btn.style.background = '#f0f9ff';
            btn.style.borderColor = '#7dd3fc';
            btn.style.color = '#0284c7';
            if (window.irrigationOn !== undefined) window.irrigationOn = true;
        } else {
            dot.className = 'w-2 h-2 rounded-full bg-stone-300 inline-block';
            lbl.textContent = 'Irrigation OFF';
            btn.style.background = '#fff';
            btn.style.borderColor = '#e5e7eb';
            btn.style.color = '#6b7280';
            if (window.irrigationOn !== undefined) window.irrigationOn = false;
        }
    }

    /* ── Mode switch AUTO/MANUAL ─────────────────────────────────── */
    function updateModeButton(mode, force) {
        // Ne pas annuler la mise à jour optimiste pendant 6s (sauf force=true)
        if (!force && Date.now() - lastModeChange < 6000) return;

        var autoBtn   = document.querySelector('.mode-auto');
        var manualBtn = document.querySelector('.mode-manual');
        if (!autoBtn || !manualBtn) return;

        if (mode === 'AUTO') {
            autoBtn.style.background   = '#dcfce7';
            autoBtn.style.color        = '#166534';
            autoBtn.style.fontWeight   = '700';
            manualBtn.style.background = '#fff';
            manualBtn.style.color      = '#a8a29e';
            manualBtn.style.fontWeight = '500';
        } else if (mode === 'MANUAL') {
            manualBtn.style.background = '#fee2e2';
            manualBtn.style.color      = '#991b1b';
            manualBtn.style.fontWeight = '700';
            autoBtn.style.background   = '#fff';
            autoBtn.style.color        = '#a8a29e';
            autoBtn.style.fontWeight   = '500';
        } else {
            // Inconnu — les deux grisés
            autoBtn.style.background   = '#f5f5f4';
            autoBtn.style.color        = '#a8a29e';
            autoBtn.style.fontWeight   = '500';
            manualBtn.style.background = '#f5f5f4';
            manualBtn.style.color      = '#a8a29e';
            manualBtn.style.fontWeight = '500';
        }
    }

    window.updateModeButton = updateModeButton;

    function toggleMode(mode) {
        lastModeChange = Date.now();
        var action = mode === 'auto' ? 'mode_auto' : 'mode_manual';
        fetch('/api/iot/irrigation-control/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRF() },
            body: JSON.stringify({ action: action }),
            credentials: 'same-origin'
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.status === 'ok') {
                updateModeButton(data.mode, true);
                // Forcer la mise à jour immédiate du bouton irrigation
                var dot = document.getElementById('irrigation-dot');
                var relay = dot && dot.classList.contains('bg-sky-500') ? 'ON' : 'OFF';
                updateIrrigationButton(relay, data.mode, true);
            }
        })
        .catch(function(e) { console.error('Mode switch error:', e); });
    }

    window.toggleMode = toggleMode;

    function renderChart(canvasId, data, datasets) {
        const canvas = $(canvasId);
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const key = '_chart_' + canvasId;
        if (window[key]) { window[key].destroy(); window[key] = null; }
        const mapped = datasets.map(function (d, i) {
            const raw = (data.datasets && data.datasets[d.key]) ? data.datasets[d.key] : [];
            return {
                label: d.label, data: Array.isArray(raw) ? raw : [],
                borderColor: d.color, backgroundColor: d.color + '1a',
                fill: true, tension: 0.3, pointRadius: 1, borderWidth: 2,
                yAxisID: i === 0 ? 'y' : 'y1',
            };
        });
        window[key] = new Chart(ctx, {
            type: 'line',
            data: { labels: Array.isArray(data.labels) ? data.labels : [], datasets: mapped },
            options: {
                responsive: true, maintainAspectRatio: false, animation: { duration: 300 },
                plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 10 } } } },
                scales: {
                    y: { grid: { color: '#f0f0f0' } },
                    y1: { position: 'right', grid: { display: false } },
                    x: { grid: { display: false }, ticks: { font: { size: 9 }, maxTicksLimit: 12 } },
                },
            },
        });
    }

    /* ================================================================
       SENSOR CHART + HISTORY TABLE
       ================================================================ */
    function loadChartData() {
        fetch(API.CHART + '?limit=30&t=' + Date.now(), getFetchOpts())
            .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return safeJson(r); })
            .then(function (data) {
                if (!data || !data.labels || !Array.isArray(data.labels) || !data.labels.length) return;
                const tbody = $('table-body');
                if (tbody) {
                    const rows = data.labels.map(function (l, i) {
                        const t = safeNum(data.datasets && data.datasets.temperature ? data.datasets.temperature[i] : null);
                        const h = safeNum(data.datasets && data.datasets.humidity ? data.datasets.humidity[i] : null);
                        const td = safeNum(data.datasets && data.datasets.tds ? data.datasets.tds[i] : null);
                        const p = safeNum(data.datasets && data.datasets.ph ? data.datasets.ph[i] : null);
                        return '<tr class="border-t border-stone-50 hover:bg-stone-50/5">' +
                            '<td class="px-5 py-2.5 text-stone-500 text-xs">' + (l || '') + '</td>' +
                            '<td class="px-5 py-2.5 font-bold ' + (t !== null && t > 35 ? 'text-red-500' : '') + '">' + (t !== null ? t.toFixed(1) : '\u2014') + '\u00b0C</td>' +
                            '<td class="px-5 py-2.5 font-bold">' + (h !== null ? h.toFixed(1) : '\u2014') + '%</td>' +
                            '<td class="px-5 py-2.5 font-bold">' + (td !== null ? td.toFixed(0) : '\u2014') + ' ppm</td>' +
                            '<td class="px-5 py-2.5 font-bold">' + (p !== null ? p.toFixed(1) : '\u2014') + '</td></tr>';
                    });
                    tbody.innerHTML = rows.reverse().join('');
                }
                renderChart('chartTempHum', data, [
                    { label: 'Temperature (\u00b0C)', key: 'temperature', color: '#ef4444' },
                    { label: 'Humidite (%)', key: 'humidity', color: '#3b82f6' },
                ]);
                renderChart('chartTdsPh', data, [
                    { label: 'TDS (ppm)', key: 'tds', color: '#f59e0b' },
                    { label: 'pH', key: 'ph', color: '#10b981' },
                ]);
            })
            .catch(function (err) { console.error('[Chart] failed:', err); });
    }

    /* ================================================================
       SENSOR AUTO-REFRESH (toutes les 5s) + BOUTON MANUEL
       ================================================================ */
    function refreshSensors() {
        try {
            console.log('[Dashboard] refreshSensors appelé — iteration ' + (++refreshSensors._count));
            fetch('/api/iot/sensor-latest/?t=' + new Date().getTime(), {
                method: 'GET',
                headers: { 'Accept': 'application/json', 'Cache-Control': 'no-cache', 'Pragma': 'no-cache' },
                credentials: 'same-origin',
                cache: 'no-store',
            })
                .then(function (r) {
                    console.log('[Dashboard] Reponse API :', r.status, r.statusText);
                    if (r.status === 404) {
                        console.error('[Dashboard] 404 — route API introuvable :', API.LATEST);
                    }
                    if (!r.ok) throw new Error('HTTP ' + r.status);
                    return safeJson(r);
                })
                .then(function (data) {
                    console.log('[Dashboard] RAW API response:', JSON.stringify(data));
                    return data;
                })
                .then(updateDashboard)
            .catch(function (err) {
                console.error('[Dashboard] fetchLatest failed:', err.message || err);
                setLiveStatus('error', 'Deconnecte');
                resetAllCards('--');
                var container = document.getElementById('alerts-container');
                if (container) {
                    container.innerHTML = '<div class="px-4 py-3 rounded-xl border bg-red-50 border-red-200 text-red-700 text-sm font-semibold">' +
                        '\u26a0 Impossible de joindre l\'API capteurs. Verifiez que le serveur est en ligne sur http://127.0.0.1:8000</div>';
                }
            });
            loadChartData();
        } catch (e) {
            console.error('[Dashboard] refreshSensors erreur bloquante:', e.message || e);
        }
    }
    refreshSensors._count = 0;

    function refreshSensorData() {
        console.log('[Dashboard] Rafraichissement manuel declenche...');
        refreshSensors();
    }

    window.refreshSensorData = refreshSensorData;

    /* ================================================================
       PLANT ANALYSIS — upload + result display
       ================================================================ */
    function loadPlantHistory() {
        fetch(API.SCANS + '?limit=10&t=' + Date.now(), getFetchOpts())
            .then(safeJsonOrNull)
            .then(function (data) {
                const tbody = $('plant-history-body');
                if (!tbody || !data || !data.results || !data.results.length) return;
                tbody.innerHTML = data.results.map(function (s) {
                    const cls = s.severity === 'critical' ? 'bg-red-100 text-red-700'
                        : s.severity === 'warning' ? 'bg-amber-100 text-amber-700'
                            : 'bg-green-100 text-green-700';
                    return '<tr class="border-t border-stone-50 hover:bg-stone-50/5">' +
                        '<td class="px-5 py-2.5 text-stone-500 text-xs">' + (s.scanned_at || '') + '</td>' +
                        '<td class="px-5 py-2.5 font-bold text-stone-700">' + (s.disease_name || '\u2014') + '</td>' +
                        '<td class="px-5 py-2.5 font-bold text-stone-700">' + (s.confidence != null ? s.confidence.toFixed(1) + '%' : '\u2014') + '</td>' +
                        '<td class="px-5 py-2.5"><span class="px-2 py-0.5 rounded-lg text-xs font-bold ' + cls + '">' + (s.severity || '\u2014') + '</span></td></tr>';
                }).join('');
            })
            .catch(function (err) { console.warn('[Plant history] failed:', err); });
    }

    function handlePlantFile(file) {
        selectedPlantFile = file;
        $('plant-drop-text').textContent = file.name;
        const reader = new FileReader();
        reader.onload = function (e) {
            const img = $('plant-preview');
            img.src = e.target.result;
            img.classList.remove('hidden');
            $('plant-drop-zone').classList.add('hidden');
            $('plant-analyze-btn').classList.remove('hidden');
            $('plant-analyze-btn').disabled = false;
        };
        reader.readAsDataURL(file);
    }

    function submitPlantImage() {
        if (!selectedPlantFile) return;
        const progress = $('plant-progress');
        const btn = $('plant-analyze-btn');
        const resultEmpty = $('plant-result-empty');
        const resultContent = $('plant-result-content');
        progress.classList.remove('hidden');
        btn.disabled = true;

        const formData = new FormData();
        formData.append('image', selectedPlantFile);
        formData.append('lang', 'fr');

        fetch(API.UPLOAD, { method: 'POST', credentials: 'same-origin', body: formData })
            .then(safeJson)
            .then(function (data) {
                progress.classList.add('hidden');
                resultEmpty.classList.add('hidden');
                resultContent.classList.remove('hidden');
                $('plant-disease-name').textContent = data.disease || data.disease_name || '\u2014';
                $('plant-confidence').textContent = (data.confidence != null ? data.confidence.toFixed(1) + '%' : '\u2014');
                const sev = data.severity || 'warning';
                const badge = $('plant-severity-badge');
                const cls = sev === 'critical' ? 'bg-red-500 text-white' : sev === 'normal' ? 'bg-green-500 text-white' : 'bg-amber-500 text-white';
                badge.className = 'inline-block px-3 py-1 rounded-lg text-xs font-bold ' + cls;
                badge.textContent = sev.toUpperCase();
                $('plant-advice').textContent = data.advice || data.watering_advice || '\u2014';
                const alertEl = $('plant-alert-critical');
                if (sev === 'critical') alertEl.classList.remove('hidden'); else alertEl.classList.add('hidden');
                loadPlantHistory();
                // Show reset button, hide analyze button
                btn.classList.add('hidden');
                var resetBtn = $('plant-reset-btn');
                if (resetBtn) resetBtn.classList.remove('hidden');
            })
            .catch(function (err) {
                console.error('[Plant] failed:', err);
                progress.classList.add('hidden');
                btn.disabled = false;
            });
    }

    function initPlantPanel() {
        const dropZone = $('plant-drop-zone');
        const fileInput = $('plant-image-input');
        if (!dropZone || !fileInput) return;
        dropZone.addEventListener('click', function () { fileInput.click(); });
        dropZone.addEventListener('dragover', function (e) { e.preventDefault(); dropZone.classList.add('border-emerald-400'); });
        dropZone.addEventListener('dragleave', function () { dropZone.classList.remove('border-emerald-400'); });
        dropZone.addEventListener('drop', function (e) {
            e.preventDefault();
            dropZone.classList.remove('border-emerald-400');
            const file = e.dataTransfer.files[0];
            if (file && file.type.startsWith('image/')) handlePlantFile(file);
        });
        fileInput.addEventListener('change', function () {
            if (this.files[0]) handlePlantFile(this.files[0]);
        });
    }

    window.submitPlantImage = submitPlantImage;

    function resetPlantForm() {
        $('plant-disease-name').textContent = '\u2014';
        $('plant-confidence').textContent = '\u2014';
        $('plant-advice').textContent = '\u2014';
        var badge = $('plant-severity-badge');
        badge.className = 'inline-block px-3 py-1 rounded-lg text-xs font-bold';
        badge.textContent = '\u2014';
        $('plant-alert-critical').classList.add('hidden');
        $('plant-result-content').classList.add('hidden');
        $('plant-result-empty').classList.remove('hidden');
        var preview = $('plant-preview');
        preview.classList.add('hidden');
        preview.src = '';
        $('plant-image-input').value = '';
        selectedPlantFile = null;
        $('plant-drop-text').textContent = 'Cliquez ou glissez une image ici';
        // Show analyze btn (disabled), hide reset btn
        $('plant-analyze-btn').classList.remove('hidden');
        $('plant-analyze-btn').disabled = true;
        var resetBtn = $('plant-reset-btn');
        if (resetBtn) resetBtn.classList.add('hidden');
    }
    window.resetPlantForm = resetPlantForm;

    /* ================================================================
       ESP32-CAM — polling de la derniere capture envoyee par POST
       L'ESP32-CAM envoie UNE photo JPEG multipart/form-data vers
       /api/upload/ a intervalle regulier. Le serveur stocke + analyse.
       Le dashboard interroge /api/iot/latest-capture/ periodiquement.
       ================================================================ */
    let lastCaptureId = 0;

    function loadLatestCapture(force) {
        fetch('/api/iot/latest-capture/?t=' + Date.now(), getFetchOpts())
            .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return safeJson(r); })
            .then(function (data) {
                const img       = $('espcam-image');
                const ph        = $('espcam-placeholder');
                const status    = $('espcam-status');
                const dot       = $('espcam-dot');
                const lastCap   = $('espcam-last-capture');
                const refresh   = $('espcam-refresh-info');

                if (!data.has_capture) {
                    if (img) img.classList.add('hidden');
                    if (ph) ph.classList.remove('hidden');
                    if (status) { status.textContent = 'En attente...'; status.className = 'text-xs font-semibold text-stone-400'; }
                    if (dot) dot.className = 'w-2 h-2 rounded-full bg-stone-300 inline-block';
                    return;
                }

                // Only update if new capture or forced refresh
                if (data.id === lastCaptureId && !force) return;
                lastCaptureId = data.id;

                // Show image
                if (img && data.image_url) {
                    img.src = data.image_url + '?t=' + Date.now();
                    img.classList.remove('hidden');
                    img.onerror = function () { img.classList.add('hidden'); if (ph) ph.classList.remove('hidden'); };
                    if (ph) ph.classList.add('hidden');
                }

                // Status
                const scanned = data.scanned_at ? new Date(data.scanned_at) : null;
                if (status) {
                    if (scanned) {
                        const ageSec = Math.floor((Date.now() - scanned.getTime()) / 1000);
                        const fresh  = ageSec < 120; // 2 min
                        status.textContent = fresh ? 'Actif (capture recente)' : 'En veille (' + ageSec + 's)';
                        status.className   = 'text-xs font-semibold ' + (fresh ? 'text-green-700' : 'text-amber-700');
                    } else {
                        status.textContent = 'Actif';
                        status.className   = 'text-xs font-semibold text-green-700';
                    }
                }
                if (dot) dot.className = 'w-2 h-2 rounded-full bg-green-500 inline-block animate-pulse';

                // Timestamp
                if (lastCap && scanned) {
                    lastCap.textContent = 'Capture: ' + scanned.toLocaleString();
                }
                if (refresh) {
                    refresh.textContent = 'Rafraichi auto (10s)';
                }

                // AI result
                $('espcam-result-empty').classList.add('hidden');
                $('espcam-result-content').classList.remove('hidden');
                $('espcam-disease').textContent = data.disease_name || '---';
                $('espcam-confidence').textContent = (data.confidence != null ? data.confidence.toFixed(1) + '%' : '---');
                const sev       = data.severity || 'normal';
                const sevBadge  = $('espcam-severity-badge');
                if (sevBadge) {
                    const cls = sev === 'critical' ? 'bg-red-500 text-white' : sev === 'normal' ? 'bg-green-500 text-white' : 'bg-amber-500 text-white';
                    sevBadge.className = 'inline-block px-3 py-1 rounded-lg text-xs font-bold ' + cls;
                    sevBadge.textContent = sev.toUpperCase();
                }
                $('espcam-advice').textContent = data.watering_advice || '---';
            })
            .catch(function (err) {
                console.error('[ESP32-CAM] API failed:', err);
                const status = $('espcam-status');
                if (status) { status.textContent = 'API injoignable'; status.className = 'text-xs font-semibold text-red-500'; }
            });
    }

    window.loadLatestCapture = loadLatestCapture;

    /* ================================================================
       EXPORT — server-side CSV + client-side CSV from table
       ================================================================ */
    window.downloadSensorCsv = function () {
        const from = ($('export-from') || {}).value || '';
        const to = ($('export-to') || {}).value || '';
        let url = API.EXPORT;
        const params = [];
        if (from) params.push('from=' + encodeURIComponent(from));
        if (to) params.push('to=' + encodeURIComponent(to));
        if (params.length) url += '?' + params.join('&');
        const link = document.createElement('a');
        link.href = url;
        link.download = 'sensor_data' + (from ? '_' + from : '') + (to ? '_' + to : '') + '.csv';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    window.downloadPlantsCsv = function () {
        window.open(API.SCANS_EXPORT + '?t=' + Date.now(), '_blank');
    };

    // Export client-side CSV from visible table rows
    window.downloadTableCsv = function () {
        const tbody = $('table-body');
        if (!tbody) return;
        const rows = tbody.querySelectorAll('tr');
        let csv = 'Date,Temperature,Humidite,TDS,pH\n';
        rows.forEach(function (row) {
            const cells = row.querySelectorAll('td');
            if (cells.length >= 5) {
                csv += [cells[0].textContent, cells[1].textContent, cells[2].textContent, cells[3].textContent, cells[4].textContent]
                    .map(function (c) { return '"' + c.replace(/"/g, '""') + '"'; }).join(',') + '\n';
            }
        });
        const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = 'historique_capteurs_' + new Date().toISOString().slice(0, 10) + '.csv';
        link.click();
        URL.revokeObjectURL(url);
    };

    /* ================================================================
       INIT — tout demarre ici
       ================================================================ */
    function init() {
        initTabs();
        initPlantPanel();
        console.log('[Dashboard] Init: demarrage polling ' + POLL_INTERVAL + 'ms');
        refreshSensors();  // chargement initial capteurs
        setInterval(refreshSensors, POLL_INTERVAL);  // polling auto capteurs toutes les 5s
        setInterval(loadChartData, CHART_INTERVAL);
        console.log('[Dashboard] Init: setInterval enregistré, ID polling ~' + (setInterval(function(){}, 99999) - 1));
        loadPlantHistory();
        loadLatestCapture();
        setInterval(function () { loadLatestCapture(); }, 10000);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();