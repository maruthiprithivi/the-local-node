/* Progress is a learner's self-check on this device, never proof that tests passed. */
(() => {
  const key = 'the-local-node:harness-progress:v1';
  const spine = window.HARNESS_SPINE ?? [];
  let done = new Set();
  try {
    const stored = JSON.parse(localStorage.getItem(key) ?? '[]');
    if (Array.isArray(stored)) done = new Set(stored.filter(id => spine.some(step => step.id === id)));
  } catch { /* Page remains usable when storage is unavailable. */ }
  const save = () => { try { localStorage.setItem(key, JSON.stringify([...done])); } catch {} };
  const current = spine.find(step => location.pathname.replace(/\/$/, '') === step.route.replace(/\/$/, ''));
  const host = document.querySelector('[data-harness-progress]');
  if (!host) return;
  const status = document.createElement('output');
  status.setAttribute('aria-live', 'polite');
  const continueLink = document.createElement('a');
  const refresh = () => {
    const required = spine.filter(step => !step.optional);
    const optional = spine.filter(step => step.optional);
    status.textContent = `${required.filter(step => done.has(step.id)).length} of ${required.length} core/advanced lessons and ${optional.filter(step => done.has(step.id)).length} of ${optional.length} optional modules self-checked on this device. This does not record test results.`;
    const next = required.find(step => !done.has(step.id)) ?? optional.find(step => step.id !== 'lesson-00' && !done.has(step.id)) ?? spine[0];
    continueLink.href = next.route;
    continueLink.textContent = `Continue: ${next.title}`;
  };
  if (current) {
    const button = document.createElement('button');
    const label = () => { button.textContent = done.has(current.id) ? 'Remove my self-check' : 'I completed the acceptance checks'; };
    button.addEventListener('click', () => {
      if (done.has(current.id)) done.delete(current.id); else done.add(current.id);
      save(); label(); refresh();
    });
    label(); host.append(button);
  }
  const reset = document.createElement('button');
  reset.textContent = 'Clear progress on this device';
  reset.addEventListener('click', () => {
    if (!confirm('Clear your self-checked lesson progress on this device?')) return;
    done.clear(); save(); location.reload();
  });
  host.append(continueLink, reset, status); refresh();
})();
