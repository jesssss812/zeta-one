const PREVIEW_NOTE = 'Example payments the real engine decided ahead of time from synthetic inputs, using its rules. No model calls; Surprise me picks another example.';
const clone = value => JSON.parse(JSON.stringify(value));

export async function createPreview() {
  const response = await fetch(new URL('./data.json', import.meta.url));
  if (!response.ok) throw new Error(`Could not load the example payments (${response.status}).`);
  const source = await response.json();
  if (!Array.isArray(source.payments) || source.payments.length < 3 || !Array.isArray(source.recipes)) throw new Error('The example payments are incomplete.');
  const prepared = clone(source.payments);
  let current;
  let sequence = 0;
  const reset = () => {
    current = clone(source);
    current.mode = 'preview';
    current.provenance = PREVIEW_NOTE;
    const initial = ['routine', 'bank-change', 'over-limit'].map(id => prepared.find(item => item.recipe_id === id)).filter(Boolean);
    current.payments = clone(initial.length === 3 ? initial : prepared.slice(0, 3));
    current.selected_id = current.payments[0]?.id ?? null;
    sequence = 0;
  };
  reset();
  return {
    async state() { return clone(current); },
    async act(action, payload = {}) {
      if (action === 'reset') reset();
      else if (action === 'add' || action === 'random') {
        const choices = action === 'add' ? prepared.filter(item => item.recipe_id === payload.recipe_id) : prepared;
        if (!choices.length) throw new Error('No prepared record exists for that recipe.');
        const payment = clone(choices[Math.floor(Math.random() * choices.length)]);
        payment.id = `${payment.id}-preview-${++sequence}`;
        payment.provenance = `${payment.provenance} Prepared record copied for browsing; no new assessment ran.`;
        current.payments.unshift(payment);
        current.selected_id = payment.id;
      } else throw new Error('Review actions require the local workspace. Public preview records are read-only; no assistant, feedback, or payment action ran.');
      return clone(current);
    },
  };
}
