// Private list of suggestions for the owner's page at /sugerencias/.
// Needs the ADMIN_KEY password in the "x-admin-key" header.
import { list, get, del } from "@vercel/blob";
import crypto from "node:crypto";

function allowed(req) {
  const key = process.env.ADMIN_KEY || "";
  const given = String(req.headers["x-admin-key"] || "");
  if (key.length < 8 || given.length !== key.length) return false;
  return crypto.timingSafeEqual(Buffer.from(given), Buffer.from(key));
}

async function readJson(pathname) {
  const r = await get(pathname, { access: "private", useCache: false });
  if (!r || r.statusCode !== 200) return null;
  const text = await new Response(r.stream).text();
  try { return JSON.parse(text); } catch { return null; }
}

export default async function handler(req, res) {
  res.setHeader("Cache-Control", "no-store");
  res.setHeader("X-Robots-Tag", "noindex");
  if (!allowed(req)) return res.status(401).json({ ok: false, error: "wrong-password" });
  if (!process.env.BLOB_READ_WRITE_TOKEN) return res.status(503).json({ ok: false, error: "no-storage" });

  if (req.method === "DELETE") {
    const id = String(req.query.id || "");
    if (!/^[0-9]+-[0-9a-f]{8}$/.test(id)) return res.status(400).json({ ok: false });
    await del(`suggestions/${id}.json`);
    return res.status(200).json({ ok: true });
  }
  if (req.method !== "GET") return res.status(405).json({ ok: false });

  const blobs = [];
  let cursor;
  do {
    const page = await list({ prefix: "suggestions/", cursor, limit: 1000 });
    blobs.push(...page.blobs);
    cursor = page.hasMore ? page.cursor : undefined;
  } while (cursor && blobs.length < 3000);

  const items = (await Promise.all(blobs.map(async (b) => {
    const data = await readJson(b.pathname);
    return data && { id: b.pathname.replace(/^suggestions\//, "").replace(/\.json$/, ""), ...data };
  }))).filter(Boolean).sort((a, b) => (a.date < b.date ? 1 : -1));

  return res.status(200).json({ ok: true, items });
}
