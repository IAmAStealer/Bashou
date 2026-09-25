// Run by tests/test_site.py when node is installed: share.js against good and hostile links.
// Usage: node tests/share_page.js share.js share-pets.json good-link
"use strict";
const fs = require("fs");
const zlib = require("zlib");
const [, , script, pets, good] = process.argv;
const { readCard } = require(require("path").resolve(script));
const data = JSON.parse(fs.readFileSync(pets, "utf8"));

const pack = obj => "#v1." + zlib.deflateSync(Buffer.from(typeof obj === "string" ? obj : JSON.stringify(obj)))
  .toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
const base = { p: "packet", f: 3, lv: 5, ach: 20, pets: 4, won: 2, read: 3, sk: ["network"] };

const hostile = {
  "too long": "#v1." + "A".repeat(2000),
  "not base64": "#v1.<script>alert(1)</script>",
  "old version": "#v0.abc",
  "empty": "",
  "zlib bomb": pack("[" + "0,".repeat(200000) + "0]"),
  "not json": pack("{nope"),
  "an array": pack([1, 2]),
  "unknown key": pack({ ...base, x: 1 }),
  "__proto__": pack('{"p":"packet","f":3,"lv":5,"ach":20,"pets":4,"won":2,"read":3,"sk":[],"__proto__":{"a":1}}'),
  "unknown pet": pack({ ...base, p: "constructor" }),
  "form too far": pack({ ...base, f: 11 }),
  "level 999": pack({ ...base, lv: 999 }),
  "negative": pack({ ...base, won: -1 }),
  "float": pack({ ...base, ach: 1.5 }),
  "string number": pack({ ...base, lv: "5" }),
  "html name": pack({ ...base, n: "<img src=x>" }),
  "javascript: name": pack({ ...base, n: "javascript:x" }),
  "long name": pack({ ...base, n: "abcdefghijklm" }),
  "unknown skill": pack({ ...base, sk: ["hacking"] }),
  "twice a skill": pack({ ...base, sk: ["bash", "bash"] }),
  "missing key": pack({ p: "packet", f: 1 }),
};

(async () => {
  let failed = 0;
  const ok = await readCard("#" + good.split("#")[1], data);
  if (!ok) { console.log("FAIL: the good link was refused"); failed++; }
  const named = await readCard(pack({ ...base, n: "Alexis_42" }), data);
  if (!named || named.n !== "Alexis_42") { console.log("FAIL: a good name was refused"); failed++; }
  for (const [name, fragment] of Object.entries(hostile)) {
    if (await readCard(fragment, data) !== null) { console.log("FAIL: accepted " + name); failed++; }
  }
  console.log(failed ? `${failed} failed` : "ok");
  process.exit(failed ? 1 : 0);
})();
