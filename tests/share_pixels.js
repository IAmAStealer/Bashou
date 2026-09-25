// Run by tests/test_site.py when node is installed: draws every sprite of share-pets.json with the
// page's own drawSprite on a fake canvas, and prints the pixels it painted, for Python to compare.
// Usage: node tests/share_pixels.js share.js share-pets.json
"use strict";
const fs = require("fs");
const [, , script, pets] = process.argv;
const { drawSprite } = require(require("path").resolve(script));
const data = JSON.parse(fs.readFileSync(pets, "utf8"));
const out = {};
for (const [id, sprite] of Object.entries(data.sprites)) {
  const cells = {};
  const ctx = { fillStyle: "", fillRect(x, y, w, h) { cells[`${y / 4},${x / 4}`] = this.fillStyle; } };
  drawSprite(ctx, sprite, 0, 0, 4);
  out[id] = cells;
}
console.log(JSON.stringify(out));
