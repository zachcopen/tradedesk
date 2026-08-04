// TradeDesk CORS proxy — Cloudflare Worker
// Relays requests to whitelisted fantasy platform APIs and adds CORS headers.
// Deploy: dash.cloudflare.com -> Workers & Pages -> Create Worker -> paste -> Deploy.

const ALLOWED_HOSTS = [
  /^www\d+\.myfantasyleague\.com$/,
  /^api\.myfantasyleague\.com$/,
  /^www\.fleaflicker\.com$/,
];

export default {
  async fetch(request) {
    const cors = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, OPTIONS",
      "Access-Control-Allow-Headers": "*",
    };
    if (request.method === "OPTIONS") return new Response(null, { headers: cors });

    const target = new URL(request.url).searchParams.get("url");
    if (!target) return new Response("Missing ?url=", { status: 400, headers: cors });

    let t;
    try { t = new URL(target); } catch { return new Response("Bad URL", { status: 400, headers: cors }); }
    if (t.protocol !== "https:" || !ALLOWED_HOSTS.some(re => re.test(t.hostname)))
      return new Response("Host not allowed", { status: 403, headers: cors });

    const upstream = await fetch(t.toString(), {
      headers: { "User-Agent": "TradeDesk/1.0 (fantasy league tool)" },
      cf: { cacheTtl: 300, cacheEverything: true },   // 5-min edge cache, be kind to MFL
    });
    const body = await upstream.arrayBuffer();
    return new Response(body, {
      status: upstream.status,
      headers: { ...cors, "Content-Type": upstream.headers.get("Content-Type") || "application/json" },
    });
  },
};
