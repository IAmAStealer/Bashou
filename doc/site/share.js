// Bashou card: draws a player's banner from the link's fragment (after the #), which never leaves the
// browser. The fragment comes from anyone: it is read as untrusted data, checked against a whitelist,
// and only ever drawn as pixels or written with textContent. No library, no request but share-pets.json.
"use strict";

const MAX_FRAGMENT = 1024;
const MAX_JSON = 4096;
const KEYS = ["p", "f", "lv", "ach", "pets", "won", "read", "sk", "n", "s", "sf"];
const NAME = /^[A-Za-z0-9_-]{1,12}$/;          // the same as bashou/share.py

const TEXT = {
  en: { title: "Bashou card", drawing: "Drawing the card…", share: "Share", save: "Save image",
        bad: "This card can't be read. Ask for a new link: bashou share.",
        unverified: "Anyone can make a card: this one isn't verified.",
        privacy: "This page drew the card on your device from the link itself: the part after the # is never " +
                 "sent to a server. There is no account, no tracking and nothing stored.",
        tagline: "is a terminal pet that teaches Linux, bash and more.",
        level: "Level", achievements: "achievements", pets: "pets found",
        won: "fights won", read: "lessons read", starter: "Starter", everything: "A bit of everything",
        footer: "a terminal pet that teaches Linux", alt: "Bashou banner" },
  fr: { title: "Carte Bashou", drawing: "Dessin de la carte…", share: "Partager", save: "Enregistrer l'image",
        bad: "Cette carte est illisible. Demande un nouveau lien : bashou share.",
        unverified: "N'importe qui peut fabriquer une carte : celle-ci n'est pas vérifiée.",
        privacy: "Cette page a dessiné la carte sur ton appareil à partir du lien lui-même : la partie après le # " +
                 "n'est jamais envoyée à un serveur. Pas de compte, pas de pistage, rien n'est stocké.",
        tagline: "est un compagnon de terminal qui apprend Linux, bash et plus encore.",
        level: "Niveau", achievements: "succès", pets: "pets trouvés",
        won: "combats gagnés", read: "leçons lues", starter: "Compagnon de départ", everything: "Un peu de tout",
        footer: "un compagnon de terminal qui apprend Linux", alt: "Bannière Bashou" },
};

function own(obj, key) {
  return obj !== null && typeof obj === "object" && Object.prototype.hasOwnProperty.call(obj, key);
}

function base64url(text) {
  const b64 = text.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4 - text.length % 4) % 4);
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

// zlib data -> text, stopping as soon as it grows past `limit` bytes (a small link can't become a huge text).
async function inflate(bytes, limit) {
  const reader = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("deflate")).getReader();
  const parts = [];
  let size = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    size += value.length;
    if (size > limit) {
      await reader.cancel();
      return null;
    }
    parts.push(value);
  }
  const all = new Uint8Array(size);
  let at = 0;
  for (const p of parts) { all.set(p, at); at += p.length; }
  return new TextDecoder("utf-8", { fatal: true }).decode(all);
}

function whole(value, low, high) {
  return Number.isInteger(value) && value >= low && value <= high;
}

// The card, or null. `data` is share-pets.json: only what it lists can be drawn.
function check(card, data) {
  if (card === null || typeof card !== "object" || Array.isArray(card)) return null;
  for (const key of Object.keys(card)) if (!KEYS.includes(key)) return null;
  if (typeof card.p !== "string" || !own(data.families, card.p)) return null;
  const family = data.families[card.p];
  if (!whole(card.f, 1, family.forms.length)) return null;
  for (const key of ["lv", "ach", "pets", "won", "read"]) {
    const bounds = data.bounds[key];
    if (!whole(card[key], bounds[0], bounds[1])) return null;
  }
  if (!Array.isArray(card.sk) || card.sk.length > Object.keys(data.skills).length) return null;
  for (const skill of card.sk) if (typeof skill !== "string" || !own(data.skills, skill)) return null;
  if (new Set(card.sk).size !== card.sk.length) return null;
  if (typeof card.n !== "string" || !NAME.test(card.n)) return null;      // every card has a nickname
  if (typeof card.s !== "string" || !data.starters.includes(card.s) || !own(data.families, card.s)) return null;
  if (!whole(card.sf, 1, data.families[card.s].forms.length)) return null;
  return card;
}

async function readCard(fragment, data) {
  try {
    const text = fragment.replace(/^#/, "");
    if (text.length > MAX_FRAGMENT || !/^v1\.[A-Za-z0-9_-]+$/.test(text)) return null;
    const json = await inflate(base64url(text.slice(3)), MAX_JSON);
    return json === null ? null : check(JSON.parse(json), data);
  } catch (e) {
    return null;
  }
}

// --- drawing ---------------------------------------------------------------------------------------

function rgb(hex) {
  return [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16));
}

function lightness(hex) {
  const [r, g, b] = rgb(hex);
  return 0.3 * r + 0.59 * g + 0.11 * b;
}

// The pet's main bright color: the most used one that reads well on the dark banner.
function accent(sprite) {
  const count = {};
  for (const row of sprite.base) for (const k of row) if (k !== ".") count[k] = (count[k] || 0) + 1;
  for (const low of [120, 70]) {
    let best = null, most = 0;
    for (const k of Object.keys(count)) {
      const light = lightness(sprite.palette[k]);
      if (light > low && light < 235 && count[k] > most) { best = sprite.palette[k]; most = count[k]; }
    }
    if (best) return best;
  }
  return "#8fd6ff";
}

function drawSprite(ctx, sprite, x, y, scale, shadow) {
  sprite.base.forEach((row, r) => {
    for (let c = 0; c < row.length; c++) {
      const k = row[c];
      if (k === ".") continue;
      ctx.fillStyle = shadow || sprite.palette[k];
      ctx.fillRect(x + c * scale, y + r * scale, scale, scale);
    }
  });
}

function box(ctx, x, y, w, h, radius, color) {
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.roundRect(x, y, w, h, radius);
  ctx.fill();
}

function banner(card, data, t, lang) {
  const canvas = document.createElement("canvas");
  canvas.width = 1500;
  canvas.height = 500;
  const ctx = canvas.getContext("2d");
  const family = data.families[card.p];
  const sprite = data.sprites[family.forms[card.f - 1]];
  const color = accent(sprite);
  const font = "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif";

  const sky = ctx.createLinearGradient(0, 0, 1500, 500);
  sky.addColorStop(0, "#15161f");
  sky.addColorStop(1, "#23263a");
  ctx.fillStyle = sky;
  ctx.fillRect(0, 0, 1500, 500);
  ctx.globalAlpha = 0.18;
  box(ctx, 50, 60, 460, 380, 36, color);
  ctx.globalAlpha = 1;
  drawSprite(ctx, sprite, 59, 94, 26);                          // 17 x 12 pixels, 26 times bigger

  const x = 570;
  ctx.fillStyle = "#ffffff";
  ctx.font = `700 64px ${font}`;
  ctx.fillText(card.n, x, 125);
  ctx.fillStyle = color;
  ctx.font = `600 34px ${font}`;
  ctx.fillText(`${t.level} ${card.lv} · ${family[lang][card.f - 1]}`, x, 178);

  family.forms.forEach((id, i) => {                             // the family, reached forms in color
    const reached = i < card.f;
    drawSprite(ctx, data.sprites[id], x + i * 80, 205, 4, reached ? null : "rgba(255,255,255,0.12)");
  });

  const stats = [[card.ach, t.achievements], [card.pets, t.pets], [card.won, t.won], [card.read, t.read]];
  stats.forEach(([n, label], i) => {
    const bx = x + i * 222;
    box(ctx, bx, 282, 202, 104, 16, "rgba(255,255,255,0.07)");
    ctx.fillStyle = "#ffffff";
    ctx.font = `700 46px ${font}`;
    ctx.fillText(String(n), bx + 20, 336);
    ctx.fillStyle = "#b9bccc";
    ctx.font = `400 22px ${font}`;
    ctx.fillText(label, bx + 20, 370);
  });

  // the starter's latest form, at the end of the skills row
  const starter = data.families[card.s];
  const starterSprite = data.sprites[starter.forms[card.sf - 1]];
  drawSprite(ctx, starterSprite, 1450 - 68, 397, 4);           // 17 x 12 pixels, 4 times bigger
  ctx.font = `400 20px ${font}`;
  ctx.fillStyle = "#b9bccc";
  const starterText = `${t.starter} · ${starter[lang][card.sf - 1]}`;
  const starterX = 1450 - 68 - 12 - ctx.measureText(starterText).width;
  ctx.fillText(starterText, starterX, 430);

  ctx.font = `600 22px ${font}`;
  let sx = x;
  const skills = card.sk.length ? card.sk.map(s => data.skills[s][lang]) : [t.everything];
  for (const label of skills) {
    const w = ctx.measureText(label).width + 28;
    if (sx + w > starterX - 16) break;
    box(ctx, sx, 404, w, 38, 19, color);
    ctx.fillStyle = lightness(color) > 140 ? "#15161f" : "#ffffff";
    ctx.fillText(label, sx + 14, 431);
    sx += w + 10;
  }

  ctx.fillStyle = "#8b8fa3";
  ctx.font = `400 20px ${font}`;
  ctx.fillText(`bashou · ${t.footer} · github.com/IAmAStealer/Bashou`, 59, 478);
  return canvas;
}

// --- page --------------------------------------------------------------------------------------------

// The browser's language, the first of its list that we speak (fr or en).
function browserLang() {
  for (const tag of navigator.languages || [navigator.language || "en"]) {
    const code = String(tag).toLowerCase().slice(0, 2);
    if (code === "fr" || code === "en") return code;
  }
  return "en";
}

async function main() {
  if (window.top !== window.self) return;                       // never inside someone else's frame
  const $ = id => document.getElementById(id);
  let lang = browserLang(), file = null, url = null;

  function texts() {
    const t = TEXT[lang];
    document.documentElement.lang = lang;
    document.title = t.title;
    for (const id of ["title", "share", "save", "unverified", "privacy", "tagline"]) $(id).textContent = t[id];
    for (const code of ["en", "fr"]) $("lang-" + code).setAttribute("aria-pressed", String(code === lang));
    return t;
  }

  let t = texts();
  $("status").textContent = t.drawing;
  let data = null;
  try {
    const answer = await fetch("share-pets.json", { credentials: "omit", referrerPolicy: "no-referrer" });
    data = await answer.json();
  } catch (e) {
    data = null;
  }
  const card = data && await readCard(location.hash, data);
  if (!card) {
    $("status").textContent = t.bad;
    return;
  }

  function draw() {
    t = texts();
    banner(card, data, t, lang).toBlob(blob => {
      if (url) URL.revokeObjectURL(url);
      url = URL.createObjectURL(blob);
      file = new File([blob], "bashou.png", { type: "image/png" });
      const img = $("card");
      img.src = url;
      img.alt = t.alt;
      img.hidden = false;
      $("save").href = url;
      for (const id of ["actions", "langs", "unverified"]) $(id).hidden = false;
      $("status").hidden = true;
      $("share").hidden = !(navigator.canShare && navigator.canShare({ files: [file] }));
    }, "image/png");
  }

  $("share").addEventListener("click", () => navigator.share({ files: [file] }).catch(() => {}));
  for (const code of ["en", "fr"]) {
    $("lang-" + code).addEventListener("click", () => { lang = code; draw(); });
  }
  draw();
}

if (typeof document !== "undefined") {
  main();
} else if (typeof module === "object") {
  module.exports = { readCard, check, inflate, base64url, drawSprite };       // for tests (node)
}
