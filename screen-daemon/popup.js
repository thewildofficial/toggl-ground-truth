// Popup — shows today's tracked time + config
document.getElementById("save").addEventListener("click", () => {
  const url = document.getElementById("api-base").value;
  browser.storage.local.set({ apiBase: url });
  document.getElementById("save").textContent = "Saved!";
  setTimeout(() => document.getElementById("save").textContent = "Save", 1500);
});

const today = new Date().toISOString().slice(0, 10);
browser.storage.local.get("apiBase").then(r => {
  if (r.apiBase) document.getElementById("api-base").value = r.apiBase;
});

browser.runtime.sendMessage({ type: "getLog", date: today }).then(resp => {
  const status = document.getElementById("status");
  if (!resp || !resp.log || resp.log.length === 0) {
    status.innerHTML = '<div class="row dim">No tracked time today.</div>';
    return;
  }
  const merged = {};
  for (const e of resp.log) {
    merged[e.category] = (merged[e.category] || 0) + e.seconds;
  }
  status.innerHTML = Object.entries(merged)
    .sort((a, b) => b[1] - a[1])
    .map(([cat, secs]) => {
      const mins = Math.round(secs / 60);
      const label = mins >= 1 ? `${mins}m` : `${secs}s`;
      return `<div class="row"><span class="cat">${cat}</span><span>${label}</span></div>`;
    })
    .join("");
});