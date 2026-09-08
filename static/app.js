let currentRun = null;
let aiConfigured = false;
let currentSourceMode = 'DEMO';
let currentWorkspace = 'mission';
let publicEvidenceLoaded = false;

const $ = (id) => document.getElementById(id);
const API_BASE = String(window.KAIZEN_API_BASE || '').replace(/\/$/, '');
const apiUrl = (path) => `${API_BASE}${path}`;
const pct = (x) => `${(Number(x) * 100).toFixed(2)}%`;
const sec = (x) => `${Number(x).toFixed(1)} s`;
const money = (x) => `$${Number(x).toLocaleString(undefined,{maximumFractionDigits:0})}`;
const num = (x, d=2) => (x === null || x === undefined || Number.isNaN(Number(x))) ? '—' : Number(x).toFixed(d);
const pval = (x) => { if (x === null || x === undefined || Number.isNaN(Number(x))) return '—'; const v=Number(x); return v < 0.0001 ? v.toExponential(2) : v.toFixed(4); };
const ci95 = (x) => Array.isArray(x) && x.length===2 ? `[${num(x[0],3)}, ${num(x[1],3)}]` : '—';
const sourceLabel = (mode) => mode === 'DEMO' ? 'HIDDEN FACTORY' : mode;

function formatApiError(detail, status) {
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const messages = detail.map(item => {
      if (typeof item === 'string') return item;
      const where = Array.isArray(item?.loc) ? item.loc.filter(x => x !== 'body').join('.') : '';
      const msg = item?.msg || 'Invalid input';
      return where ? `${where}: ${msg}` : msg;
    }).filter(Boolean);
    if (messages.length) return messages.join('\n');
  }
  if (detail && typeof detail === 'object') {
    if (typeof detail.message === 'string') return detail.message;
    try { return JSON.stringify(detail); } catch (_) { /* fall through */ }
  }
  return `HTTP ${status}`;
}

async function json(url, opts={}) {
  const res = await fetch(apiUrl(url), opts);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(formatApiError(body.detail, res.status));
  return body;
}

let buildCompatible = false;

function blockForBuildMismatch(message) {
  buildCompatible = false;
  $('health').textContent = message;
  $('health').classList.remove('ok');
  $('health').classList.add('bad');
  const banner = $('buildMismatch');
  if (banner) {
    banner.hidden = false;
    banner.textContent = message + ' — Close old KAIZEN windows/servers and launch this folder again.';
  }
  $('breakBtn').disabled = true;
  $('revealBtn').disabled = true;
  if ($('simulateBtn')) $('simulateBtn').disabled = true;
  if ($('optimizeBtn')) $('optimizeBtn').disabled = true;
  if ($('askAiBtn')) $('askAiBtn').disabled = true;
  if ($('redTeamBtn')) $('redTeamBtn').disabled = true;
  if ($('runProbeBtn')) $('runProbeBtn').disabled = true;
  if ($('freezeHumanBtn')) $('freezeHumanBtn').disabled = true;
  if ($('executeExperimentBtn')) $('executeExperimentBtn').disabled = true;
}

async function checkHealth() {
  try {
    const h = await json('/health');
    const expectedVersion = window.KAIZEN_EXPECTED_VERSION;
    const expectedBuild = window.KAIZEN_EXPECTED_BUILD;
    if (h.version !== expectedVersion || h.build_id !== expectedBuild) {
      blockForBuildMismatch(`BUILD MISMATCH: UI ${expectedVersion}/${expectedBuild} vs API ${h.version}/${h.build_id || 'unknown'}`);
      return;
    }
    buildCompatible = true;
    $('health').textContent = `● ${h.status.toUpperCase()} / ${h.version} · ${h.build_id}`;
    $('health').classList.remove('bad');
    $('health').classList.add('ok');
    const banner = $('buildMismatch');
    if (banner) banner.hidden = true;
    $('breakBtn').disabled = false;
  } catch (e) {
    blockForBuildMismatch(`SYSTEM ERROR: ${e.message}`);
  }
}

async function checkAIStatus() {
  try {
    const data = await json('/api/ai/status');
    const a = data.ai;
    aiConfigured = Boolean(a.configured);
    if ($('aiProvider')) $('aiProvider').textContent = a.provider;
    if ($('aiModel')) $('aiModel').textContent = a.model;
    if ($('aiState')) {
      $('aiState').textContent = aiConfigured ? 'GEMINI READY' : 'GEMINI NOT CONFIGURED';
      $('aiState').classList.toggle('ok', aiConfigured);
    }
    if ($('aiSetup')) {
      $('aiSetup').textContent = aiConfigured
        ? `Gemini connected through ${a.api} · ${a.sdk}. Every answer is forced through KAIZEN engineering tools before it can respond.`
        : 'Gemini integration is installed but no API key is loaded. Copy .env.example to .env, add GEMINI_API_KEY, save, then restart KAIZEN.';
    }
    if ($('askAiBtn')) $('askAiBtn').disabled = !(aiConfigured && currentRun && buildCompatible);
    if ($('redTeamBtn')) $('redTeamBtn').disabled = !(aiConfigured && currentRun && buildCompatible);
  } catch (e) {
    aiConfigured = false;
    if ($('aiState')) $('aiState').textContent = 'GEMINI STATUS ERROR';
    if ($('aiSetup')) $('aiSetup').textContent = `AI status check failed: ${e.message}`;
  }
}

function validateRunInputs() {
  const seed = Number($('seed').value);
  const units = Number($('units').value);
  if (!Number.isInteger(seed) || seed < 0 || seed > 2147483647) throw new Error('Seed must be a whole number between 0 and 2,147,483,647.');
  if (!Number.isInteger(units) || units < 100 || units > 250000) throw new Error('Units must be a whole number between 100 and 250,000.');
  return {seed, units};
}

function resetTruthForNewRun() {
  $('truthText').textContent = 'Ground truth sealed. No causal labels are exposed in production records.';
  $('revealBtn').disabled = false;
  $('revealBtn').textContent = 'REVEAL + SCORE';
  const sc = $('arenaScorecard'); if (sc) sc.hidden = true;
  const st = $('arenaScoreText'); if (st) st.textContent = 'Reveal the sealed answer only after reviewing the blind diagnosis.';
  if ($('aiAnswerCard')) $('aiAnswerCard').hidden = true;
  if ($('askAiBtn')) $('askAiBtn').disabled = !(aiConfigured && buildCompatible);
  if ($('redTeamBtn')) $('redTeamBtn').disabled = !(aiConfigured && buildCompatible);
  if ($('runProbeBtn')) $('runProbeBtn').disabled = true;
  if ($('freezeHumanBtn')) $('freezeHumanBtn').disabled = true;
  if ($('executeExperimentBtn')) $('executeExperimentBtn').disabled = true;
  if ($('humanScore')) $('humanScore').hidden = true;
  if ($('humanStatus')) $('humanStatus').textContent = 'Choose one of the six competing hypotheses before reveal.';
  if ($('probeResult')) $('probeResult').textContent = 'No additional observational probe executed.';
  if ($('beliefUpdate')) $('beliefUpdate').textContent = '';
  if ($('experimentStatus')) $('experimentStatus').textContent = 'L5 remains locked';
  if ($('experimentMetrics')) $('experimentMetrics').textContent = 'No controlled experiment executed.';
  if ($('beliefRevision')) $('beliefRevision').textContent = 'If the authorized predeclared experiment later satisfies every confirmation criterion, the synthetic Level-5 gate may unlock. If it fails, KAIZEN must revise its belief instead of defending the old diagnosis.';
  if ($('l5Status')) $('l5Status').textContent = 'LOCKED';
}

async function breakFactory() {
  if (!buildCompatible) { alert('KAIZEN build mismatch/system health must be resolved before running an incident.'); return; }
  let inputs;
  try { inputs = validateRunInputs(); } catch (e) { alert(e.message); return; }
  $('breakBtn').disabled = true;
  $('breakBtn').textContent = 'INJECTING…';
  try {
    const payload = { seed:inputs.seed, units:inputs.units, scenario:'random', activation_fraction:0.42 };
    const created = await json('/api/runs', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
    currentRun = created.run_id;
    currentSourceMode = 'DEMO';
    $('runId').textContent = created.run_id;
    $('symptom').textContent = created.symptom;
    resetTruthForNewRun();
    await Promise.all([loadSummary(), loadRecords(), loadQuality(), loadIE(), loadInvestigation(), loadArena(), loadSimulationOverview(), loadOptimizerOverview(), loadActiveOverview(), loadControlPlan()]);
    await loadMissionControl();
  } catch (e) { alert(e.message); }
  finally { $('breakBtn').disabled = false; $('breakBtn').textContent = 'BREAK THE FACTORY'; }
}

async function loadSummary() {
  const data = await json(`/api/runs/${currentRun}/summary`);
  const pre = data.public_summary.pre_incident;
  const post = data.public_summary.post_incident;
  currentSourceMode = data.source_mode || 'DEMO';
  $('preDef').textContent = pct(pre.observed_defect_rate);
  $('postDef').textContent = pct(post.observed_defect_rate);
  $('preWait').textContent = sec(pre.avg_queue_wait_s);
  $('postWait').textContent = sec(post.avg_queue_wait_s);
  $('symptom').textContent = data.public_summary.symptom || $('symptom').textContent;
  if ($('contextRun')) $('contextRun').textContent = currentRun;
  if ($('contextMode')) $('contextMode').textContent = sourceLabel(currentSourceMode);
  if ($('missionMode')) $('missionMode').textContent = sourceLabel(currentSourceMode);
  const external = currentSourceMode !== 'DEMO';
  if (external) {
    $('truthText').textContent = 'External observable data: no synthetic causal truth exists inside KAIZEN. Real causal confirmation requires an intervention performed outside the application.';
    $('revealBtn').disabled = true;
    $('revealBtn').textContent = 'NO SYNTHETIC TRUTH';
  }
  updateArtifactButtons();
}

async function loadRecords() {
  const data = await json(`/api/runs/${currentRun}/records?limit=18`);
  $('recordCount').textContent = `${data.total.toLocaleString()} rows`;
  $('recordsBody').innerHTML = data.records.map(r => `<tr>
    <td>${r.unit_id}</td><td>${r.shift}</td><td>${r.product_variant}</td><td>${r.machine_id}</td><td>${r.fixture_id}</td>
    <td>${Number(r.torque_measured_nm).toFixed(3)}</td><td>${Number(r.alignment_measured_mm).toFixed(3)}</td><td>${Number(r.queue_wait_s).toFixed(1)}</td>
    <td>${r.observed_defect ? r.defect_type : '—'}</td>
  </tr>`).join('');
}

function capabilityRow(a) {
  const cls = a.status === 'CAPABLE' ? 'good' : a.status === 'MARGINAL' ? 'warn' : 'bad';
  return `<tr><td>${a.metric}</td><td>${a.scope}</td><td>${a.phase.toUpperCase()}</td><td>${a.n}</td><td>${num(a.mean,3)}</td>
    <td>${num(a.cp)}</td><td>${num(a.cpk)}</td><td>${num(a.pp)}</td><td>${num(a.ppk)}</td><td><span class="pill ${cls}">${a.status.replace('_',' ')}</span></td></tr>`;
}

function renderPareto(items) {
  if (!items.length) { $('paretoBars').innerHTML = '<p class="empty">No observed defects.</p>'; return; }
  const max = Math.max(...items.map(x => x.occurrences));
  $('paretoBars').innerHTML = items.map(x => `<div class="bar-row">
      <div class="bar-label"><strong>${x.defect_family}</strong><span>${x.occurrences} · ${pct(x.cumulative_share)} cumulative</span></div>
      <div class="bar-track"><div class="bar-fill" style="width:${100*x.occurrences/max}%"></div></div>
    </div>`).join('');
}

function renderSpc(chart) {
  const el = $('spcChart');
  const series = chart.series;
  if (!series?.length) { el.textContent = 'No SPC points.'; return; }
  const width = 1000, height = 260, pad = 34;
  const ys = series.map(p => p.value).concat([chart.ucl, chart.lcl, chart.center]);
  const ymin = Math.min(...ys), ymax = Math.max(...ys), span = Math.max(1e-9, ymax-ymin);
  const x = i => pad + i*(width-2*pad)/Math.max(1,series.length-1);
  const y = v => height-pad-(v-ymin)*(height-2*pad)/span;
  const points = series.map((p,i)=>`${x(i).toFixed(1)},${y(p.value).toFixed(1)}`).join(' ');
  const incidentIndex = series.findIndex(p=>p.incident_active);
  const incidentX = incidentIndex >= 0 ? x(incidentIndex) : null;
  const hline = (v,label,cls) => `<line class="${cls}" x1="${pad}" x2="${width-pad}" y1="${y(v)}" y2="${y(v)}"/><text x="${width-pad-4}" y="${y(v)-5}" text-anchor="end">${label} ${num(v,3)}</text>`;
  el.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Torque error Individuals chart">
    ${hline(chart.ucl,'UCL','limit danger-line')}${hline(chart.center,'CL','limit center-line')}${hline(chart.lcl,'LCL','limit danger-line')}
    ${incidentX !== null ? `<line class="incident-line" x1="${incidentX}" x2="${incidentX}" y1="${pad}" y2="${height-pad}"/><text x="${incidentX+6}" y="${pad+14}">INCIDENT</text>`:''}
    <polyline class="spc-series" points="${points}"/>
  </svg>`;
}

async function loadQuality() {
  $('qualityState').textContent = 'Calculating…';
  const data = await json(`/api/runs/${currentRun}/quality/overview`);
  const q = data.quality;
  $('qualityState').textContent = q.evidence_state.define_measure_core.replaceAll('_',' ');
  $('problemStatement').textContent = q.define.project_charter.problem_statement;
  $('dqScore').textContent = `${q.data_quality.score.toFixed(0)}/100`;
  $('copq').textContent = money(q.pareto_copq.copq.per_1000_units_usd);

  const torquePre = q.capability.analyses.find(x => x.metric==='Torque error' && x.phase==='pre');
  const torquePost = q.capability.analyses.find(x => x.metric==='Torque error' && x.phase==='post');
  $('torqueCpk').textContent = `${num(torquePre?.cpk)} → ${num(torquePost?.cpk)}`;
  const rr = q.msa.crossed_gage_rr;
  $('grr').textContent = `${rr.pct_study_variation_grr.toFixed(1)}%`;
  $('grrStatus').textContent = rr.status;
  $('ndc').textContent = rr.ndc;

  renderPareto(q.pareto_copq.pareto);
  const c = q.pareto_copq.copq;
  $('copqBreakdown').textContent = `Run COPQ ${money(c.total_usd)} · quality ${money(c.quality_usd)} · flow delay ${money(c.flow_delay_usd)} · rework ${c.rework_units} · scrap ${c.scrap_units}`;
  $('capBody').innerHTML = q.capability.analyses.map(capabilityRow).join('');
  $('gageBody').innerHTML = q.msa.gage_stratification.map(g => `<tr><td>${g.gage_id}</td><td>${g.n}</td><td>${num(g.mean_torque_error_nm,3)}</td><td>${num(g.sd_torque_error_nm,3)}</td><td>${pct(g.observed_defect_rate)}</td></tr>`).join('');

  const spc = q.spc.torque_error_imr;
  $('spcSignals').textContent = `${spc.signal_count.toLocaleString()} signals`;
  $('spcNote').textContent = q.spc.baseline_policy;
  $('spcLimits').textContent = `Center ${num(spc.center,3)} Nm · UCL ${num(spc.ucl,3)} · LCL ${num(spc.lcl,3)} · within σ ${num(spc.sigma_within,3)} · p-chart signals ${q.spc.defect_p_chart.signal_count}`;
  renderSpc(spc);
}


function statusClass(status) {
  if (['AVAILABLE','CAPABLE','ACCEPTABLE'].includes(status)) return 'good';
  if (['AT_RISK','MARGINAL','ASSUMED_100_PERCENT'].includes(status)) return 'warn';
  return 'bad';
}

function flowRow(x) {
  return `<tr><td>${x.phase.toUpperCase()}</td><td>${num(x.throughput_units_per_hour,1)}</td><td>${num(x.good_throughput_units_per_hour,1)}</td>
    <td>${num(x.mean_flow_time_s,1)}</td><td>${num(x.average_wip_units,2)}</td><td>${x.max_wip_units}</td><td>${num(x.little_law_error_pct,6)}%</td></tr>`;
}

function queueRow(x) {
  return `<tr><td>${x.phase.toUpperCase()}</td><td>${num(x.arrival_rate_units_per_hour,1)}</td><td>${num(x.service_rate_units_per_hour,1)}</td>
    <td>${sec(x.mean_wait_s)}</td><td>${num(x.average_queue_wip_units,2)}</td><td>${x.max_queue_wip_units}</td><td>${pct(x.probability_waited)}</td></tr>`;
}

function capacityRow(x) {
  const cls = statusClass(x.status);
  return `<tr><td>${x.station}</td><td>${x.phase.toUpperCase()}</td><td>${num(x.mean_service_s,1)}</td><td>${num(x.p95_service_s,1)}</td>
    <td>${num(x.capacity_units_per_hour,1)}</td><td>${pct(x.demand_utilization)}</td><td>${pct(x.release_utilization)}</td>
    <td><span class="pill ${cls}">${x.status.replaceAll('_',' ')}</span></td></tr>`;
}

function oeeRow(x) {
  return `<tr><td>${x.phase.toUpperCase()}</td><td>${pct(x.availability)}</td><td>${pct(x.performance)}</td><td>${pct(x.quality)}</td>
    <td><strong>${pct(x.oee)}</strong></td><td><span class="pill warn">${x.availability_status.replaceAll('_',' ')}</span></td></tr>`;
}

async function loadIE() {
  $('ieState').textContent = 'Calculating…';
  const data = await json(`/api/runs/${currentRun}/ie/overview`);
  const ie = data.ie;
  const pre = ie.flow.pre, post = ie.flow.post;
  const qpre = ie.queueing.pre, qpost = ie.queueing.post;
  const bpre = ie.capacity.pre.bottleneck, bpost = ie.capacity.post.bottleneck;
  const lpre = ie.line_balance.pre, lpost = ie.line_balance.post;
  const vpre = pre.value_stream, vpost = post.value_stream;
  const opre = ie.oee.pre, opost = ie.oee.post;

  $('ieState').textContent = ie.evidence_state.ie_core.replaceAll('_',' ');
  $('taktMetric').textContent = `${num(ie.takt.takt_seconds_per_unit,1)} s/unit`;
  $('throughputMetric').textContent = `${num(post.throughput_units_per_hour,1)} /h`;
  $('wipMetric').textContent = `${num(post.average_wip_units,1)} units`;
  $('oeeMetric').textContent = pct(opost.oee);
  $('ieSummary').textContent = `Customer takt is ${num(ie.takt.takt_seconds_per_unit,1)} s/unit (${num(ie.takt.required_rate_units_per_hour,1)} units/h). Post-incident bottleneck: ${bpost.station} at ${num(bpost.capacity_units_per_hour,1)} units/h.`;

  $('flowBody').innerHTML = [pre,post].map(flowRow).join('');
  $('flowNote').textContent = `Little's Law closes from reconstructed launch-to-completion intervals. Post FPY ${pct(post.first_pass_yield)} · release rate ${num(post.release_rate_units_per_hour,1)}/h.`;
  $('queueBody').innerHTML = [qpre,qpost].map(queueRow).join('');
  $('queueNote').textContent = `${qpost.method} Post cell Little's Law error ${num(qpost.little_law_cell_error_pct,6)}%.`;

  $('capacityBody').innerHTML = [...ie.capacity.pre.stations, ...ie.capacity.post.stations].map(capacityRow).join('');
  $('bottleneckBadge').textContent = `${bpre.station} → ${bpost.station}`;
  $('bottleneckNote').textContent = `Pre bottleneck ${bpre.station}: ${num(bpre.capacity_units_per_hour,1)}/h. Post: ${bpost.station}: ${num(bpost.capacity_units_per_hour,1)}/h with ${pct(bpost.release_utilization)} release utilization.`;

  $('balancePre').textContent = pct(lpre.intrinsic_balance_efficiency);
  $('balancePost').textContent = pct(lpost.intrinsic_balance_efficiency);
  $('cyclePost').textContent = sec(lpost.intrinsic_cycle_time_s);
  $('smoothPost').textContent = `${num(lpost.smoothness_index_s,1)} s`;
  $('balanceNote').textContent = lpost.takt_feasible_with_one_resource_each
    ? `All station mean workloads remain at or below takt. Balance delay ${pct(lpost.intrinsic_balance_delay)}.`
    : `Takt infeasible with one resource at: ${lpost.stations_exceeding_takt.join(', ')}.`;

  $('pcePre').textContent = pct(vpre.process_cycle_efficiency);
  $('pcePost').textContent = pct(vpost.process_cycle_efficiency);
  $('vaPost').textContent = sec(vpost.mean_value_added_s);
  $('waitPost').textContent = sec(vpost.mean_wait_s);
  $('valueStreamNote').textContent = vpost.classification_note;

  $('oeeBody').innerHTML = [opre,opost].map(oeeRow).join('');
  $('oeeNote').textContent = opost.availability_note;
}


function hypothesisStatusClass(status) {
  if (status === 'STRONG_SUSPECT') return 'good';
  if (status === 'SUPPORTED_ASSOCIATION') return 'warn';
  if (status === 'WEAK_SIGNAL') return 'warn';
  return 'bad';
}

function hypothesisRow(h) {
  const cls = hypothesisStatusClass(h.status);
  const t = h.primary_test || {};
  return `<tr><td>${h.rank}</td><td><strong>${h.title}</strong></td><td>${h.target}</td><td>${num(h.evidence_score,1)}</td>
    <td><span class="pill ${cls}">${h.status.replaceAll('_',' ')}</span></td><td>${pval(t.p_value)}</td><td>${num(t.effect,3)}</td></tr>`;
}

function gateItem(x) {
  const cls = x.passed ? 'pass' : (x.level === 5 ? 'locked' : '');
  const mark = x.passed ? '✓' : (x.level === 5 ? '🔒' : '·');
  return `<div class="gate-item ${cls}"><span class="gate-dot">${mark}</span><div><strong>L${x.level} — ${x.name}</strong><p>${x.meaning}</p></div></div>`;
}

async function loadInvestigation() {
  $('investigatorState').textContent = 'Calculating…';
  const data = await json(`/api/runs/${currentRun}/investigation/overview`);
  const inv = data.investigation;
  const top = inv.top_suspect;

  $('investigatorState').textContent = inv.evidence_state.analyze_core.replaceAll('_',' ');
  $('topSuspectShort').textContent = top.target;
  $('topEvidenceScore').textContent = `${num(top.evidence_score,1)}/100`;
  $('topHypothesisStatus').textContent = top.status.replaceAll('_',' ');
  $('ambiguityMetric').textContent = inv.ambiguity.level;
  $('investigatorSummary').textContent = `${top.title}. ${top.summary}`;

  $('hypothesisBody').innerHTML = inv.ranked_hypotheses.map(hypothesisRow).join('');
  $('hypothesisNote').textContent = `${inv.ambiguity.message} Top-to-second score gap: ${num(inv.ambiguity.top_to_second_score_gap,1)}. Evidence score is not a probability.`;

  $('causalGate').innerHTML = inv.causality_gate.levels.map(gateItem).join('');
  $('gatePolicy').textContent = inv.causality_gate.policy;

  const models = inv.adjusted_models;
  $('modelStatus').textContent = `${models.models_fit}/${models.models_attempted} MODELS ${models.status}`;
  const regRows = [];
  for (const model of models.ols || []) {
    for (const c of (model.coefficients || []).slice(0,6)) {
      regRows.push(`<tr><td>${model.name}</td><td>${c.term}</td><td>${num(c.estimate,4)}</td><td>${pval(c.p_value)}</td><td>${ci95(c.confidence_interval_95)}</td></tr>`);
    }
  }
  for (const c of (models.logistic?.coefficients || []).slice(0,4)) {
    regRows.push(`<tr><td>Defect logistic</td><td>${c.term}</td><td>OR ${num(c.odds_ratio,3)}</td><td>${pval(c.p_value)}</td><td>${ci95(c.confidence_interval_95_or)}</td></tr>`);
  }
  $('regressionBody').innerHTML = regRows.length ? regRows.join('') : '<tr><td colspan="5" class="empty">Adjusted models unavailable.</td></tr>';
  $('regressionNote').textContent = models.policy;

  const anova = models.anova || {};
  $('anovaBody').innerHTML = (anova.terms || []).slice(0,12).map(a => `<tr><td>${a.term}</td><td>${num(a.f_statistic,3)}</td><td>${pval(a.p_value)}</td><td>${num(a.df,1)}</td></tr>`).join('') || '<tr><td colspan="4" class="empty">ANOVA unavailable.</td></tr>';
  $('anovaNote').textContent = anova.interpretation_limit || anova.error || '';

  const ledger = inv.evidence_ledger;
  $('evidenceCount').textContent = `${ledger.length} tests`;
  $('evidenceBody').innerHTML = ledger.map(e => `<tr><td>${e.evidence_id}</td><td>${e.hypothesis_code}</td><td>${e.role}</td><td>${e.test}</td>
    <td>${pval(e.p_value)}</td><td>${num(e.effect,3)}</td><td>${e.n}</td><td>${e.detail}</td></tr>`).join('');

  $('confounderBody').innerHTML = inv.confounder_checks.map(c => `<tr><td>${c.factor}</td><td>${c.level}</td><td>${c.test.test}</td>
    <td>${pval(c.test.p_value)}</td><td>${num(c.test.effect,3)}</td><td>${c.interpretation}</td></tr>`).join('');
}


function arenaTimelineItem(e) {
  const cls = e.status === 'LOCKED' ? 'locked' : 'pass';
  const mark = e.status === 'LOCKED' ? '🔒' : '✓';
  return `<div class="timeline-item ${cls}"><span class="timeline-mark">${mark}</span><div><span class="timeline-stage">${e.stage}</span><strong>${e.title}</strong><p>${e.detail}</p></div></div>`;
}

async function loadArena() {
  const data = await json(`/api/runs/${currentRun}/arena/overview`);
  const a = data.arena;
  const p = a.prediction_snapshot;
  $('arenaPrediction').textContent = `${p.target} · ${p.direction || 'direction unresolved'}`;
  $('arenaScorePreview').textContent = `${num(p.evidence_score,1)}/100`;
  $('arenaStatus').textContent = p.status.replaceAll('_',' ');
  $('arenaAmbiguity').textContent = p.ambiguity;
  $('arenaTimeline').innerHTML = a.timeline.map(arenaTimelineItem).join('');
  $('arenaPolicy').textContent = a.reveal_policy;
}

function renderArenaScorecard(card) {
  $('arenaScorecard').hidden = false;
  $('arenaFinalScore').textContent = `${num(card.score,1)}%`;
  $('arenaGrade').textContent = card.grade.replaceAll('_',' ');
  $('arenaDimensions').textContent = `${card.dimensions_correct}/${card.dimensions_total}`;
  const c = card.checks;
  $('arenaChecks').innerHTML = Object.entries(c).map(([k,v]) => `<div class="score-check ${v?'pass':'fail'}"><span>${v?'✓':'✕'}</span><strong>${k.replaceAll('_',' ')}</strong></div>`).join('');
  const b = card.blind_prediction;
  const e = card.expected_attribution;
  $('arenaScoreText').textContent = `Blind: ${b.code} / ${b.target} / ${b.direction || '—'} / ${b.interaction_partner || 'none'} · Truth target: ${e.target}.`;
}

async function revealTruth() {
  if (!currentRun) return;
  if (!confirm('Reveal the hidden causal mechanism and score the blind diagnosis?')) return;
  try {
    const data = await json(`/api/runs/${currentRun}/arena/reveal-score`, {method:'POST'});
    const s = data.ground_truth.scenario;
    $('truthText').innerHTML = `<strong>${s.root_cause}</strong><br>${s.mechanism}<br><br><span style="color:#93a69e">Causal chain: ${s.causal_graph.join(' → ')}</span>`;
    renderArenaScorecard(data.scorecard);
    $('revealBtn').disabled = true;
    $('revealBtn').textContent = 'DIAGNOSIS SCORED';
    if ($('humanStatus')) await loadHumanVsAI();
    await loadMissionControl();
  } catch(e) { alert(e.message); }
}


function simCandidateRow(x) {
  const rec = x.recommended_for_top_suspect ? '<span class="pill good">RECOMMENDED</span>' : '';
  const dDef = `${x.defect_rate_pp_delta >= 0 ? '+' : ''}${num(x.defect_rate_pp_delta,2)} pp`;
  const dLead = `${x.lead_time_delta_s >= 0 ? '+' : ''}${num(x.lead_time_delta_s,1)} s`;
  const dCopq = `${x.copq_per_1000_delta_usd >= 0 ? '+' : ''}${money(x.copq_per_1000_delta_usd)}`;
  return `<tr><td><strong>${x.label}</strong> ${rec}</td><td>${x.target}</td><td>${num(x.evidence_score,1)}</td><td>${dDef}</td><td>${dLead}</td><td>${dCopq}</td><td>${money(x.one_time_cost_usd)}</td><td>${num(x.planned_downtime_hours,1)} h</td></tr>`;
}

function renderWhatIf(w) {
  const b = w.baseline, a = w.counterfactual, d = w.delta;
  $('simRecommended').textContent = w.label;
  $('simDefect').textContent = `${pct(b.defect_rate)} → ${pct(a.defect_rate)}`;
  $('simGoodThroughput').textContent = `${num(b.good_throughput_units_per_hour,1)} → ${num(a.good_throughput_units_per_hour,1)} /h`;
  $('simCopq').textContent = `${money(b.copq_per_1000_units_usd)} → ${money(a.copq_per_1000_units_usd)}`;
  $('simBaselineHeadline').textContent = `${pct(b.defect_rate)} defects · ${num(b.mean_lead_time_s,1)} s lead`;
  $('simBaselineDetail').textContent = `Good throughput ${num(b.good_throughput_units_per_hour,1)}/h · WIP ${num(b.average_wip_units,1)} · queue ${num(b.mean_queue_wait_s,1)} s · torque Cpk ${num(b.torque_cpk,2)}.`;
  $('simCounterHeadline').textContent = `${pct(a.defect_rate)} defects · ${num(a.mean_lead_time_s,1)} s lead`;
  $('simCounterDetail').textContent = `Δ defect ${d.defect_rate_pp >= 0 ? '+' : ''}${num(d.defect_rate_pp,2)} pp · Δ good throughput ${d.good_throughput_units_per_hour >= 0 ? '+' : ''}${num(d.good_throughput_units_per_hour,1)}/h · Δ COPQ ${d.copq_per_1000_units_usd >= 0 ? '+' : ''}${money(d.copq_per_1000_units_usd)} /1k.`;
  $('simulationGuardrail').textContent = w.causal_guardrail;
  const u = w.uncertainty || {};
  $('simulationUncertainty').textContent = u.repetitions
    ? `Paired bootstrap (${u.repetitions} reps, 90%): defect Δ ${u.defect_rate_pp_delta_90pct[0]} to ${u.defect_rate_pp_delta_90pct[1]} pp · COPQ Δ ${money(u.copq_per_1000_delta_usd_90pct[0])} to ${money(u.copq_per_1000_delta_usd_90pct[1])} /1k · unit flow Δ ${u.mean_unit_flow_time_delta_s_90pct[0]} to ${u.mean_unit_flow_time_delta_s_90pct[1]} s.`
    : '';
}

async function loadSimulationOverview() {
  $('simulationState').textContent = 'Simulating…';
  const data = await json(`/api/runs/${currentRun}/simulation/overview`);
  const s = data.simulation;
  $('simulationState').textContent = s.evidence_state.simulation_core.replaceAll('_',' ');
  $('simulationSummary').textContent = `Recommended from blind diagnosis: ${s.recommended_intervention.label}. All scenarios replay the same observed unit mix; sealed truth is not an input.`;
  const select = $('simIntervention');
  select.innerHTML = s.controls.available_interventions.map(x => `<option value="${x.code}" ${x.code===s.recommended_intervention_code?'selected':''}>${x.label}</option>`).join('');
  $('simulationCandidates').innerHTML = s.candidate_interventions.map(simCandidateRow).join('');
  $('simulationPolicy').textContent = s.evidence_state.note;
  renderWhatIf(s.recommended_intervention);
  $('simulateBtn').disabled = false;
}

async function runWhatIf() {
  if (!currentRun) return;
  const intervention = $('simIntervention').value;
  const effectiveness = Number($('simEffectiveness').value) / 100.0;
  const demand = Number($('simDemand').value);
  if (!intervention) { alert('Choose an intervention.'); return; }
  if (!Number.isFinite(effectiveness) || effectiveness < 0 || effectiveness > 1) { alert('Effectiveness must be between 0% and 100%.'); return; }
  if (!Number.isFinite(demand) || demand < 0.5 || demand > 1.75) { alert('Demand multiplier must be between 0.50 and 1.75.'); return; }
  $('simulateBtn').disabled = true;
  $('simulateBtn').textContent = 'SIMULATING…';
  try {
    const data = await json(`/api/runs/${currentRun}/simulation/what-if`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({intervention_code:intervention,effectiveness,demand_multiplier:demand})});
    renderWhatIf(data.what_if);
  } catch (e) { alert(e.message); }
  finally { $('simulateBtn').disabled = false; $('simulateBtn').textContent = 'RUN WHAT-IF'; }
}



function portfolioLabels(items) {
  if (!items?.length) return 'No action';
  return items.map(x => x.label).join(' + ');
}

function portfolioRow(x, rank) {
  const roi = x.financials?.first_year_roi;
  const roiText = roi === null || roi === undefined ? '—' : `${(roi*100).toFixed(0)}%`;
  return `<tr><td>${rank}</td><td><strong>${x.labels.length ? x.labels.join(' + ') : 'No action'}</strong></td><td>${money(x.cost_usd)}</td><td>${num(x.downtime_hours,1)} h</td><td>${num(x.good_throughput_uph,1)}/h</td><td>${pct(x.defect_rate)}</td><td>${money(x.financials.first_year_net_value_usd)}</td><td>${roiText}</td></tr>`;
}

function formatPayback(years) {
  if (years === null || years === undefined) return '—';
  const days = Number(years) * 365;
  if (days < 30) return `${num(days,1)} days`;
  return `${num(Number(years)*12,1)} months`;
}

function renderOptimizer(o) {
  $('optimizerState').textContent = o.evidence_state.optimizer_core.replaceAll('_',' ');
  $('optimizerMethod').textContent = `${o.solver.method} · ${o.solver.evaluated_portfolios}/${o.solver.search_space_size} portfolios evaluated`;
  $('optimizerPolicy').textContent = o.evidence_state.note;
  const b = o.best_portfolio;
  if (!b) {
    $('optimizerStatus').textContent = 'INFEASIBLE';
    $('optimizerPortfolio').textContent = 'No feasible portfolio';
    $('optimizerCost').textContent = '—';
    $('optimizerDowntime').textContent = '—';
    $('optimizerValue').textContent = '—';
    $('optimizerResult').textContent = o.infeasibility?.message || 'No portfolio satisfies all constraints.';
    $('optimizerTopBody').innerHTML = (o.infeasibility?.nearest_portfolios || []).map((x,i)=>portfolioRow(x,i+1)).join('') || '<tr><td colspan="8" class="empty">No feasible portfolio.</td></tr>';
    return;
  }
  const f = o.best_financials;
  $('optimizerStatus').textContent = 'OPTIMAL';
  $('optimizerPortfolio').textContent = portfolioLabels(b.interventions);
  $('optimizerCost').textContent = money(b.engineering_assumptions.total_one_time_cost_usd);
  $('optimizerDowntime').textContent = `${num(b.engineering_assumptions.total_planned_downtime_hours,1)} h`;
  $('optimizerValue').textContent = money(f.first_year_net_value_usd);
  $('optimizerResult').textContent = `Good throughput ${num(b.counterfactual.good_throughput_units_per_hour,1)}/h · defect rate ${pct(b.counterfactual.defect_rate)} · annual COPQ avoided ${money(f.annual_copq_avoided_usd)} · payback ${formatPayback(f.simple_payback_years)}.`;
  $('optimizerTopBody').innerHTML = o.top_feasible_portfolios.map((x,i)=>portfolioRow(x,i+1)).join('');
}

async function loadOptimizerOverview() {
  $('optimizerState').textContent = 'Optimizing…';
  const data = await json(`/api/runs/${currentRun}/optimizer/overview`);
  const o = data.optimizer;
  renderOptimizer(o);
  $('optimizeBtn').disabled = false;
}

async function solvePortfolio() {
  if (!currentRun) return;
  const payload = {
    budget_usd: Number($('optBudget').value),
    max_downtime_hours: Number($('optDowntime').value),
    min_good_throughput_uph: Number($('optGood').value),
    max_defect_rate: Number($('optDefect').value)/100.0,
    annual_volume_units: Number($('optAnnualVolume').value),
    effectiveness: Number($('optEffectiveness').value)/100.0,
    demand_multiplier: Number($('optDemand').value),
    min_evidence_score: Number($('optEvidence').value),
  };
  if (!Number.isFinite(payload.budget_usd) || payload.budget_usd < 0) { alert('Budget must be non-negative.'); return; }
  if (!Number.isFinite(payload.max_downtime_hours) || payload.max_downtime_hours < 0) { alert('Downtime limit must be non-negative.'); return; }
  if (!Number.isFinite(payload.min_good_throughput_uph) || payload.min_good_throughput_uph < 0) { alert('Minimum good throughput must be non-negative.'); return; }
  if (!Number.isFinite(payload.max_defect_rate) || payload.max_defect_rate < 0 || payload.max_defect_rate > 1) { alert('Maximum defect rate must be between 0% and 100%.'); return; }
  if (!Number.isInteger(payload.annual_volume_units) || payload.annual_volume_units < 1) { alert('Annual volume must be a positive whole number.'); return; }
  if (!Number.isFinite(payload.effectiveness) || payload.effectiveness < 0 || payload.effectiveness > 1) { alert('Effectiveness must be between 0% and 100%.'); return; }
  if (!Number.isFinite(payload.demand_multiplier) || payload.demand_multiplier < 0.5 || payload.demand_multiplier > 1.75) { alert('Demand multiplier must be between 0.50 and 1.75.'); return; }
  if (!Number.isFinite(payload.min_evidence_score) || payload.min_evidence_score < 0 || payload.min_evidence_score > 100) { alert('Minimum evidence score must be between 0 and 100.'); return; }
  $('optimizeBtn').disabled = true;
  $('optimizeBtn').textContent = 'OPTIMIZING…';
  try {
    const data = await json(`/api/runs/${currentRun}/optimizer/solve`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    renderOptimizer(data.optimizer);
    await loadMissionControl();
  } catch(e) { alert(e.message); }
  finally { $('optimizeBtn').disabled = false; $('optimizeBtn').textContent = 'OPTIMIZE PORTFOLIO'; }
}


function renderActiveOverview(a) {
  const u = a.uncertainty;
  const voi = a.value_of_information;
  const best = voi.recommended_next_measurement;
  $('activeState').textContent = u.state.replaceAll('_',' ');
  $('uncertaintyVerdict').textContent = u.label;
  $('uncertaintyGap').textContent = `${num(u.score_gap,1)} pts`;
  $('voiAction').textContent = best.label;
  $('voiScore').textContent = `${num(best.value_of_information_score,1)}/100`;
  $('uncertaintyReason').textContent = u.rationale;
  $('voiDetail').textContent = `${best.question} · synthetic probe burden ${money(best.cost_usd)} / ${num(best.duration_hours,1)} h · ${best.interpretation}`;
  $('probeSelect').innerHTML = voi.ranked_candidates.map(x => `<option value="${x.code}" ${x.rank===1?'selected':''}>#${x.rank} ${x.label} — VOI ${num(x.value_of_information_score,1)}</option>`).join('');
  $('runProbeBtn').disabled = false;

  const d = a.experiment_preview;
  $('experimentTitle').textContent = d.title;
  $('experimentFactor').textContent = `Factor: ${d.factor} · target ${d.target} · blocks: ${(d.blocks||[]).join(', ')}`;
  $('experimentLevels').textContent = `Levels: ${(d.levels||[]).join(' | ')} · n=${d.planned_sample_size} · randomization: ${d.randomization}`;
  $('experimentRule').textContent = `Predeclared rule: ${d.predeclared_success_rule}`;
  $('executeExperimentBtn').dataset.experimentCode = d.experiment_code;
  if (currentSourceMode === 'DEMO') {
    $('executeExperimentBtn').disabled = false;
    $('executeExperimentBtn').textContent = 'AUTHORIZE + RUN SYNTHETIC DOE';
  } else {
    $('executeExperimentBtn').disabled = true;
    $('executeExperimentBtn').textContent = 'REAL DOE EXECUTES OUTSIDE KAIZEN';
  }
  const c = a.causal_confirmation || {};
  $('l5Status').textContent = c.passed ? 'UNLOCKED' : (c.level_5 || 'LOCKED');
  if (a.experiment_result) {
    renderExperimentResult(a.experiment_result);
  } else {
    $('experimentStatus').textContent = 'L5 remains locked';
    $('experimentMetrics').textContent = 'No controlled experiment executed.';
    $('beliefRevision').textContent = 'If the authorized predeclared experiment later satisfies every confirmation criterion, the synthetic Level-5 gate may unlock. If it fails, KAIZEN must revise its belief instead of defending the old diagnosis.';
  }
  if (a.last_probe_result) renderProbeResult(a.last_probe_result);
  $('activePolicy').textContent = `${u.policy} ${a.active_investigation.policy}`;
}

async function loadHumanVsAI() {
  const data = await json(`/api/runs/${currentRun}/human-vs-ai`);
  const h = data.human_vs_ai;
  $('humanDiagnosis').innerHTML = h.available_choices.map(x => `<option value="${x.code}">${x.title} · ${x.target} · evidence ${num(x.evidence_score,1)}</option>`).join('');
  if (h.human_prediction) {
    $('humanStatus').textContent = `LOCKED: ${h.human_prediction.title} · target ${h.human_prediction.target}`;
    $('freezeHumanBtn').disabled = true;
  } else {
    $('freezeHumanBtn').disabled = false;
  }
  if (h.truth_revealed && h.human_score) {
    $('humanScore').hidden = false;
    $('humanScore').textContent = `HUMAN ${num(h.human_score.score,1)}% · ${h.human_score.dimensions_correct}/4 | AI ${num(h.ai_score.score,1)}% · ${h.ai_score.dimensions_correct}/4`;
  }
}

async function loadActiveOverview() {
  $('activeState').textContent = 'Calculating…';
  const data = await json(`/api/runs/${currentRun}/active/overview`);
  renderActiveOverview(data.active);
  await loadHumanVsAI();
}

function renderProbeResult(p) {
  const r = p.result;
  $('probeResult').textContent = `${p.probe.label}: effect ${num(r.effect,4)} · p=${pval(r.p_value)} · support ${num(r.support_score,1)}/100 · ${r.supports_target_hypothesis ? 'supports' : 'does not strongly support'} ${p.probe.hypothesis_code}. ${r.detail}`;
  const b = p.belief_update;
  $('beliefUpdate').textContent = b.changed_leader
    ? `BELIEF REVISED: ${b.prior_leader} → ${b.updated_leader}. ${b.policy}`
    : `Leader retained: ${b.updated_leader}. ${b.policy}`;
}

async function runActiveProbe() {
  if (!currentRun) return;
  const code = $('probeSelect').value;
  if (!code) return;
  $('runProbeBtn').disabled = true; $('runProbeBtn').textContent = 'MEASURING…';
  try {
    const data = await json(`/api/runs/${currentRun}/active/probe`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({probe_code:code})});
    renderProbeResult(data.probe);
  } catch(e) { alert(e.message); }
  finally { $('runProbeBtn').disabled=false; $('runProbeBtn').textContent='RUN NEXT PROBE'; }
}

async function freezeHumanDiagnosis() {
  if (!currentRun) return;
  const code = $('humanDiagnosis').value;
  if (!code) { alert('Choose a diagnosis.'); return; }
  $('freezeHumanBtn').disabled = true;
  try {
    const data = await json(`/api/runs/${currentRun}/human-vs-ai/predict`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({hypothesis_code:code})});
    const h=data.human_prediction;
    $('humanStatus').textContent = `LOCKED: ${h.title} · target ${h.target}. Reveal later to score Human vs AI.`;
  } catch(e) { alert(e.message); $('freezeHumanBtn').disabled=false; }
}

function renderExperimentResult(e) {
  const c=e.causal_confirmation, r=e.aggregate_results, b=e.belief_revision;
  $('experimentStatus').textContent = c.passed ? 'L5 UNLOCKED — SYNTHETIC DOE CONFIRMED' : 'L5 LOCKED — DOE DID NOT CONFIRM';
  $('l5Status').textContent = c.passed ? 'UNLOCKED' : 'LOCKED';
  $('experimentMetrics').textContent = `Control ${num(r.control_mean,4)} → treatment ${num(r.treatment_mean,4)} · Δ ${num(r.difference_treatment_minus_control,4)} · p=${pval(r.p_value)} · Cohen d ${num(r.cohen_d,3)} · direction ${r.direction_passed?'PASS':'FAIL'}.`;
  $('beliefRevision').textContent = `${b.audit_message}${b.outcome==='FAILED_CONFIRMATION' && b.next_leader_if_failed ? ` Next hypothesis: ${b.next_leader_if_failed}.` : ''} ${c.note}`;
  $('executeExperimentBtn').disabled = true;
  if ($('missionL5')) $('missionL5').textContent = c.passed ? 'UNLOCKED' : 'LOCKED';
  if ($('contextL5')) $('contextL5').textContent = c.passed ? 'UNLOCKED' : 'LOCKED';
}

async function executeExperiment() {
  if (!currentRun) return;
  const code = $('executeExperimentBtn').dataset.experimentCode;
  if (!code) return;
  if (!confirm('Authorize and run the controlled synthetic DOE? This is the only DEMO action that can unlock synthetic L5 inside the Hidden Factory benchmark.')) return;
  $('executeExperimentBtn').disabled=true; $('executeExperimentBtn').textContent='RUNNING DOE…';
  try {
    const data=await json(`/api/runs/${currentRun}/experiment/execute`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({experiment_code:code,authorized:true})});
    renderExperimentResult(data.experiment);
    await loadMissionControl();
  } catch(e) { alert(e.message); $('executeExperimentBtn').disabled=false; }
  finally { $('executeExperimentBtn').textContent='AUTHORIZE + RUN SYNTHETIC DOE'; }
}

function fillList(id, items, emptyText='None identified.') {
  const el = $(id);
  if (!el) return;
  el.innerHTML = '';
  const vals = Array.isArray(items) && items.length ? items : [emptyText];
  vals.forEach(text => { const li=document.createElement('li'); li.textContent=String(text); el.appendChild(li); });
}

function renderAIResult(payload) {
  const x = payload.ai;
  const r = x.response;
  $('aiAnswerCard').hidden = false;
  $('aiMode').textContent = r.mode;
  $('aiHeadline').textContent = r.headline;
  $('aiCausalStatus').textContent = r.causal_status.replaceAll('_',' ');
  $('aiAnswerText').textContent = r.answer;
  $('aiEvidence').innerHTML = '';
  (r.evidence_ids || []).forEach(id => { const tag=document.createElement('span'); tag.textContent=id; $('aiEvidence').appendChild(tag); });
  if (!(r.evidence_ids || []).length) { const tag=document.createElement('span'); tag.textContent='NO LEDGER IDS CITED'; $('aiEvidence').appendChild(tag); }
  fillList('aiContradictions', r.contradictory_evidence);
  fillList('aiAssumptions', r.assumptions);
  fillList('aiUnknowns', r.unresolved_questions);
  fillList('aiNextActions', r.recommended_next_actions);
  $('aiToolTrace').innerHTML = '';
  (x.tool_trace || []).forEach((t,i) => {
    const div=document.createElement('div'); div.className='timeline-item';
    const strong=document.createElement('strong'); strong.textContent=`${i+1}. ${t.tool}`;
    const p=document.createElement('p'); p.textContent=t.result_summary;
    div.appendChild(strong); div.appendChild(p); $('aiToolTrace').appendChild(div);
  });
  $('aiConfidence').textContent = `${r.confidence_language} · Provider: ${x.provider} · Model: ${x.model} · Ground-truth dependency: NO · AI authority over L5: NONE.`;
}

async function askKaizen(mode='ASK') {
  if (!currentRun) { alert('Break the factory first.'); return; }
  if (!aiConfigured) { alert('Gemini is not configured. Add GEMINI_API_KEY to .env and restart KAIZEN.'); return; }
  let q = $('aiQuestion').value.trim();
  if (mode==='RED_TEAM' && q.length < 3) q = "Challenge KAIZEN's current diagnosis and recommended intervention.";
  if (q.length < 3) { alert('Ask KAIZEN a question first.'); return; }
  const btn = mode==='RED_TEAM' ? $('redTeamBtn') : $('askAiBtn');
  const other = mode==='RED_TEAM' ? $('askAiBtn') : $('redTeamBtn');
  btn.disabled = true; other.disabled = true;
  const original = btn.textContent; btn.textContent = mode==='RED_TEAM' ? 'RED TEAMING…' : 'ANALYZING…';
  $('aiState').textContent = 'GEMINI WORKING…';
  try {
    const data = await json(`/api/runs/${currentRun}/ai/ask`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q,mode})});
    renderAIResult(data);
    $('aiState').textContent = 'GEMINI GROUNDED';
  } catch(e) { alert(e.message); $('aiState').textContent = 'GEMINI ERROR'; }
  finally { btn.textContent=original; btn.disabled=!(aiConfigured&&currentRun&&buildCompatible); other.disabled=!(aiConfigured&&currentRun&&buildCompatible); }
}

$('breakBtn').addEventListener('click', breakFactory);
$('revealBtn').addEventListener('click', revealTruth);
$('simulateBtn').addEventListener('click', runWhatIf);
$('optimizeBtn').addEventListener('click', solvePortfolio);
$('askAiBtn').addEventListener('click', ()=>askKaizen('ASK'));
$('redTeamBtn').addEventListener('click', ()=>askKaizen('RED_TEAM'));
$('runProbeBtn').addEventListener('click', runActiveProbe);
$('freezeHumanBtn').addEventListener('click', freezeHumanDiagnosis);
$('executeExperimentBtn').addEventListener('click', executeExperiment);
checkHealth().then(checkAIStatus);

async function loadControlPlan() {
  if (!currentRun || !$('controlState')) return;
  try {
    const data = await json(`/api/runs/${currentRun}/control/plan`);
    const c=data.control, m=c.monitoring, b=c.benefits_verification;
    $('controlState').textContent=c.state.replaceAll('_',' ');
    $('controlMetric').textContent=m.primary_metric;
    $('controlChart').textContent=m.chart;
    $('controlWindow').textContent=`${b.minimum_stabilization_window_units} units`;
    $('controlBenefits').textContent=c.handoff.realized_benefits_verified ? 'YES' : 'NO';
    $('controlReaction').textContent=m.reaction;
    $('controlCadence').textContent=`${m.cadence} Owner: ${m.owner_role}.`;
    $('controlVerify').textContent=b.success_policy;
    $('controlReopen').textContent=b.reopen_policy;
  } catch(e) { $('controlState').textContent='CONTROL PLAN ERROR'; console.error(e); }
}

// ---------------- V1.0 CONTROL ROOM / DATA INTEGRATION ----------------
function setWorkspace(name, {scroll=true}={}) {
  currentWorkspace = name;
  document.querySelectorAll('.workspace-section').forEach(el => {
    el.classList.toggle('active-workspace', el.dataset.workspace === name);
  });
  document.querySelectorAll('[data-workspace-target]').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.workspaceTarget === name);
  });
  if (scroll) window.scrollTo({top:0, behavior:'smooth'});
  if (name === 'evidence' && !publicEvidenceLoaded) loadPublicEvidence();
}

document.querySelectorAll('[data-workspace-target]').forEach(btn => {
  btn.addEventListener('click', () => setWorkspace(btn.dataset.workspaceTarget));
});
document.querySelectorAll('[data-jump]').forEach(btn => {
  btn.addEventListener('click', () => setWorkspace(btn.dataset.jump));
});

function updateArtifactButtons() {
  const enabled = Boolean(currentRun);
  ['exportCsvBtn','exportSnapshotBtn','openReportBtn'].forEach(id => { if ($(id)) $(id).disabled = !enabled; });
  if ($('reportBtn')) $('reportBtn').disabled = !enabled;
  if ($('replayBtn')) $('replayBtn').disabled = !enabled;
}

async function loadMissionControl() {
  if (!currentRun) return;
  try {
    const m = await json(`/api/runs/${currentRun}/mission-control`);
    currentSourceMode = m.source_mode || currentSourceMode;
    const k=m.kpis, d=m.diagnosis, dec=m.decision, v=m.validation;
    $('missionMode').textContent = sourceLabel(m.source_mode);
    $('missionDefect').textContent = pct(k.post_defect_rate);
    $('missionDefectDelta').textContent = `${((Number(k.post_defect_rate)-Number(k.pre_defect_rate))*100).toFixed(2)} pp vs baseline`;
    $('missionGood').textContent = num(k.post_good_throughput_uph,1);
    $('missionSuspect').textContent = d.target || d.hypothesis_code;
    $('missionEvidence').textContent = `${d.status.replaceAll('_',' ')} · ${num(d.evidence_score,1)}/100 · ${d.ambiguity} ambiguity`;
    $('missionDecision').textContent = dec.recommended_intervention || (dec.best_portfolio_labels || []).join(' + ') || 'No action';
    $('missionOptimizer').textContent = `${dec.optimizer_status.replaceAll('_',' ')} · MILP/oracle ${dec.milp_oracle_agreement === true ? 'agree' : dec.milp_oracle_agreement === false ? 'check' : '—'}`;
    $('missionL5').textContent = v.l5;
    $('missionUncertainty').textContent = `${v.uncertainty_verdict.replaceAll('_',' ')} · next: ${v.best_next_measurement}`;
    $('contextRun').textContent = currentRun;
    $('contextMode').textContent = sourceLabel(m.source_mode);
    $('contextSuspect').textContent = d.target || '—';
    $('contextL5').textContent = v.l5;
    updateArtifactButtons();
  } catch(e) {
    console.error('Mission Control:', e);
  }
}

async function loadContract() {
  try {
    const x=await json('/api/data/contract');
    const c=x.data_contract;
    const modes=Object.entries(c.source_modes).map(([k,v])=>`<b>${k}</b>: ${v}`).join('<br>');
    $('contractText').innerHTML = `<p>${c.principle}</p><p><b>${c.full_engine_required_fields.length}</b> observable source fields support the full current engine; unit_index and total_processing_s can be derived deterministically.</p><p>${modes}</p><p><b>Real-world causal boundary:</b> ${c.real_world_causal_policy}</p><p>API: <code>POST /api/data/import/csv</code> · <code>POST /api/live/sessions</code> · <code>POST /api/live/sessions/{id}/events</code> · <code>POST /api/live/sessions/{id}/finalize</code></p>`;
  } catch(e) { if ($('contractText')) $('contractText').textContent=`Contract unavailable: ${e.message}`; }
}

async function loadPublicEvidence() {
  const state=$('publicEvidenceState');
  if (!state) return;
  state.textContent='Calculating…';
  try {
    const body=await json('/api/data/public-backbone');
    const c=body.case_study || {};
    const model=c.defect_risk_model || c;
    const rows=model.model_comparison || [];
    $('publicEvidenceDataset').textContent=String(body.dataset || '—').replaceAll('_',' ');
    $('publicEvidenceDatasetState').textContent=String(body.dataset_state || body.schema_validation || '—').replaceAll('_',' ');
    $('publicEvidenceChampion').textContent=model.selected_model || c.selected_model || 'REFERENCE ONLY';
    $('publicEvidenceAuc').textContent=num(model.holdout?.auc ?? c.holdout?.auc,3);
    $('publicEvidenceModels').innerHTML=rows.length ? rows.map(x=>`<tr><td><b>${x.model}</b></td><td>${x.holdout_rows ?? '—'}</td><td>${num(x.auc,3)}</td><td>${num(x.balanced_accuracy,3)}</td><td>${num(x.brier,3)}</td></tr>`).join('') : '<tr><td class="empty" colspan="5">No comparable classifier is active for this project; see the case-study metrics and holdout method in the evidence report.</td></tr>';
    $('publicEvidenceBoundary').textContent=body.claim_boundary || c.decision_impact || 'Human review required.';
    $('publicEvidenceSelection').textContent=`Selection rule: ${model.selection_metric || c.selection_metric || 'case-study-specific validated metric'} · human authority: ${body.human_authority || 'HUMAN_REVIEW'} · autonomous execution: ${body.autonomous_execution === false ? 'DISABLED' : 'REVIEW'}.`;
    state.textContent=c.status === 'ACTIVE' ? 'ACTIVE / REVIEWABLE' : String(c.status || 'REFERENCE').replaceAll('_',' ');
    publicEvidenceLoaded=true;
  } catch (e) {
    state.textContent='EVIDENCE UNAVAILABLE';
    $('publicEvidenceBoundary').textContent=`Evidence endpoint unavailable: ${e.message}`;
  }
}

async function loadFullRun() {
  await Promise.all([loadSummary(), loadRecords(), loadQuality(), loadIE(), loadInvestigation(), loadArena(), loadSimulationOverview(), loadOptimizerOverview(), loadActiveOverview(), loadControlPlan()]);
  await loadMissionControl();
}

async function importCsv(event) {
  event.preventDefault();
  if (!buildCompatible) { alert('Resolve KAIZEN system health before importing data.'); return; }
  const file=$('csvFile').files?.[0];
  if (!file) { alert('Choose a CSV file.'); return; }
  const activation=Number($('csvActivation').value);
  if (!Number.isInteger(activation) || activation < 1) { alert('Boundary unit must be a positive whole number.'); return; }
  const fd=new FormData();
  fd.append('file',file);
  fd.append('activation_unit',String(activation));
  fd.append('line_name',$('csvLineName').value.trim() || 'External Manufacturing Line');
  fd.append('source_mode',$('csvMode').value);
  fd.append('mapping_json','{}');
  $('csvImportBtn').disabled=true; $('csvImportBtn').textContent='MAPPING…';
  try {
    const res=await fetch(apiUrl('/api/data/import/csv'),{method:'POST',body:fd});
    const body=await res.json().catch(()=>({}));
    if (!res.ok) throw new Error(formatApiError(body.detail,res.status));
    currentRun=body.run_id; currentSourceMode=body.source_mode;
    $('runId').textContent=currentRun;
    resetTruthForNewRun();
    $('dataImportResult').textContent=`${body.source_mode} accepted: ${body.units.toLocaleString()} canonical records · boundary ${body.activation_unit} · full engine ready ${body.mapping_report.readiness.full_engine_ready ? 'YES' : 'NO'} · ${Object.keys(body.mapping_report.mapping).length} source columns mapped · fabricated fields 0.`;
    await loadFullRun();
    setWorkspace('mission');
  } catch(e) { $('dataImportResult').textContent=`IMPORT REJECTED: ${e.message}`; alert(e.message); }
  finally { $('csvImportBtn').disabled=false; $('csvImportBtn').textContent='IMPORT DATA'; }
}

async function replaySample() {
  if (!currentRun) return;
  $('replayBtn').disabled=true;
  try {
    const manifest=await json(`/api/runs/${currentRun}/replay/manifest`);
    const batch=await json(`/api/runs/${currentRun}/replay/events?offset=0&limit=30`);
    const events=batch.events || [];
    $('replayStatus').textContent=`Replay ready: ${manifest.events.toLocaleString()} canonical events. Playing first ${events.length}…`;
    let i=0;
    await new Promise(resolve=>{
      const timer=setInterval(()=>{
        if (i>=events.length) { clearInterval(timer); resolve(); return; }
        const r=events[i++];
        $('replayStatus').textContent=`REPLAY ${i}/${events.length} · ${r.unit_id} · ${r.machine_id} · ${r.product_variant} · torque ${num(r.torque_measured_nm,2)} · ${r.observed_defect ? r.defect_type : 'PASS'}`;
      },55);
    });
    $('replayStatus').textContent=`Replay sample complete. Source values were not changed; playback speed affects presentation only.`;
  } catch(e) { alert(e.message); }
  finally { $('replayBtn').disabled=false; }
}

function openReport() {
  if (!currentRun) { alert('Create or import a run first.'); return; }
  window.open(`/api/runs/${currentRun}/report`,'_blank','noopener');
}

$('csvImportForm')?.addEventListener('submit',importCsv);
$('exportCsvBtn')?.addEventListener('click',()=>{if(currentRun) location.href=`/api/runs/${currentRun}/export/csv`;});
$('exportSnapshotBtn')?.addEventListener('click',()=>{if(currentRun) location.href=`/api/runs/${currentRun}/export/snapshot`;});
$('openReportBtn')?.addEventListener('click',openReport);
$('reportBtn')?.addEventListener('click',openReport);
$('replayBtn')?.addEventListener('click',replaySample);

updateArtifactButtons();
loadContract();
setWorkspace('mission',{scroll:false});
