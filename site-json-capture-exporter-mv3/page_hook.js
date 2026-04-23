(() => {
  const CAPTURE_KEY = "__siteJsonCaptureStore";
  const store = (window[CAPTURE_KEY] = window[CAPTURE_KEY] || []);

  // Each rule ties a hash route to a specific API endpoint and output filename prefix.
  // Rules with a classify() function inspect the parsed response to determine the
  // prefix dynamically — returning null discards the capture.
  const RULES = [
    { hash: "/net-worth",            apiMatch: "getHistories",        prefix: "networth_getHistories" },
    { hash: "/all-transactions",     apiMatch: "getUserTransactions",  prefix: "transactions_getUserTransactions" },
    { hash: "/portfolio/allocation", apiMatch: "getHoldings",         prefix: "allocations_getHoldings" },
    {
      hash: "/portfolio/holdings",
      apiMatch: "getHoldings",
      classify(data) {
        // Two distinct getHoldings responses on this page:
        // - consolidated view: has holdingsTotalValue, one row per position
        // - per-account detail: has classificationTypes, one row per account per position
        if (data?.spData?.holdingsTotalValue !== undefined) return "holdings_getHoldings";
        if (data?.spData?.classificationTypes  !== undefined) return "holdings_detail_getHoldings";
        return null; // unrecognised shape — discard
      }
    },
  ];

  // Recursively normalize a parsed JSON value: sort object keys, sort arrays by
  // their serialized form. This ensures two logically identical responses that
  // differ only in key/element ordering produce the same fingerprint.
  function normalizeJSON(val) {
    if (Array.isArray(val)) {
      const items = val.map(normalizeJSON);
      items.sort((a, b) => {
        const sa = JSON.stringify(a), sb = JSON.stringify(b);
        return sa < sb ? -1 : sa > sb ? 1 : 0;
      });
      return items;
    }
    if (val !== null && typeof val === "object") {
      const out = {};
      for (const k of Object.keys(val).sort()) out[k] = normalizeJSON(val[k]);
      return out;
    }
    return val;
  }

  // Fast 32-bit hash of normalized parsed data — order-insensitive fingerprint.
  function contentHash(data) {
    const str = JSON.stringify(normalizeJSON(data));
    let h = 5381;
    for (let i = 0; i < str.length; i++) {
      h = ((h << 5) + h) ^ str.charCodeAt(i);
      h = h >>> 0;
    }
    return h.toString(16);
  }

  function findRule(url) {
    if (typeof url !== "string") return null;
    const hash = window.location.hash;
    return RULES.find(r => hash.includes(r.hash) && url.includes(r.apiMatch)) || null;
  }

  function buildEntry(url, data, prefix, hash) {
    const date = new Date().toISOString().slice(0, 10).replace(/-/g, "");
    const filename = `Empower - ${prefix}_${date}.json`;
    return {
      id: `${prefix}_${Date.now()}`,
      name: prefix,
      filename,
      url,
      capturedAt: new Date().toISOString(),
      contentHash: hash,
      data
    };
  }

  function addCapture(url, text, rule = findRule(url)) {
    if (!rule) return;
    try {
      const data = JSON.parse(text);

      // Resolve prefix — classify() overrides static prefix when defined.
      const prefix = rule.classify ? rule.classify(data) : rule.prefix;
      if (!prefix) return;

      // Deduplicate: drop if we already have this exact content for this prefix.
      // Hash is computed on parsed+normalized data, so array-order differences are ignored.
      const hash = contentHash(data);
      if (store.some(e => e.name === prefix && e.contentHash === hash)) return;

      const entry = buildEntry(url, data, prefix, hash);
      store.push(entry);

      window.postMessage(
        {
          source: "site-json-capture",
          type: "CAPTURE_ADDED",
          payload: {
            id: entry.id,
            filename: entry.filename,
            capturedAt: entry.capturedAt,
            url: entry.url
          }
        },
        "*"
      );
    } catch (e) {
      console.error("[Extension] failed to capture", url, e);
    }
  }

  function downloadEntry(entry) {
    const blob = new Blob([JSON.stringify(entry.data, null, 2)], {
      type: "application/json"
    });
    const objectUrl = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = objectUrl;
    a.download = entry.filename;
    document.documentElement.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
  }

  const origOpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function (method, url, ...rest) {
    this.addEventListener("load", function () {
      addCapture(url, this.responseText);
    });
    return origOpen.apply(this, [method, url, ...rest]);
  };

  const origFetch = window.fetch;
  window.fetch = async function (...args) {
    const response = await origFetch.apply(this, args);
    try {
      const url =
        typeof args[0] === "string"
          ? args[0]
          : args[0] && typeof args[0].url === "string"
          ? args[0].url
          : "";

      const rule = findRule(url);
      if (rule) {
        const clone = response.clone();
        const text = await clone.text();
        addCapture(url, text, rule);
      }
    } catch (e) {
      console.error("[Extension] fetch capture failed", e);
    }
    return response;
  };

  window.addEventListener("message", (event) => {
    if (event.source !== window || !event.data) return;
    if (event.data.source !== "site-json-capture-extension") return;

    if (event.data.type === "GET_CAPTURES") {
      window.postMessage(
        {
          source: "site-json-capture",
          type: "CAPTURES_LIST",
          payload: store.map(({ id, filename, capturedAt, url }) => ({
            id,
            filename,
            capturedAt,
            url
          }))
        },
        "*"
      );
    }

    if (event.data.type === "DOWNLOAD_LATEST") {
      const latest = store[store.length - 1];
      if (latest) downloadEntry(latest);
    }

    if (event.data.type === "DOWNLOAD_ALL") {
      store.forEach(downloadEntry);
    }

    if (event.data.type === "CLEAR_CAPTURES") {
      store.length = 0;
      window.postMessage(
        {
          source: "site-json-capture",
          type: "CAPTURES_CLEARED"
        },
        "*"
      );
    }
  });
})();