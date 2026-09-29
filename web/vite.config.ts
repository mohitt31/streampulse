import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { viteSingleFile } from "vite-plugin-singlefile";

// `npm run build`         -> GitHub Pages build (data fetched from ./data/replay.json)
// `npm run build:single`  -> one self-contained HTML (data inlined) for offline review
export default defineConfig(({ mode }) => ({
  base: "./",
  plugins: mode === "single" ? [react(), viteSingleFile()] : [react()],
  define: { __INLINE_DATA__: JSON.stringify(mode === "single") },
  // single mode inlines public/data/replay.json via import, so public/ must not be special there
  publicDir: mode === "single" ? false : "public",
  build: { outDir: mode === "single" ? "dist-single" : "dist" },
}));
