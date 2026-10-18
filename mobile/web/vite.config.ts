import { defineConfig } from "vite";
import { fileURLToPath } from "node:url";
export default defineConfig({
  tsconfig: fileURLToPath(new URL("./tsconfig.json", import.meta.url)),
  server: { host: "127.0.0.1", port: 5173 },
  build: { outDir: "dist" },
});
