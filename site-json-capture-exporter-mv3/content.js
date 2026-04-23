(() => {
  const script = document.createElement("script");
  script.src = chrome.runtime.getURL("page_hook.js");
  script.onload = () => script.remove();
  (document.head || document.documentElement).appendChild(script);

  let latestCaptures = [];

  window.addEventListener("message", (event) => {
    if (event.source !== window || !event.data) return;
    if (event.data.source !== "site-json-capture") return;

    if (event.data.type === "CAPTURES_LIST") {
      latestCaptures = event.data.payload || [];
    }

    if (event.data.type === "CAPTURE_ADDED") {
      latestCaptures.push(event.data.payload);
    }

    chrome.runtime.sendMessage({
      type: "PAGE_EVENT",
      event: event.data.type,
      payload: event.data.payload || null
    }).catch(() => {});
  });

  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (!message || !message.type) return;

    if (message.type === "GET_CAPTURES") {
      sendResponse({ captures: latestCaptures });
    }

    if (message.type === "DOWNLOAD_LATEST") {
      if (latestCaptures.length === 0) {
        sendResponse({ ok: false, error: "No captures available." });
        return;
      }
      window.postMessage(
        { source: "site-json-capture-extension", type: "DOWNLOAD_LATEST" },
        "*"
      );
      sendResponse({ ok: true });
    }

    if (message.type === "DOWNLOAD_ALL") {
      if (latestCaptures.length === 0) {
        sendResponse({ ok: false, error: "No captures available." });
        return;
      }
      window.postMessage(
        { source: "site-json-capture-extension", type: "DOWNLOAD_ALL" },
        "*"
      );
      sendResponse({ ok: true });
    }

    if (message.type === "CLEAR_CAPTURES") {
      latestCaptures = [];
      window.postMessage(
        { source: "site-json-capture-extension", type: "CLEAR_CAPTURES" },
        "*"
      );
      sendResponse({ ok: true });
    }
  });
})();