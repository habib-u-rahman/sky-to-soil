// MapLibre GL JS derives its worker script's URL from import.meta.url at
// runtime, and falls back to an EMPTY string if that doesn't look like a
// real http(s) URL (which it doesn't under Next.js/Turbopack's module
// wrapping) -- see map-picker.tsx's setWorkerUrl() call for the other half
// of this fix. This script copies the matching worker bundle out of
// node_modules into public/ so it's just a normal static asset Next.js
// serves at a stable URL, kept in sync automatically on every `npm install`
// via the postinstall hook in package.json.
const fs = require("fs");
const path = require("path");

const src = path.join(__dirname, "..", "node_modules", "maplibre-gl", "dist", "maplibre-gl-worker.mjs");
const dest = path.join(__dirname, "..", "public", "maplibre-gl-worker.mjs");

fs.copyFileSync(src, dest);
console.log(`Copied ${src} -> ${dest}`);
