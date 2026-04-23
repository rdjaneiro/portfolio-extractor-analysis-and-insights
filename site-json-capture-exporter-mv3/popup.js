async function getActiveTab() {
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  return tabs[0];
}

function renderCaptures(captures) {
  const status = document.getElementById("status");
  const list = document.getElementById("list");

  if (!captures || captures.length === 0) {
    status.textContent = "No captured responses found on this page yet.";
    list.innerHTML = "";
    return;
  }

  status.textContent = `${captures.length} capture(s) available.`;
  list.innerHTML = captures
    .slice()
    .reverse()
    .map(
      (c) => `
        <div class="item">
          <div><strong>${c.filename}</strong></div>
          <div>${new Date(c.capturedAt).toLocaleString()}</div>
        </div>
      `
    )
    .join("");
}

async function sendToActiveTab(message) {
  const tab = await getActiveTab();
  if (!tab?.id) throw new Error("No active tab found.");
  return chrome.tabs.sendMessage(tab.id, message);
}

async function refreshCaptures() {
  try {
    const response = await sendToActiveTab({ type: "GET_CAPTURES" });
    renderCaptures(response?.captures || []);
  } catch (e) {
    document.getElementById("status").textContent =
      "Open the target site in the active tab first.";
    document.getElementById("list").innerHTML = "";
  }
}

document.getElementById("refresh").addEventListener("click", refreshCaptures);

document.getElementById("downloadLatest").addEventListener("click", async () => {
  const res = await sendToActiveTab({ type: "DOWNLOAD_LATEST" });
  if (res && !res.ok) document.getElementById("status").textContent = res.error;
});

document.getElementById("downloadAll").addEventListener("click", async () => {
  const res = await sendToActiveTab({ type: "DOWNLOAD_ALL" });
  if (res && !res.ok) document.getElementById("status").textContent = res.error;
});

document.getElementById("clear").addEventListener("click", async () => {
  await sendToActiveTab({ type: "CLEAR_CAPTURES" });
  renderCaptures([]);
});

refreshCaptures();