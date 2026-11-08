const stepsEl = document.getElementById('steps');
const ledgerEl = document.getElementById('ledger');
const statusEl = document.getElementById('status');
const approvalEl = document.getElementById('approval');
const es = new EventSource(`/api/runs/${RUN_ID}/stream`);
es.onmessage = async (m) => {
  const ev = JSON.parse(m.data);
  if (ev.kind === 'end') { statusEl.textContent = ev.status; checkVerify(); es.close(); return; }
  const li = document.createElement('li');
  li.textContent = `#${ev.seq} ${ev.kind} ${ev.hash.slice(0,12)}…`;
  ledgerEl.appendChild(li);
  if (ev.kind === 'step_start') {
    const s = document.createElement('li');
    s.id = `step-${ev.payload.index}`;
    s.textContent = `▶ ${ev.payload.label || ev.payload.kind}`;
    stepsEl.appendChild(s);
  }
  if (ev.kind === 'step_result') {
    const s = document.getElementById(`step-${ev.payload.step_index}`);
    if (s) s.innerHTML = `<span class="badge-ok">✔</span> ${ev.payload.label} (exit ${ev.payload.exit_code}, ${ev.payload.duration_s}s)`;
  }
  if (ev.kind === 'blocked') {
    const s = document.createElement('li');
    s.innerHTML = `<span class="badge-blocked">⛔ BLOCKED</span> ${ev.payload.label}: ${ev.payload.reason}`;
    stepsEl.appendChild(s);
  }
  if (ev.kind === 'note' && /held for approval/.test(ev.payload.msg || '')) approvalEl.classList.remove('hidden');
};
document.getElementById('approve-btn')?.addEventListener('click', async () => {
  await fetch(`/api/runs/${RUN_ID}/approve`, {method:'POST'});
  approvalEl.classList.add('hidden');
});
async function checkVerify() {
  const r = await fetch(`/api/runs/${RUN_ID}/verify`);
  const d = await r.json();
  document.getElementById('verify').textContent = d.valid ? `valid ✔ (${d.events} events)` : 'INVALID ✘';
}
checkVerify();
