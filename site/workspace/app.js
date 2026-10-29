import {createPreview} from './preview.js';

const $ = (id) => document.getElementById(id);
const node = (tag, attrs = {}, ...children) => {
  const element = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key.startsWith('on')) element.addEventListener(key.slice(2), value);
    else if (key === 'text') element.textContent = value;
    else if (value !== undefined && value !== null) element.setAttribute(key, String(value));
  }
  for (const child of children.flat(Infinity)) if (child != null) element.append(child instanceof Node ? child : document.createTextNode(String(child)));
  return element;
};
const money = (value) => {
  if (!value || !Number.isFinite(value.amount)) return 'Amount unavailable';
  try { return new Intl.NumberFormat('en-US', {style:'currency', currency:value.currency || 'USD'}).format(value.amount / 100); }
  catch { return `${(value.amount / 100).toFixed(2)} ${value.currency || ''}`; }
};
const human = (value) => String(value ?? 'Not recorded').replaceAll('_', ' ');
const date = (value) => value ? new Date(value).toLocaleString([], {month:'short',day:'numeric',hour:'numeric',minute:'2-digit'}) : 'Time not recorded';
const json = (value) => JSON.stringify(value, null, 2);
const disclosure = (title, content) => node('details', {}, node('summary', {text:title}), content);
const section = (title, ...body) => node('section', {class:'section'}, node('div', {class:'section-heading'}, node('h3', {text:title})), ...body);
const badge = (decision) => node('span', {class:`badge ${['allow','challenge','block'].includes(decision) ? decision : ''}`,text:human(decision)});
const metric = (label, value) => node('div', {}, node('span', {text:label}), value);
let adapter, workspace, selected, working = false;

function createLocal(config) {
  const base = (config.api_base || '/v1/workspace').replace(/\/$/, '');
  async function request(path, payload) {
    const response = await fetch(base + path, payload === undefined ? {cache:'no-store'} : {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
    const text = await response.text();
    let result;
    try { result = JSON.parse(text); } catch { throw new Error(`The workspace returned an unreadable response (${response.status}).`); }
    if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : json(result.detail || result));
    return result;
  }
  return {state:() => request(''), act:(action,payload) => request('/' + action,payload)};
}

function error(message) { $('error').textContent = message; $('error').hidden = !message; }
function setWorking(value, label = '') {
  working = value; $('busy').textContent = value ? label : '';
  document.querySelectorAll('button, select, textarea').forEach((control) => {
    control.disabled = value || control.dataset.unavailable === 'true';
  });
  $('detail').setAttribute('aria-busy', String(value));
}
async function act(action, payload = {}) {
  if (working) return;
  error(''); setWorking(true, action === 'assemble' ? 'Gathering the case…' : 'Updating workspace…');
  try {
    workspace = await adapter.act(action, payload);
    selected = workspace.selected_id || (workspace.payments.some(p => p.id === selected) ? selected : workspace.payments[0]?.id);
    render();
  } catch (e) { error(e.message || String(e)); }
  finally { setWorking(false); }
}
function recipeDescription() { $('recipe-description').textContent = workspace?.recipes.find(r => r.id === $('recipe').value)?.description || ''; }
function render() {
  const preview = workspace.mode === 'preview';
  $('mode').textContent = preview ? 'Recorded public preview' : workspace.mode === 'live' ? 'Local sandbox · models enabled' : 'Local sandbox · deterministic rules';
  $('mode-description').textContent = preview ? 'Explore prepared results from the real engine. Random selects a recorded example; no decisions or models run here.' : workspace.mode === 'live' ? 'Each new payment gets a fresh assessment. Models run only when the engine needs them. Assemble case explicitly calls the review assistant.' : 'Each new payment gets a fresh assessment using deterministic rules. Case assembly gathers evidence without model calls.';
  $('legacy').hidden = preview;
  $('count').textContent = workspace.payments.length;
  const recipe = $('recipe').value;
  $('recipe').replaceChildren(...workspace.recipes.map(r => node('option', {value:r.id,text:r.title})));
  if (workspace.recipes.some(r => r.id === recipe)) $('recipe').value = recipe;
  recipeDescription();
  $('payments').replaceChildren(...workspace.payments.map(p => {
    const s = p.summary || {};
    return node('button', {class:'payment-row',type:'button','aria-current':p.id === selected,onclick:() => {if (!working) {selected = p.id; render();}}},
      node('span', {class:'row-top'}, node('strong', {text:s.vendor || p.title}), badge(s.decision)),
      node('span', {class:'row-bottom'}, node('span', {text:p.title}), node('b', {text:money(s.amount)})));
  }));
  $('inbox-empty').hidden = workspace.payments.length > 0;
  $('provenance').textContent = workspace.provenance || '';
  const payment = workspace.payments.find(p => p.id === selected);
  if (payment) renderDetail(payment, preview);
  else $('detail').replaceChildren(node('div', {class:'empty-detail'}, node('span', {class:'empty-mark',text:'ζ'}), node('h2', {text:'Start with a payment.'}), node('p', {text:'Add a scenario to see the gateway separate identity, authorization, and risk.'})));
}
function renderDetail(payment, preview) {
  const s = payment.summary || {}, r = payment.record || {}, ctx = r.context || {}, proposal = r.proposal || {};
  const decision = ['allow','challenge','block'].includes(s.decision) ? s.decision : '';
  const parts = s.parts || [];
  const header = node('div', {class:'detail-head'}, node('div', {}, node('div', {class:'eyebrow',text:payment.title}), node('h2', {text:s.vendor || 'Unknown payee'}), node('p', {class:'subtle',text:`${date(s.created_at)} · ${human(s.status)}`})), node('div', {class:'payment-amount'}, money(s.amount), node('small', {text:'SIMULATED PAYMENT'})));
  const verdict = node('div', {class:`verdict ${decision}`}, node('div',{class:'eyebrow',text:'ORIGINAL GATEWAY DECISION'}), badge(s.decision), node('div', {}, node('strong', {text:decision === 'challenge' && s.status === 'executed' ? 'Approved · paid (simulated)' : decision === 'challenge' && s.status === 'blocked' ? 'Review closed · payment blocked' : s.action || human(s.decision)}), node('p', {text:s.headline || 'Inspect the evidence record for the decision reasons.'})));
  const checks = node('div', {class:'parts'}, ['identity','authorization','risk'].map((question, i) => {
    const part = parts.find(p => p.question === question);
    return node('div', {class:'part'}, node('div', {class:'eyebrow',text:`0${i+1} / ${question.toUpperCase()}`}), node('p', {}, node('span', {class:'part-symbol',text:part ? (part.ok ? '✓' : '○') : '—'}), part?.text || 'Not reached by the engine'));
  }));
  const models = s.models || [];
  const modelNames = (r.risk?.tier_results || []).filter(t => t.model).map(t => t.model);
  const metrics = node('div', {class:'metrics'}, metric('TOTAL ASSESSMENT', s.total_ms == null ? 'Not recorded' : `${Number(s.total_ms).toFixed(0)} ms`), metric('MODELS RUN', modelNames.length ? [...new Set(modelNames)].join(', ') : models.length ? models.map(human).join(', ') : 'None · deterministic decision'), metric('POLICY',r.policy_version || r.policy?.version || 'See evidence record'));
  const invoice = ctx.bill?.document_excerpt;
  const history = ctx.payment_history;
  const context = node('div', {class:'context-grid section'}, node('div', {class:'context-card'}, node('h3', {text:'Invoice excerpt'}), invoice ? [node('div', {class:'untrusted',text:'UNTRUSTED DOCUMENT CONTENT'}), node('blockquote', {text:invoice})] : node('p', {text:'No invoice excerpt was available in this decision.'})), node('div', {class:'context-card'}, node('h3', {text:'Payment context'}), node('p', {text:proposal.memo || proposal.agent_rationale || 'The proposal and source records are available below.'}), history ? [node('p',{class:'subtle',text:`${history.count ?? 0} prior payments${history.median_amount ? ' · Typical amount ' + money(history.median_amount) : ''}`}), disclosure('Payment history', node('div',{}, (history.recent || []).map(item => node('p',{text:`${date(item.posted_at)} · ${money(item.amount)} · ${item.id}`})), node('pre',{text:json(history)})))] : node('p', {class:'subtle',text:'No payment history included in this record.'})));
  const caseSection = renderCase(payment, preview);
  const timeline = section('Case timeline', node('ol', {class:'timeline'}, (payment.events || []).map(e => node('li', {}, node('strong', {text:e.title}), node('p', {text:typeof e.detail === 'string' ? e.detail : json(e.detail)})))));
  const evidence = disclosure('Inspect the full evidence record', node('pre', {text:json(r)}));
  const performance = disclosure('Timings & model details', node('pre', {text:json({stages:s.stages, models:s.models, risk_tiers:r.risk?.tiers_run, risk:r.risk?.tier_results, latency_ms:r.latency_ms})}));
  $('detail').replaceChildren(header,verdict,checks,metrics,context,caseSection,timeline,review(payment,preview),evidence,performance,node('p', {class:'provenance',text:payment.provenance || workspace.provenance}));
}
function actionButton(label, action, payment, preview, extra = {}) {
  const button = node('button', {class:'secondary',type:'button',onclick:() => act(action,{id:payment.id,...extra}),text:label});
  if (preview) { button.disabled = true; button.dataset.unavailable = 'true'; button.title = 'Available in the local sandbox only.'; }
  return button;
}
function renderCase(payment, preview) {
  const outer = payment.case_file;
  const f = outer?.case_file;
  const result = section('Review assistant', node('p', {class:'subtle',text:'Gathers and organizes evidence for a person. The assistant does not decide whether to pay or confirm fraud.'}));
  if (preview) result.append(node('p', {class:'case-note',text:'Case assembly and human review are available in the local sandbox. This public preview displays recorded evidence only.'}));
  else if (!outer) result.append(node('p', {class:'case-note',text:workspace.mode === 'live' ? 'Assemble a case to ask the assistant to gather and summarize the evidence. This action may call models.' : 'Assemble a case to gather the underlying records. The model assistant is disabled in rules mode.'}));
  result.append(node('div', {class:'actions'}, actionButton(outer ? 'Refresh case' : 'Assemble case', 'assemble', payment, preview)));
  if (!outer) return result;
  if (f?.summary) result.append(node('p', {text:f.summary}));
  if (outer.errors?.length) result.append(node('p', {class:'case-note',text:outer.errors.map(e => typeof e === 'string' ? e : json(e)).join(' · ')}));
  for (const [key,label] of [['verified_facts','Facts with sources'],['inferences','Inferences'],['contradictions','Contradictions'],['open_questions','Open questions'],['missing_evidence','Missing evidence']]) {
    if (!f?.[key]?.length) continue;
    result.append(disclosure(label,node('ul',{class:'case-list'},f[key].map(item => node('li',{}, typeof item === 'string' ? item : item.statement || json(item), item.sources?.length ? node('small',{text:'Sources: ' + item.sources.join(', ')}) : null,item.basis ? node('small',{text:'Basis: ' + item.basis}) : null)))));
  }
  if (f?.timeline?.length) result.append(disclosure('Assistant timeline',node('ol',{class:'timeline'},f.timeline.map(e => node('li',{},node('strong',{text:e.at}),node('p',{text:e.event}))))));
  if (outer.research) result.append(disclosure('Vendor research & sources',node('pre',{text:json(outer.research)})));
  result.append(disclosure('Complete case & assistant usage',node('pre',{text:json(outer)})));
  return result;
}
function review(payment, preview) {
  const box = section('Human review');
  if (preview) {box.append(node('p',{class:'subtle',text:'Record findings, resolve held payments, and repeat an assessment in the local sandbox. No review outcomes are fabricated in this preview.'})); return box;}
  const finding = node('select',{id:'finding'}, [['legitimate','Legitimate'],['payee_fraud','Payee fraud'],['manipulated_agent','Manipulated agent'],['unauthorized','Unauthorized']].map(([value,text])=>node('option',{value,text})));
  const verification = node('select',{id:'verification',required:''}, node('option',{value:'',text:'Choose verification method…'}), [['callback_known_number','Called a number already on file'],['vendor_portal','Vendor portal'],['bank_confirmation','Bank confirmation'],['signed_customer_attestation','Signed customer attestation'],['customer_report','Customer report only (a claim)'],['none','Not verified']].map(([value,text])=>node('option',{value,text})));
  const note = node('textarea',{id:'review-note',placeholder:'What you established, how, and from whom',maxlength:2000});
  const form = node('form',{class:'review-form'}, node('div',{},node('label',{for:'finding',text:'Finding'}),finding),node('div',{},node('label',{for:'verification',text:'How was it verified?'}),verification),node('div',{class:'full'},node('label',{for:'review-note',text:'Review note'}),note),node('p',{class:'subtle full',text:'A customer report records a claim. Only a verified finding changes risk. Approval and rejection here are simulated.'}));
  const fields = () => ({id:payment.id,finding:finding.value,verification:verification.value,note:note.value});
  form.addEventListener('submit',e=>{e.preventDefault();act('outcome',fields());});
  const actions = node('div',{class:'actions full'},node('button',{class:'primary',type:'submit',text:'Record finding'}));
  if (payment.summary?.decision === 'challenge' && payment.summary?.status === 'held') {
    for (const [outcome,label] of [['approve','Approve held payment'],['reject','Reject held payment']]) actions.append(node('button',{class:'secondary',type:'button',text:label,onclick:()=>{if(form.reportValidity())act('resolve',{...fields(),outcome});}}));
  }
  actions.append(actionButton('Repeat assessment','repeat',payment,false));
  form.append(actions);box.append(form);
  if (payment.summary?.outcome) box.append(disclosure('Latest recorded finding',node('pre',{text:json(payment.summary.outcome)})));
  return box;
}
$('recipe').addEventListener('change',recipeDescription);
$('add-form').addEventListener('submit',e=>{e.preventDefault();if($('recipe').value)act('add',{recipe_id:$('recipe').value});});
$('random').addEventListener('click',()=>act('random'));
$('reset').addEventListener('click',()=>act('reset'));
setWorking(true,'Loading workspace…');
try {
  const response = await fetch('./config.json',{cache:'no-store'});
  if (!response.ok) throw new Error(`Could not load workspace configuration (${response.status}).`);
  const config = await response.json();
  const explanation = config.explanation_url || '../';
  document.querySelector('.brand').href = explanation;
  document.querySelector('nav a').href = explanation + '#approach';
  document.querySelector('footer a').href = explanation;
  if (!['preview','live','rules'].includes(config.mode)) throw new Error('Unknown workspace mode.');
  adapter = config.mode === 'preview' ? await createPreview() : createLocal(config);
  workspace = await adapter.state(); selected = workspace.selected_id || workspace.payments[0]?.id; render();
} catch (e) { error(e.message || String(e)); $('mode').textContent='Workspace unavailable'; $('mode-description').textContent='Check the connection and reload to try again.'; }
finally { setWorking(false); if (!adapter || !workspace) document.querySelectorAll('button,select').forEach(e=>e.disabled=true); }
