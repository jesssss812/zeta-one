const $ = (id) => document.getElementById(id);
const text = (id, value) => { $(id).textContent = value; };
const pretty = (value) => String(value ?? 'Not evaluated').replaceAll('_', ' ');
const money = (value) => value ? new Intl.NumberFormat('en-US', {style: 'currency', currency: value.currency}).format(value.amount / 100) : 'Not available';
const stages = [
  ['CODE SETS THE BOUNDARIES', 'Authority is not a prediction.', 'Verify the agent and check the business’s authorization: scope, limits, expiry, and revocation. A model cannot override a hard constraint.', 'Signed proposal → Identity → Authorization', 'Deterministic checks precede contextual risk assessment.'],
  ['STRUCTURED INTELLIGENCE', 'Pay for a decision, not an essay.', 'Use Jev for targeted risk questions about the payment and its context. Structured probabilities inform policy without generating a long response for every action.', 'Payment context → Jev → Typed risk signals', 'Jev is the intended inexpensive tier. Savings and calibration must be measured on our scenarios.'],
  ['SELECTIVE ESCALATION', 'More reasoning when it earns its place.', 'Reserve a stronger model for cases that need deeper assessment. Match human verification to the uncertainty instead of interrupting every legitimate payment.', 'Uncertain case → Deeper assessment → Policy decision', 'Models inform risk. Humans retain consequential review decisions.']
];
function selectStage(index) {
  const ids = ['stage-label','stage-title','stage-copy','stage-diagram','stage-foot'];
  ids.forEach((id, i) => text(id, stages[index][i]));
  document.querySelectorAll('[data-stage]').forEach((button, i) => {
    button.setAttribute('aria-selected', String(i === index)); button.tabIndex = i === index ? 0 : -1;
  });
  $('stage-panel').setAttribute('aria-labelledby', `stage-${index}`);
}
document.querySelectorAll('[data-stage]').forEach((button) => {
  button.addEventListener('click', () => selectStage(Number(button.dataset.stage)));
  button.addEventListener('keydown', (event) => {
    const current = Number(button.dataset.stage);
    const index = {ArrowRight: (current + 1) % 3, ArrowDown: (current + 1) % 3, ArrowLeft: (current + 2) % 3, ArrowUp: (current + 2) % 3, Home: 0, End: 2}[event.key];
    if (index !== undefined) { event.preventDefault(); selectStage(index); $(`stage-${index}`).focus(); }
  });
});
selectStage(0);
const scenario = 'vendor_payment_method_changed';
let busy = false;
function resetResult() {
  $('result').hidden = true; $('intro').hidden = false; text('status', '');
  $('connection').hidden = $('mode').value !== 'engine';
  $('run').textContent = $('mode').value === 'fixture' ? 'Explore illustrative decision ↗' : 'Run scenario through engine ↗';
  text('mode-note', $('mode').value === 'fixture' ? 'Illustrative result · No model runs or payments are made.' : 'Runs the synthetic scenario. Payment execution remains simulated.');
}
$('mode').addEventListener('change', resetResult);
if (!['localhost','127.0.0.1'].includes(location.hostname) || location.port === '8000') $('engine-url').value = location.origin;
function element(tag, content, className) {
  const node = document.createElement(tag); if (content != null) node.textContent = content; if (className) node.className = className; return node;
}
function check(number, title, description, outcome) {
  const row = element('div', null, 'check'); row.append(element('span', number));
  const body = element('div', title); body.append(element('small', description)); row.append(body, element('span', outcome)); return row;
}
function render(data) {
  const record = data.decision_record;
  if (!record || !data.context || !data.proposal || !['allow','challenge','block'].includes(record.decision) || typeof data.illustrative !== 'boolean' || record.execution?.simulated !== true || !record.identity || !record.authorization || !record.risk) throw new Error('The engine response does not match the simulated demo contract.');
  const context = data.context;
  text('vendor', context.counterparty.name); text('amount', money(data.proposal.amount)); text('business', context.business.name);
  text('bill-memo', context.bill?.memo ?? data.proposal.memo); text('history', `${context.payment_history.count} prior payments`);
  text('change-summary', context.payment_method_history?.[0]?.summary ?? 'No payment-method changes recorded.');
  text('result-source', data.illustrative ? 'ILLUSTRATIVE RESULT / NO MODEL RUN' : 'ENGINE RESULT / SYNTHETIC SCENARIO');
  text('verdict', {allow: 'Allow payment', challenge: 'Verification needed', block: 'Payment blocked'}[record.decision]);
  text('execution', `${pretty(record.execution.status)} · simulated`);
  const authorization = record.authorization;
  const authState = !authorization.snapshot ? 'Not evaluated' : authorization.violations.length ? 'Violation' : 'Within scope';
  $('checks').replaceChildren(
    check('01', 'Identity', record.identity.claimed_agent_id ?? 'No verified agent', pretty(record.identity.result)),
    check('02', 'Authorization', authorization.snapshot ? `Authorization ${authorization.authorization_id} · version ${authorization.version}` : 'No authorization evaluated', authState),
    check('03', 'Transaction risk', record.risk.tiers_run.length ? record.risk.tiers_run.map(pretty).join(' → ') : 'No risk tier ran', pretty(record.risk.level))
  );
  text('challenge', record.challenge ? `${record.challenge.user_sees} Routed to ${record.challenge.routed_to}.` : `Decision reasons: ${record.reasons.map(pretty).join('; ')}.`);
  text('cost', record.cost?.usd == null ? 'Not measured' : `$${Number(record.cost.usd).toFixed(6)}`);
  text('latency', record.latency_ms?.total == null ? 'Not measured' : `${record.latency_ms.total} ms`);
  text('tiers', record.risk.tiers_run.length ? record.risk.tiers_run.map(pretty).join(' + ') : 'None');
  const evidence = $('evidence'); evidence.replaceChildren();
  const records = [context.counterparty, context.bill, ...(context.payment_method_history ?? []), ...(context.payment_history.recent ?? [])].filter(Boolean);
  for (const signal of record.risk.signals) {
    const item = element('div', null, 'evidence-row'); item.append(element('strong', pretty(signal.name)), element('small', `${pretty(signal.severity)} · ${pretty(signal.source)}`));
    for (const ref of signal.evidence) {
      const link = element('a', ref, 'evidence-link'); link.href = `#evidence-${encodeURIComponent(ref)}`; item.append(link, document.createTextNode(' '));
    }
    evidence.append(item);
  }
  for (const item of records) {
    const row = element('div', null, 'evidence-row'); row.id = `evidence-${encodeURIComponent(item.id)}`;
    row.append(element('strong', item.id), element('p', item.summary ?? item.document_excerpt ?? (item.amount ? `${money(item.amount)} · ${item.posted_at}` : item.name)));
    evidence.append(row);
  }
  if (record.risk.model_rationale) evidence.append(element('strong', 'Model output'), element('p', record.risk.model_rationale));
  text('raw', JSON.stringify(record, null, 2));
  $('intro').hidden = true; $('result').hidden = false; $('result').focus({preventScroll: true});
}
$('run').addEventListener('click', async () => {
  if (busy) return;
  busy = true; $('run').disabled = true; $('mode').disabled = true; $('result').hidden = true;
  text('status', $('mode').value === 'fixture' ? 'Loading illustrative evidence…' : 'Waiting for the decision engine…');
  try {
    let url = new URL(`./fixtures/${scenario}.json`, location.href); let options = {};
    if ($('mode').value === 'engine') {
      const base = new URL($('engine-url').value);
      if (base.username || base.password || base.search || base.hash || !['http:','https:'].includes(base.protocol)) throw new Error('Use an engine URL without credentials, query parameters, or fragments.');
      if (base.origin !== location.origin && !['localhost','127.0.0.1','[::1]'].includes(base.hostname)) throw new Error('Use a local engine or this site’s own origin.');
      url = new URL(`/v1/scenarios/${scenario}/run`, base); options = {method:'POST'};
    }
    const response = await fetch(url, {...options, signal: AbortSignal.timeout(60000), credentials:'omit'});
    if (!response.ok) throw new Error(`Request failed (${response.status}). Check that the demo engine is running and allows this site’s origin.`);
    render(await response.json()); text('status', '');
    $('run').textContent = $('mode').value === 'fixture' ? 'Replay illustrative decision ↗' : 'Run scenario again ↗';
  } catch (error) {
    text('status', error.name === 'TimeoutError' ? 'The engine timed out. Retry when it is ready; no illustrative result was substituted.' : `Unable to load decision. ${error.message}. Check the engine URL, start the demo engine, and confirm CORS permits this origin.`);
  } finally { busy = false; $('run').disabled = false; $('mode').disabled = false; }
});
