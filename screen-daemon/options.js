document.getElementById("save").addEventListener("click", () => {
  const apiBase = document.getElementById("api-base").value;
  const pollInterval = parseInt(document.getElementById("poll-interval").value, 10);
  browser.storage.local.set({ apiBase, pollInterval });
  document.getElementById("saved-msg").style.display = "block";
  setTimeout(() => document.getElementById("saved-msg").style.display = "none", 3000);
});

browser.storage.local.get(["apiBase", "pollInterval"]).then(r => {
  if (r.apiBase) document.getElementById("api-base").value = r.apiBase;
  if (r.pollInterval) document.getElementById("poll-interval").value = r.pollInterval;
});