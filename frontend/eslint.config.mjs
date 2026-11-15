import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    // Static assets (including the maplibre-gl worker bundle copied in by
    // scripts/copy-maplibre-worker.js -- third-party minified code, not
    // something we should lint) and plain Node build scripts.
    "public/**",
    "scripts/**",
  ]),
]);

export default eslintConfig;
