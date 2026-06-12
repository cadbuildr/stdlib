/**
 * Thumbnail capture tool (dev-only). Renders each catalogue part in a single
 * real R3F scene (same lighting as CadbuildrViewer), reads the canvas as a PNG,
 * and POSTs it to the vite `/__save-thumb` endpoint which writes
 * public/thumbnails/<id>.png. Drive it from the console (or the agent):
 *
 *   window.__captureAll()   // then poll window.__captureProgress
 *
 * Run against the local no-auth kernel-api with a dummy session token (see the
 * capture .env). One Pyodide boot, one WebGL context, real R3F output.
 */
import React from "react";
import ReactDOM from "react-dom/client";
import { Canvas } from "@react-three/fiber";
import { Bounds } from "@react-three/drei";

import { MeshGroup, useCadbuildrRender, CadbuildrProvider } from "@cadbuildr/sdk-react";
import { type KernelDag } from "@cadbuildr/cad-kernel-r3f";
import { type PyodideLike } from "@cadbuildr/cad-pyodide-runtime";

import { resolveKernelApiBaseUrl } from "./kernelApiEnv";
import { bootstrapRuntime, fetchManifest, renderPart, defaultConfig, type CatalogEntry } from "./catalog";

const CAD_Z_UP_TO_Y_UP: [number, number, number] = [-Math.PI / 2, 0, 0];

declare global {
  interface Window {
    __captureAll?: () => Promise<string>;
    __captureProgress?: { done: number; total: number; current: string; failed: string[] };
    __sceneStatus?: string;
    __setDag?: (d: KernelDag | null) => void;
  }
}

function Scene({ dag }: { dag: KernelDag | null }): React.ReactElement {
  const { meshPayload, status } = useCadbuildrRender({ dag });
  React.useEffect(() => {
    window.__sceneStatus = meshPayload ? status : "loading";
  }, [status, meshPayload]);
  return (
    <>
      {/* Same lighting as CadbuildrViewer (no env map → no CORS taint). */}
      <ambientLight intensity={0.85} />
      <hemisphereLight intensity={0.32} color="#f4e8dc" groundColor="#1a1410" />
      <directionalLight intensity={1.05} position={[20, 40, 25]} color="#fff5eb" />
      <directionalLight intensity={0.35} position={[-25, 10, -20]} color="#cfe0ff" />
      {meshPayload ? (
        <Bounds fit observe margin={1.22}>
          <MeshGroup meshPayload={meshPayload} rotation={CAD_Z_UP_TO_Y_UP} />
        </Bounds>
      ) : null}
    </>
  );
}

function CaptureApp(): React.ReactElement {
  const [entries, setEntries] = React.useState<CatalogEntry[]>([]);
  const [dag, setDag] = React.useState<KernelDag | null>(null);
  const pyodideRef = React.useRef<PyodideLike | null>(null);

  React.useEffect(() => {
    window.__setDag = setDag;
  }, []);

  React.useEffect(() => {
    (async () => {
      const py = await bootstrapRuntime();
      pyodideRef.current = py;
      setEntries(await fetchManifest(py));
    })();
  }, []);

  React.useEffect(() => {
    if (!pyodideRef.current || entries.length === 0) return;
    const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
    const frames = (n: number) =>
      new Promise<void>((res) => {
        let i = 0;
        const t = () => (++i >= n ? res() : requestAnimationFrame(t));
        requestAnimationFrame(t);
      });
    const waitReady = async (timeoutMs: number) => {
      const start = Date.now();
      while (Date.now() - start < timeoutMs) {
        if (window.__sceneStatus === "ready") return true;
        if (window.__sceneStatus === "error") return false;
        await sleep(120);
      }
      return false;
    };

    window.__captureAll = async () => {
      const progress = { done: 0, total: entries.length, current: "", failed: [] as string[] };
      window.__captureProgress = progress;
      for (const entry of entries) {
        progress.current = entry.id;
        try {
          window.__sceneStatus = "loading";
          const d = await renderPart(pyodideRef.current as PyodideLike, entry, defaultConfig(entry));
          window.__setDag?.(d);
          const ok = await waitReady(20000);
          if (!ok) {
            progress.failed.push(entry.id);
          } else {
            await frames(5); // paint + Bounds settle
            const canvas = document.querySelector("canvas") as HTMLCanvasElement;
            const dataUrl = canvas.toDataURL("image/png");
            await fetch("/__save-thumb", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ id: entry.id, dataUrl }),
            });
            progress.done += 1;
          }
        } catch (e) {
          progress.failed.push(`${entry.id}: ${String(e).slice(0, 60)}`);
        }
        window.__setDag?.(null);
        window.__sceneStatus = "loading";
        await frames(2);
      }
      return `done: ${progress.done}/${progress.total}, failed: ${progress.failed.length}`;
    };
  }, [entries]);

  return (
    <div style={{ width: "440px", height: "440px" }}>
      <Canvas
        gl={{ preserveDrawingBuffer: true, alpha: true, antialias: true }}
        camera={{ position: [120, 95, 140], fov: 32 }}
        style={{ background: "transparent" }}
      >
        <Scene dag={dag} />
      </Canvas>
      <div style={{ color: "#8c857b", fontFamily: "monospace", fontSize: 12, padding: 8 }}>
        {entries.length ? `ready: ${entries.length} parts — run window.__captureAll()` : "booting…"}
      </div>
    </div>
  );
}

const kernelApiBaseUrl = resolveKernelApiBaseUrl();
const sessionToken = (import.meta.env.VITE_CADBUILDR_SESSION_TOKEN as string | undefined)?.trim() || "local";
const hubBaseUrl = (import.meta.env.VITE_CADBUILDR_HUB_BASE_URL as string | undefined)?.trim() || undefined;

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <CadbuildrProvider baseUrl={kernelApiBaseUrl} hubBaseUrl={hubBaseUrl} sessionToken={sessionToken}>
    <CaptureApp />
  </CadbuildrProvider>,
);
