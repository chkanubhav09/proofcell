const form = document.getElementById('task-form');
const ta = document.getElementById('task');
async function start(task) {
  const r = await fetch('/api/runs', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({task})});
  const d = await r.json();
  if (d.run_id) location.href = '/runs/' + d.run_id;
}
form.addEventListener('submit', e => { e.preventDefault(); start(ta.value); });
document.querySelectorAll('.sample').forEach(b => b.addEventListener('click', () => { ta.value = b.dataset.task; }));

const drillBtn = document.getElementById('drill');
const drillList = document.getElementById('drill-list');
drillBtn.addEventListener('click', async () => {
  if (!drillList.classList.contains('hidden')) { drillList.classList.add('hidden'); return; }
  const r = await fetch('/api/drill/scenarios');
  const d = await r.json();
  drillList.innerHTML = '<span>Pick a hostile scenario - each runs with a canned drill-authored plan, so the walls (not model luck) are what gets tested:</span>';
  d.scenarios.forEach(s => {
    const b = document.createElement('button');
    b.className = 'drill-scenario';
    b.innerHTML = `<strong>${s.title}</strong><small>${s.expectation}</small>`;
    b.addEventListener('click', async () => {
      const rr = await fetch('/api/drill/' + s.id, {method:'POST'});
      const dd = await rr.json();
      if (dd.run_id) location.href = '/runs/' + dd.run_id;
    });
    drillList.appendChild(b);
  });
  drillList.classList.remove('hidden');
});
