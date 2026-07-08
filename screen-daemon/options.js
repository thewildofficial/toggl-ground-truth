document.getElementById("save").addEventListener("click", () => {
  const apiBase = document.getElementById("api-base").value;
  const apiToken = document.getElementById("api-token").value;
  const pollInterval = parseInt(document.getElementById("poll-interval").value, 10);
  browser.storage.local.set({ apiBase, apiToken, pollInterval });
  document.getElementById("saved-msg").style.display = "block";
  setTimeout(() => document.getElementById("saved-msg").style.display = "none", 3000);
});

browser.storage.local.get(["apiBase", "pollInterval", "apiToken"]).then(r => {
  if (r.apiBase) document.getElementById("api-base").value = r.apiBase;
  if (r.apiToken) document.getElementById("api-token").value = r.apiToken;
  if (r.pollInterval) document.getElementById("poll-interval").value = r.pollInterval;
});