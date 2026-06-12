import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig, type Plugin } from "vite";

import { LOCAL_STDLIB_URL_SEGMENT, LOCAL_STDLIB_WHEEL_FILE } from "./src/stdlibLocal";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/** Dev-only: stream the wheel from `../dist/` (run `uv build` in the stdlib package dir). */
function serveLocalStdlibWheelFromDist(): Plugin {
  return {
    name: "serve-local-stdlib-wheel-from-dist",
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const pathname = req.url?.split("?")[0] ?? "";
        const tail = `/${LOCAL_STDLIB_URL_SEGMENT}/${LOCAL_STDLIB_WHEEL_FILE}`;
        if (!pathname.endsWith(tail)) {
          next();
          return;
        }
        const wheelPath = path.resolve(__dirname, "..", "dist", LOCAL_STDLIB_WHEEL_FILE);
        if (!fs.existsSync(wheelPath)) {
          res.statusCode = 404;
          res.setHeader("Content-Type", "text/plain; charset=utf-8");
          res.end(
            `Missing stdlib wheel at ${wheelPath}.\nRun: uv build in the Python package directory (parent of github-io/)`
          );
          return;
        }
        res.setHeader("Content-Type", "application/octet-stream");
        fs.createReadStream(wheelPath).pipe(res);
      });
    },
  };
}

/** Dev-only: POST {id, dataUrl} to write a thumbnail PNG into public/thumbnails/. */
function saveThumbnailEndpoint(): Plugin {
  return {
    name: "save-thumbnail-endpoint",
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        if (req.method !== "POST" || !(req.url ?? "").startsWith("/__save-thumb")) {
          next();
          return;
        }
        let body = "";
        req.on("data", (c) => (body += c));
        req.on("end", () => {
          try {
            const { id, dataUrl } = JSON.parse(body) as { id: string; dataUrl: string };
            const b64 = dataUrl.replace(/^data:image\/png;base64,/, "");
            const dir = path.resolve(__dirname, "public", "thumbnails");
            fs.mkdirSync(dir, { recursive: true });
            const safe = id.replace(/[^a-z0-9_-]/gi, "_");
            fs.writeFileSync(path.join(dir, `${safe}.png`), Buffer.from(b64, "base64"));
            res.statusCode = 200;
            res.end("ok");
          } catch (e) {
            res.statusCode = 500;
            res.end(String(e));
          }
        });
      });
    },
  };
}

export default defineConfig({
  base: (process.env.VITE_APP_BASE_PATH as string | undefined) ?? "/",
  plugins: [react(), serveLocalStdlibWheelFromDist(), saveThumbnailEndpoint()],
  server: {
    host: "0.0.0.0",
    port: 3009,
  },
  build: {
    outDir: "dist",
  },
});
