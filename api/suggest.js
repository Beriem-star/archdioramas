// Receives a suggestion ("what should the next video / guide be about?")
// and saves it privately in Vercel Blob. Works with or without JavaScript.
import { put } from "@vercel/blob";
import crypto from "node:crypto";

const KINDS = ["video", "blog", "both"];

function clean(v, max) {
  return String(v ?? "").replace(/[\u0000-\u0008\u000B-\u001F\u007F]/g, "").trim().slice(0, max);
}

async function readBody(req) {
  if (req.body && typeof req.body === "object") return req.body;
  const chunks = [];
  for await (const c of req) chunks.push(c);
  const raw = Buffer.concat(chunks).toString("utf8");
  if ((req.headers["content-type"] || "").includes("application/json")) {
    try { return JSON.parse(raw); } catch { return {}; }
  }
  return Object.fromEntries(new URLSearchParams(raw));
}

function backTo(req, hash) {
  const ref = req.headers.referer || "/blog/";
  try {
    const u = new URL(ref);
    if (u.host !== req.headers.host) return "/blog/" + hash;
    return u.pathname + hash;
  } catch { return "/blog/" + hash; }
}

export default async function handler(req, res) {
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return res.status(405).json({ ok: false });
  }
  const wantsJson = (req.headers.accept || "").includes("application/json");
  const reply = (status, ok) => wantsJson
    ? res.status(status).json({ ok })
    : res.redirect(303, backTo(req, ok ? "#ideas-ok" : "#ideas-error"));

  const body = await readBody(req);
  // Hidden field that only bots fill in: pretend success, save nothing.
  if (clean(body.website, 200)) return reply(200, true);

  const idea = clean(body.idea, 600);
  if (idea.length < 3) return reply(400, false);
  if (!process.env.BLOB_READ_WRITE_TOKEN) return reply(503, false);

  const item = {
    idea,
    kind: KINDS.includes(body.kind) ? body.kind : "both",
    name: clean(body.name, 60),
    lang: body.lang === "es" ? "es" : "en",
    page: clean(body.page, 200),
    date: new Date().toISOString(),
  };
  const id = `${Date.now()}-${crypto.randomBytes(4).toString("hex")}`;
  try {
    await put(`suggestions/${id}.json`, JSON.stringify(item), {
      access: "private",
      contentType: "application/json",
      addRandomSuffix: false,
    });
    return reply(200, true);
  } catch (err) {
    console.error("suggest: save failed", err);
    return reply(500, false);
  }
}
