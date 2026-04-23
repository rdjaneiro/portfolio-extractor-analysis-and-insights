# Site JSON Capture Exporter

Manifest V3 Chrome extension that intercepts selected JSON API responses on a specific site and saves them as `.json` files to the user's local device.

## What this package includes

- `page_hook.js`: runs in the page's JS context; patches `XMLHttpRequest` and `fetch` to capture responses whose URLs match configured patterns, stores captures in memory, and triggers downloads via anchor-click
- `content.js`: injected as a content script at `document_start`; injects `page_hook.js` into the page context, maintains a local mirror of the capture list, and relays messages between the page and the popup
- `popup.html` / `popup.js`: shows the list of captures available on the active tab with buttons to refresh, download the latest capture, download all captures, or clear the list
- `manifest.json`: MV3 manifest targeting `https://participant.empower-retirement.com/*`; no special permissions required

## Capture rules

Rules are hardcoded in `page_hook.js`. A capture only fires when the page's hash route and the API URL both match:

| Hash route | API endpoint | Output filename |
|---|---|---|
| `#/net-worth` | `getHistories` | `Empower - networth_getHistories_YYYYMMDD.json` |
| `#/all-transactions` | `getUserTransactions` | `Empower - transactions_getUserTransactions_YYYYMMDD.json` |
| `#/portfolio/allocation` | `getHoldings` | `Empower - allocations_getHoldings_YYYYMMDD.json` |
| `#/portfolio/holdings` | `getHoldings` (consolidated — one row per position) | `Empower - holdings_getHoldings_YYYYMMDD.json` |
| `#/portfolio/holdings` | `getHoldings` (per-account — one row per account per position) | `Empower - holdings_detail_getHoldings_YYYYMMDD.json` |

To add or change rules, edit the `RULES` array at the top of `page_hook.js`.

## Before publishing

1. Replace the host in `manifest.json` (`host_permissions` and `content_scripts.matches`) with the exact site you own or are authorized to target.
2. Rename the extension so it does not imply affiliation with a third-party brand unless you have permission.
3. Test with `chrome://extensions` → Developer mode → Load unpacked.
4. Create a ZIP from the extension folder contents for the Chrome Web Store upload.
5. Prepare a privacy policy and store disclosure — this extension captures financial data (account history, transaction records, and portfolio allocation).

## Suggested Chrome Web Store description

Export selected JSON API responses from a specific website into local `.json` files. The extension runs only on the declared site, captures only configured endpoints, and saves files locally in the user's browser session.

## Minimal privacy-policy starter

This extension captures JSON responses from specific API endpoints on the site listed in the Chrome Web Store description and saves them locally to the user's device. The extension does not transmit captured data to the developer or any third party. The extension requires no special browser permissions beyond access to the declared site.

## Important review notes

- Keep permissions narrow; remove any permissions that are not actively used.
- Do not add remote code.
- Do not claim affiliation with a site unless authorized.
- Make the store listing and in-product UI clearly explain what is captured.
