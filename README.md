# TradeDesk

Self-updating dynasty/keeper trade calculator. Import any Sleeper, MFL, or
Fleaflicker league; values refresh daily with no servers and no maintenance.

## Architecture (all free)
- **GitHub Pages** serves `index.html` — the entire app.
- **GitHub Actions** runs `scripts/build_values.py` every morning (7 AM ET),
  blending multiple public market and expert-consensus sources into `data/values.json`.
- **Cloudflare Worker** (`cors-proxy-worker.js`) relays MFL/Fleaflicker API calls,
  since those platforms block direct browser requests. Sleeper needs no proxy.

## Setup
1. Create a GitHub repo, upload all these files (drag-and-drop on github.com works).
2. Settings -> Pages -> Deploy from branch -> `main`, folder `/ (root)`.
3. Actions tab -> enable workflows -> run **Update player values** once manually.
4. (For MFL/Fleaflicker imports) In dash.cloudflare.com: Workers & Pages ->
   Create Worker -> paste `cors-proxy-worker.js` -> Deploy. Copy the worker URL
   into the `PROXY` constant near the top of the script in `index.html`.
5. Site is live at `https://<username>.github.io/<repo>/`.

## Tuning
Blend weights, age curves, pick tier probabilities: top of `scripts/build_values.py`.

## Formula
SlateValue = a weighted blend of market-based and expert-consensus valuations
(reweighted automatically if a source is unreachable) x position age curve.
Superflex leagues use 2QB values end to end. Future picks are priced from the
origin team's projected finish. Trade fairness applies a consolidation discount.
