/**
 * NeuroUrja — Frontend Command Center Controller
 * Manages:
 *  - Real-time WebSocket streaming with REST fallback
 *  - 60 FPS HTML5 Canvas Synaptic Conduit & Power Flow particle physics
 *  - Live Neuromorphic LIF Oscilloscope waveform rendering
 *  - Interactive Control Deck sliders & Chaos Scenario execution
 *  - Immutable Blockchain Audit Ledger & Agent Dialogue feeds
 */

// Global State
let telemetryData = null;
let socket = null;
let simulationSpeed = 1.0;
let isTransferActive = true;
let currentTransferredKw = 65.0;

// Oscilloscope History Buffer
const OSCILLOSCOPE_POINTS = 160;
let hostelPotentialHistory = new Array(OSCILLOSCOPE_POINTS).fill(0.12);
let academicPotentialHistory = new Array(OSCILLOSCOPE_POINTS).fill(-0.15);

// Particle Physics for Synaptic Conduit & Microgrid Power Flow
let powerParticles = [];
let synapticSpikeParticles = [];

class PowerParticle {
  constructor(canvasWidth) {
    this.x = Math.random() * canvasWidth;
    this.speed = 1.8 + Math.random() * 2.2;
    this.size = 2.5 + Math.random() * 2.5;
    this.alpha = 0.5 + Math.random() * 0.5;
    this.pulse = Math.random() * Math.PI;
  }

  update(width, active, kw) {
    if (!active || kw <= 0) {
      this.speed = 0.4;
      this.alpha = 0.25;
    } else {
      this.speed = 1.5 + (kw / 75.0) * 3.5;
      this.alpha = 0.7 + Math.sin(this.pulse) * 0.3;
    }
    this.pulse += 0.08;
    this.x += this.speed;
    if (this.x > width) {
      this.x = 0;
    }
  }

  draw(ctx, height, active) {
    ctx.save();
    ctx.beginPath();
    ctx.arc(this.x, height / 2 + (Math.sin(this.pulse * 2) * 5), this.size, 0, Math.PI * 2);
    ctx.fillStyle = active ? `rgba(16, 185, 129, ${this.alpha})` : `rgba(148, 163, 184, ${this.alpha})`;
    ctx.shadowColor = active ? 'rgba(16, 185, 129, 0.8)' : 'transparent';
    ctx.shadowBlur = active ? 8 : 0;
    ctx.fill();
    ctx.restore();
  }
}

class SynapticSpikeParticle {
  constructor(dir, width) {
    // dir: 1 (left to right, surplus spike) or -1 (right to left, deficit spike)
    this.dir = dir;
    this.x = dir === 1 ? 20 : width - 20;
    this.speed = 4.2;
    this.size = 5.0;
    this.color = dir === 1 ? '#059669' : '#D97706';
    this.done = false;
  }

  update(width) {
    this.x += this.dir * this.speed;
    if (this.dir === 1 && this.x >= width / 2) this.done = true;
    if (this.dir === -1 && this.x <= width / 2) this.done = true;
  }

  draw(ctx, height) {
    ctx.save();
    ctx.beginPath();
    ctx.arc(this.x, height / 2, this.size, 0, Math.PI * 2);
    ctx.fillStyle = this.color;
    ctx.shadowColor = this.color;
    ctx.shadowBlur = 10;
    ctx.fill();
    ctx.restore();
  }
}

// Initialize Canvases
function initCanvases() {
  const pCanvas = document.getElementById('powerFlowCanvas');
  const sCanvas = document.getElementById('synapticCanvas');
  const oCanvas = document.getElementById('oscilloscopeCanvas');

  function resizeCanvas(c) {
    if (!c) return;
    const rect = c.parentElement.getBoundingClientRect();
    c.width = rect.width * window.devicePixelRatio;
    c.height = rect.height * window.devicePixelRatio;
    const ctx = c.getContext('2d');
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
  }

  resizeCanvas(pCanvas);
  resizeCanvas(sCanvas);
  resizeCanvas(oCanvas);

  // Seed power particles
  const w = pCanvas.getBoundingClientRect().width;
  powerParticles = [];
  for (let i = 0; i < 35; i++) {
    powerParticles.push(new PowerParticle(w));
  }

  window.addEventListener('resize', () => {
    resizeCanvas(pCanvas);
    resizeCanvas(sCanvas);
    resizeCanvas(oCanvas);
  });
}

// 60 FPS Render Loop for Hero Canvases
let handshakeFlash = 0;
function renderConduits() {
  const pCanvas = document.getElementById('powerFlowCanvas');
  const sCanvas = document.getElementById('synapticCanvas');

  if (pCanvas && sCanvas) {
    const pRect = pCanvas.getBoundingClientRect();
    const pCtx = pCanvas.getContext('2d');
    pCtx.clearRect(0, 0, pRect.width, pRect.height);

    // Draw Microgrid Bus Track
    pCtx.save();
    pCtx.strokeStyle = '#E2E8F0';
    pCtx.lineWidth = 4;
    pCtx.lineCap = 'round';
    pCtx.beginPath();
    pCtx.moveTo(15, pRect.height / 2);
    pCtx.lineTo(pRect.width - 15, pRect.height / 2);
    pCtx.stroke();

    // Active power flow gradient bar
    if (isTransferActive) {
      const grad = pCtx.createLinearGradient(15, 0, pRect.width - 15, 0);
      grad.addColorStop(0, 'rgba(16, 185, 129, 0.4)');
      grad.addColorStop(0.5, 'rgba(16, 185, 129, 0.85)');
      grad.addColorStop(1, 'rgba(245, 158, 11, 0.4)');
      pCtx.strokeStyle = grad;
      pCtx.lineWidth = 3;
      pCtx.stroke();
    }
    pCtx.restore();

    // Render power particles
    powerParticles.forEach(p => {
      p.update(pRect.width, isTransferActive, currentTransferredKw);
      p.draw(pCtx, pRect.height, isTransferActive);
    });

    // Render Synaptic Axon Channel
    const sRect = sCanvas.getBoundingClientRect();
    const sCtx = sCanvas.getContext('2d');
    sCtx.clearRect(0, 0, sRect.width, sRect.height);

    // Draw Axon Fiber
    sCtx.save();
    sCtx.strokeStyle = '#E2E8F0';
    sCtx.lineWidth = 3;
    sCtx.setLineDash([6, 4]);
    sCtx.beginPath();
    sCtx.moveTo(15, sRect.height / 2);
    sCtx.lineTo(sRect.width - 15, sRect.height / 2);
    sCtx.stroke();
    sCtx.restore();

    // Periodic synaptic spike spawn
    if (Math.random() < 0.03 && isTransferActive) {
      synapticSpikeParticles.push(new SynapticSpikeParticle(1, sRect.width));
      synapticSpikeParticles.push(new SynapticSpikeParticle(-1, sRect.width));
    }

    // Update and draw synaptic spike particles
    for (let i = synapticSpikeParticles.length - 1; i >= 0; i--) {
      const spk = synapticSpikeParticles[i];
      spk.update(sRect.width);
      spk.draw(sCtx, sRect.height);
      if (spk.done) {
        handshakeFlash = 1.0;
        synapticSpikeParticles.splice(i, 1);
      }
    }

    // Draw Center Handshake Node
    sCtx.save();
    const midX = sRect.width / 2;
    const midY = sRect.height / 2;
    sCtx.beginPath();
    sCtx.arc(midX, midY, 9, 0, Math.PI * 2);
    sCtx.fillStyle = '#2563EB';
    sCtx.shadowColor = '#2563EB';
    sCtx.shadowBlur = 12 * (handshakeFlash + 0.4);
    sCtx.fill();

    // Icon or center ring
    sCtx.beginPath();
    sCtx.arc(midX, midY, 15 + (1 - handshakeFlash) * 5, 0, Math.PI * 2);
    sCtx.strokeStyle = `rgba(37, 99, 235, ${0.8 * handshakeFlash})`;
    sCtx.lineWidth = 2;
    sCtx.stroke();
    sCtx.restore();

    if (handshakeFlash > 0) {
      handshakeFlash = Math.max(0, handshakeFlash - 0.03);
    }
  }

  requestAnimationFrame(renderConduits);
}

// 60 FPS Oscilloscope Waveform Renderer
function renderOscilloscope() {
  const oCanvas = document.getElementById('oscilloscopeCanvas');
  if (!oCanvas) return;

  const rect = oCanvas.getBoundingClientRect();
  const ctx = oCanvas.getContext('2d');
  ctx.clearRect(0, 0, rect.width, rect.height);

  const w = rect.width;
  const h = rect.height;
  const midY = h / 2;
  const scaleY = (h / 2) * 0.75; // -1.0 is at midY + scaleY, +1.0 at midY - scaleY

  // 1. Draw Grid Lines
  ctx.save();
  ctx.strokeStyle = '#F1F5F9';
  ctx.lineWidth = 1;
  const gridStep = 30;
  for (let x = 0; x < w; x += gridStep) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, h);
    ctx.stroke();
  }
  for (let y = 0; y < h; y += gridStep) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(w, y);
    ctx.stroke();
  }

  // 2. Draw Threshold Lines (+1.0 and -1.0)
  ctx.strokeStyle = 'rgba(220, 38, 38, 0.45)';
  ctx.lineWidth = 1.5;
  ctx.setLineDash([5, 4]);

  // +1.0 Threshold Line
  ctx.beginPath();
  ctx.moveTo(0, midY - scaleY);
  ctx.lineTo(w, midY - scaleY);
  ctx.stroke();

  // -1.0 Threshold Line
  ctx.beginPath();
  ctx.moveTo(0, midY + scaleY);
  ctx.lineTo(w, midY + scaleY);
  ctx.stroke();

  // Baseline 0.0 Rest Potential
  ctx.strokeStyle = 'rgba(148, 163, 184, 0.4)';
  ctx.setLineDash([2, 2]);
  ctx.beginPath();
  ctx.moveTo(0, midY);
  ctx.lineTo(w, midY);
  ctx.stroke();
  ctx.restore();

  // Labels for Thresholds
  ctx.save();
  ctx.font = '10px "JetBrains Mono"';
  ctx.fillStyle = '#DC2626';
  ctx.fillText('+V_th (+1.0) SURPLUS TRIGGER', 8, midY - scaleY - 5);
  ctx.fillText('-V_th (-1.0) DEFICIT TRIGGER', 8, midY + scaleY + 12);
  ctx.fillStyle = '#64748B';
  ctx.fillText('0.0 REST', 8, midY - 4);
  ctx.restore();

  // 3. Draw Building A (Hostel) Waveform (Emerald)
  drawWaveformLine(ctx, hostelPotentialHistory, '#059669', w, midY, scaleY, 2.5);

  // 4. Draw Building B (Academic) Waveform (Amber)
  drawWaveformLine(ctx, academicPotentialHistory, '#D97706', w, midY, scaleY, 2.5);

  // Current Potential Indicators at Right Edge
  const currHostel = hostelPotentialHistory[hostelPotentialHistory.length - 1] || 0;
  const currAcad = academicPotentialHistory[academicPotentialHistory.length - 1] || 0;

  drawProbePoint(ctx, w - 8, midY - (currHostel * scaleY), '#059669', `V_A: ${currHostel >= 0 ? '+' : ''}${currHostel.toFixed(2)}`);
  drawProbePoint(ctx, w - 8, midY - (currAcad * scaleY), '#D97706', `V_B: ${currAcad >= 0 ? '+' : ''}${currAcad.toFixed(2)}`);

  requestAnimationFrame(renderOscilloscope);
}

function drawWaveformLine(ctx, data, color, width, midY, scaleY, lineWidth) {
  if (data.length < 2) return;
  ctx.save();
  ctx.beginPath();
  ctx.strokeStyle = color;
  ctx.lineWidth = lineWidth;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';

  const dx = width / (data.length - 1);
  for (let i = 0; i < data.length; i++) {
    const px = i * dx;
    const py = midY - (data[i] * scaleY);
    if (i === 0) ctx.moveTo(px, py);
    else ctx.lineTo(px, py);
  }
  ctx.stroke();
  ctx.restore();
}

function drawProbePoint(ctx, x, y, color, label) {
  ctx.save();
  ctx.beginPath();
  ctx.arc(x, y, 4.5, 0, Math.PI * 2);
  ctx.fillStyle = color;
  ctx.shadowColor = color;
  ctx.shadowBlur = 8;
  ctx.fill();

  ctx.font = 'bold 10px "JetBrains Mono"';
  ctx.fillStyle = color;
  ctx.fillText(label, x - 75, y - 6);
  ctx.restore();
}

// Telemetry Processor & UI State Synchronization
function updateUI(data) {
  telemetryData = data;
  const campus = data.campus_summary || {};
  const bldg = data.buildings || {};
  const coord = data.coordinator || {};
  const activeTx = coord.active_transfer;

  // 1. Uniqueness Pillars Ribbon
  const dormVal = document.getElementById('pillarDormancyVal');
  if (dormVal) dormVal.textContent = `${campus.avg_dormancy_rate || 94.2}%`;

  const transVal = document.getElementById('pillarTransferVal');
  if (transVal) {
    if (activeTx && activeTx.transferred_kw > 0) {
      transVal.textContent = `${activeTx.transferred_kw.toFixed(1)} kW`;
      isTransferActive = true;
      currentTransferredKw = activeTx.transferred_kw;
    } else {
      transVal.textContent = `0.0 kW (Idle)`;
      isTransferActive = false;
      currentTransferredKw = 0;
    }
  }

  // 2. Active Transfer Pill & Center Channel
  const transferPillText = document.getElementById('transferPillText');
  const powerKwDisplay = document.getElementById('powerKwDisplay');
  const synapseStatusBadge = document.getElementById('synapseStatusBadge');

  if (activeTx && activeTx.status === 'SYNAPTIC_STREAMING') {
    if (transferPillText) {
      transferPillText.textContent = `⚡ ${activeTx.transferred_kw.toFixed(1)} kW Clean Transfer Active • ₹${activeTx.cost_saved_per_hour_inr}/hr Saved`;
    }
    if (powerKwDisplay) powerKwDisplay.textContent = `⚡ ${activeTx.transferred_kw.toFixed(1)} kW Flow`;
    if (synapseStatusBadge) {
      synapseStatusBadge.textContent = 'SYNAPSE ENGAGED (65 kW)';
      synapseStatusBadge.style.background = 'var(--donor-surface)';
      synapseStatusBadge.style.color = 'var(--donor-emerald)';
    }
  } else {
    if (transferPillText) {
      transferPillText.textContent = `💤 Microgrid Dormant (0 W Compute Overhead) • Agents Asleep`;
    }
    if (powerKwDisplay) powerKwDisplay.textContent = `⚡ 0.0 kW Bus Rest`;
    if (synapseStatusBadge) {
      synapseStatusBadge.textContent = 'DORMANT (MONITORING)';
      synapseStatusBadge.style.background = 'var(--bg-subtle)';
      synapseStatusBadge.style.color = 'var(--text-tertiary)';
    }
  }

  // 3. Building A (Hostel) Telemetry
  const hostel = bldg['bldg-hostel-a'];
  if (hostel && hostel.inputs) {
    const inp = hostel.inputs;
    document.getElementById('hostelSolarVal').textContent = `${inp.solar_generation_kw.toFixed(1)} kW`;
    document.getElementById('hostelLoadVal').textContent = `${inp.current_load_kw.toFixed(1)} kW`;
    document.getElementById('hostelOccVal').textContent = `${inp.occupancy_count} / ${inp.max_capacity} (${((inp.occupancy_count / inp.max_capacity) * 100).toFixed(0)}%)`;
    const surplus = inp.solar_generation_kw - inp.current_load_kw;
    document.getElementById('hostelSurplusVal').textContent = `${surplus >= 0 ? '+' : ''}${surplus.toFixed(1)} kW`;
    document.getElementById('hostelSocText').textContent = `${inp.battery_soc_percent.toFixed(1)}% (${inp.battery_soc_percent > 85 ? 'Full' : 'Normal'})`;
    document.getElementById('hostelSocBar').style.width = `${inp.battery_soc_percent}%`;

    // Push into oscilloscope buffer
    hostelPotentialHistory.push(hostel.v_m);
    if (hostelPotentialHistory.length > OSCILLOSCOPE_POINTS) hostelPotentialHistory.shift();
  }

  // 4. Building B (Academic Block) Telemetry
  const acad = bldg['bldg-academic-b'];
  if (acad && acad.inputs) {
    const inp = acad.inputs;
    document.getElementById('acadSolarVal').textContent = `${inp.solar_generation_kw.toFixed(1)} kW`;
    document.getElementById('acadLoadVal').textContent = `${inp.current_load_kw.toFixed(1)} kW`;
    document.getElementById('acadOccVal').textContent = `${inp.occupancy_count} / ${inp.max_capacity} (${((inp.occupancy_count / inp.max_capacity) * 100).toFixed(0)}%)`;
    document.getElementById('acadTempVal').textContent = `${inp.target_temp_c.toFixed(1)}°C`;
    document.getElementById('acadSocText').textContent = `${inp.battery_soc_percent.toFixed(1)}% (${inp.battery_soc_percent < 20 ? 'Critical Low' : 'Normal'})`;
    document.getElementById('acadSocBar').style.width = `${inp.battery_soc_percent}%`;

    // Push into oscilloscope buffer
    academicPotentialHistory.push(acad.v_m);
    if (academicPotentialHistory.length > OSCILLOSCOPE_POINTS) academicPotentialHistory.shift();
  }

  // 5. Update Agent Dialog Feed
  renderAgentDialog(coord.recent_messages || []);

  // 6. Update Security Audit Ledger Feed
  renderAuditLedger(data.recent_audits || []);
}

// Render Agent Dialogue Feed
function renderAgentDialog(messages) {
  const container = document.getElementById('agentDialogFeed');
  if (!container) return;

  // Preserve user scroll if scrolled up
  const isScrolledToBottom = container.scrollHeight - container.clientHeight <= container.scrollTop + 40;

  container.innerHTML = messages.map(msg => {
    let agentClass = 'agent-grid';
    let agentDisplayName = msg.sender_name || 'Agent';

    if (msg.sender_agent.includes('hostel')) agentClass = 'agent-hostel';
    else if (msg.sender_agent.includes('acad')) agentClass = 'agent-academic';
    else if (msg.sender_agent.includes('cryo')) agentClass = 'agent-cryo';
    else if (msg.sender_agent.includes('security') || msg.sender_agent.includes('firewall')) agentClass = 'agent-security';

    return `
      <div class="dialog-msg">
        <div class="dialog-msg-header">
          <span class="dialog-agent-badge ${agentClass}">
            <span class="agent-dot"></span>
            ${agentDisplayName}
          </span>
          <span class="dialog-timestamp">${msg.timestamp_iso || ''}</span>
        </div>
        <div class="dialog-content">${escapeHtml(msg.content)}</div>
      </div>
    `;
  }).join('');

  if (isScrolledToBottom) {
    container.scrollTop = container.scrollHeight;
  }
}

// Render Immutable Audit Ledger Feed
function renderAuditLedger(audits) {
  const container = document.getElementById('auditLedgerFeed');
  if (!container) return;

  container.innerHTML = audits.map(b => {
    const isAlert = b.status === 'SECURITY_ALERT' || b.status === 'REJECTED';
    const statusClass = isAlert ? 'status-alert' : 'status-approved';
    const shortHash = b.block_hash ? `${b.block_hash.substring(0, 16)}...` : 'genesis';
    const detailNotes = b.details ? (b.details.notes || b.details.message || b.details.reason || JSON.stringify(b.details)) : '';

    return `
      <div class="audit-block-item ${statusClass}">
        <div class="audit-block-header">
          <span class="audit-block-index">#${b.block_index} • ${b.event_type}</span>
          <span class="audit-status-badge">${b.status}</span>
        </div>
        <div class="audit-hash-row">
          <span>SHA-256: <code>${shortHash}</code></span>
          <span>• ${b.timestamp_iso || ''}</span>
        </div>
        <div class="audit-details-text">${escapeHtml(detailNotes)}</div>
      </div>
    `;
  }).reverse().join('');
}

// Toast Notifications
function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = 'toast';
  
  let iconName = 'info';
  if (type === 'success') iconName = 'check-circle';
  if (type === 'alert') iconName = 'shield-alert';
  if (type === 'spike') iconName = 'zap';

  toast.innerHTML = `<i data-lucide="${iconName}" style="width: 18px; height: 18px;"></i> <span>${escapeHtml(message)}</span>`;
  container.appendChild(toast);
  
  if (window.lucide) window.lucide.createIcons();

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4500);
}

// Escape HTML helper
function escapeHtml(str) {
  if (!str) return '';
  return str.toString()
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// Scenario Triggers
function setupScenarioButtons() {
  const btnNormal = document.getElementById('btnNormalMidday');
  const btnSurge = document.getElementById('btnSurgeCloudburst');
  const btnAttack = document.getElementById('btnSpoofedAttack');

  if (btnNormal) {
    btnNormal.addEventListener('click', async () => {
      try {
        const res = await fetch('/api/scenarios/normal', { method: 'POST' });
        const json = await res.json();
        showToast("Scenario: Normal Midday — Sensor noise leaks away (beta=0.88). Agents sleep.", "success");
        // Update slider values in UI
        document.getElementById('sliderDemand').value = 45;
        document.getElementById('valSliderDemand').textContent = '45 kW';
        document.getElementById('sliderOcc').value = 120;
        document.getElementById('valSliderOcc').textContent = '120 p';
        document.getElementById('sliderSolar').value = 82;
        document.getElementById('valSliderSolar').textContent = '82 kW';
        document.getElementById('sliderSoc').value = 60;
        document.getElementById('valSliderSoc').textContent = '60%';
      } catch (err) {
        console.error(err);
      }
    });
  }

  if (btnSurge) {
    btnSurge.addEventListener('click', async () => {
      try {
        const res = await fetch('/api/scenarios/surge', { method: 'POST' });
        const json = await res.json();
        showToast("Action Spikes Fired! P2P Handshake: 65.0 kW Synaptic Transfer Active.", "spike");
        // Update slider values in UI
        document.getElementById('sliderDemand').value = 115;
        document.getElementById('valSliderDemand').textContent = '115 kW';
        document.getElementById('sliderOcc').value = 480;
        document.getElementById('valSliderOcc').textContent = '480 p';
        document.getElementById('sliderSolar').value = 85;
        document.getElementById('valSliderSolar').textContent = '85 kW';
        document.getElementById('sliderSoc').value = 14;
        document.getElementById('valSliderSoc').textContent = '14%';
      } catch (err) {
        console.error(err);
      }
    });
  }

  if (btnAttack) {
    btnAttack.addEventListener('click', async () => {
      try {
        const res = await fetch('/api/scenarios/attack', { method: 'POST' });
        const json = await res.json();
        showToast("SECURITY GUARDRAIL INTERLOCK: Forged HMAC & 140 kW Cable Overload BLOCKED!", "alert");
      } catch (err) {
        console.error(err);
      }
    });
  }
}

// 4-Input Control Deck Sliders Binding
let sliderDebounceTimer = null;
function setupSliders() {
  const sliderDemand = document.getElementById('sliderDemand');
  const sliderOcc = document.getElementById('sliderOcc');
  const sliderSolar = document.getElementById('sliderSolar');
  const sliderSoc = document.getElementById('sliderSoc');

  function onSliderChange() {
    clearTimeout(sliderDebounceTimer);
    sliderDebounceTimer = setTimeout(async () => {
      const demandVal = parseFloat(sliderDemand.value);
      const occVal = parseInt(sliderOcc.value);
      const solarVal = parseFloat(sliderSolar.value);
      const socVal = parseFloat(sliderSoc.value);

      document.getElementById('valSliderDemand').textContent = `${demandVal} kW`;
      document.getElementById('valSliderOcc').textContent = `${occVal} p`;
      document.getElementById('valSliderSolar').textContent = `${solarVal} kW`;
      document.getElementById('valSliderSoc').textContent = `${socVal}%`;

      // Dispatch updates to Academic Block and Hostel
      await fetch('/api/inputs/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          building_id: 'bldg-academic-b',
          current_load_kw: demandVal,
          occupancy_count: occVal,
          battery_soc_percent: socVal
        })
      });

      await fetch('/api/inputs/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          building_id: 'bldg-hostel-a',
          solar_generation_kw: solarVal
        })
      });
    }, 150);
  }

  [sliderDemand, sliderOcc, sliderSolar, sliderSoc].forEach(s => {
    if (s) {
      s.addEventListener('input', (e) => {
        const id = e.target.id;
        if (id === 'sliderDemand') document.getElementById('valSliderDemand').textContent = `${e.target.value} kW`;
        if (id === 'sliderOcc') document.getElementById('valSliderOcc').textContent = `${e.target.value} p`;
        if (id === 'sliderSolar') document.getElementById('valSliderSolar').textContent = `${e.target.value} kW`;
        if (id === 'sliderSoc') document.getElementById('valSliderSoc').textContent = `${e.target.value}%`;
        onSliderChange();
      });
    }
  });
}

// Simulation Speed Controller Buttons
function setupSpeedButtons() {
  ['1x', '2x', '5x'].forEach(s => {
    const btn = document.getElementById(`speed${s}`);
    if (btn) {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.speed-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const factor = parseFloat(s.replace('x', ''));
        simulationSpeed = factor;
        if (socket && socket.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify({ action: 'SET_SPEED', speed: factor }));
        }
      });
    }
  });
}

// WebSocket Connection with REST Fallback Polling
function connectWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws/telemetry`;

  try {
    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      console.log("[NeuroUrja] WebSocket Synapse Connected");
      showToast("Connected to NeuroUrja Real-Time Synaptic Stream", "success");
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        updateUI(data);
      } catch (err) {
        console.error("JSON parse error:", err);
      }
    };

    socket.onclose = () => {
      console.warn("[NeuroUrja] WebSocket disconnected. Retrying in 2s...");
      setTimeout(connectWebSocket, 2000);
    };

    socket.onerror = () => {
      socket.close();
    };
  } catch (e) {
    console.error("WebSocket setup failed:", e);
    // Fallback polling
    setInterval(async () => {
      try {
        const res = await fetch('/api/telemetry');
        const data = await res.json();
        updateUI(data);
      } catch (err) {}
    }, 1000);
  }
}

// Document Ready Initialization
document.addEventListener('DOMContentLoaded', () => {
  if (window.lucide) window.lucide.createIcons();
  initCanvases();
  setupScenarioButtons();
  setupSliders();
  setupSpeedButtons();
  connectWebSocket();
  renderConduits();
  renderOscilloscope();
});
