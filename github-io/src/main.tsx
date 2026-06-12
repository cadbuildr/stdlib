import React from "react";
import ReactDOM from "react-dom/client";
import { AnimatePresence, motion } from "framer-motion";
import { Boxes, Github, ExternalLink, X } from "lucide-react";

import { type KernelDag } from "@cadbuildr/cad-kernel-r3f";
import { type PyodideLike } from "@cadbuildr/cad-pyodide-runtime";
import { CadbuildrProvider, CadbuildrViewer } from "@cadbuildr/sdk-react";

import { resolveKernelApiBaseUrl } from "./kernelApiEnv";
import {
  bootstrapRuntime,
  fetchManifest,
  renderPart,
  defaultConfig,
  type CatalogEntry,
  type ParamSpec,
  type PartConfig,
} from "./catalog";
import "./styles.css";

const SCENE_BG = "#0e1216";
const REPO_HTTPS = "https://github.com/cadbuildr/stdlib";
const CATEGORY_ORDER = [
  "Fasteners",
  "Linear Motion",
  "Bearings",
  "Power Transmission",
  "Actuators",
  "Profiles",
];

// ---- render gate ----
// Must be 1: foundation's show() capture is a single global hook in the shared
// Pyodide instance, so overlapping renders would cross each other's DAGs (a part
// showing another part's mesh). Serialize end-to-end; lazy-loading keeps it snappy.
const MAX_CONCURRENT = 1;
let activeRenders = 0;
const renderQueue: Array<() => void> = [];
function scheduleRender<T>(task: () => Promise<T>): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const run = () => {
      activeRenders += 1;
      task()
        .then(resolve, reject)
        .finally(() => {
          activeRenders -= 1;
          const next = renderQueue.shift();
          if (next) next();
        });
    };
    if (activeRenders < MAX_CONCURRENT) run();
    else renderQueue.push(run);
  });
}

/** URL of the pre-rendered thumbnail committed under public/thumbnails/. */
function thumbUrl(id: string): string {
  const base = import.meta.env.BASE_URL ?? "/";
  const normalized = base.endsWith("/") ? base : `${base}/`;
  return `${normalized}thumbnails/${id}.png`;
}

// ---- the 3D thumbnail / viewer for a single configured part ----
function PartViewer({
  pyodide,
  entry,
  config,
  camera,
}: {
  pyodide: PyodideLike;
  entry: CatalogEntry;
  config: PartConfig;
  camera: [number, number, number];
}): React.ReactElement {
  const [dag, setDag] = React.useState<KernelDag | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const key = JSON.stringify(config);

  React.useEffect(() => {
    let cancelled = false;
    setError(null);
    setDag(null);
    scheduleRender(() => renderPart(pyodide, entry, config))
      .then((d) => {
        if (!cancelled) setDag(d);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  if (error) return <div className="viewer-status error mini">{error}</div>;
  if (!dag)
    return (
      <div className="viewer-status mini">
        <span className="spinner" />
      </div>
    );
  return (
    <CadbuildrViewer
      dag={dag}
      background={SCENE_BG}
      cameraPosition={camera}
      meshPosition={[0, 0, 0]}
      showHelpers={false}
      onError={(e) => setError(e.message)}
    />
  );
}

// ---- card in the grid ----
function PartCard({
  entry,
  onOpen,
}: {
  entry: CatalogEntry;
  onOpen: (e: CatalogEntry) => void;
}): React.ReactElement {
  return (
    <motion.button
      className={`card${entry.featured ? " featured" : ""}`}
      onClick={() => onOpen(entry)}
      initial={{ opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-40px" }}
      whileHover={{ y: -4 }}
      transition={{ duration: 0.3 }}
    >
      <div className="card-canvas">
        <img className="thumb" src={thumbUrl(entry.id)} alt={entry.name} loading="lazy" />
      </div>
      <div className="card-body">
        <h3>{entry.name}</h3>
        <span className="standard">{entry.standard}</span>
        <p>{entry.description}</p>
      </div>
    </motion.button>
  );
}

// ---- configurator drawer ----
function controlValue(spec: ParamSpec, raw: string): string | number | boolean {
  if (spec.kind === "number") return Number(raw);
  if (spec.kind === "bool") return raw === "true";
  return raw;
}

function Configurator({
  pyodide,
  entry,
  onClose,
}: {
  pyodide: PyodideLike | null;
  entry: CatalogEntry;
  onClose: () => void;
}): React.ReactElement {
  const [config, setConfig] = React.useState<PartConfig>(() => defaultConfig(entry));
  const set = (name: string, value: string | number | boolean) =>
    setConfig((c) => ({ ...c, [name]: value }));

  return (
    <motion.aside
      className="drawer"
      initial={{ x: "100%" }}
      animate={{ x: 0 }}
      exit={{ x: "100%" }}
      transition={{ type: "spring", stiffness: 320, damping: 36 }}
    >
      <div className="drawer-head">
        <div>
          <h2>{entry.name}</h2>
          <span className="standard">{entry.standard}</span>
        </div>
        <button className="icon-btn" onClick={onClose} aria-label="Close">
          <X size={18} />
        </button>
      </div>

      <div className="drawer-canvas">
        {pyodide ? (
          <PartViewer pyodide={pyodide} entry={entry} config={config} camera={[160, 120, 200]} />
        ) : (
          <div className="viewer-status">
            <span className="spinner" /> Booting in-browser CAD…
          </div>
        )}
      </div>

      <div className="drawer-body">
        <p className="muted">{entry.description}</p>
        <div className="controls">
          {entry.params.map((spec) => (
            <label key={spec.name} className="control">
              <span className="control-label">
                {spec.label ?? spec.name}
                {spec.unit ? <em> ({spec.unit})</em> : null}
              </span>
              {spec.kind === "enum" ? (
                <select
                  value={String(config[spec.name])}
                  onChange={(e) => set(spec.name, controlValue(spec, e.target.value))}
                >
                  {(spec.choices ?? []).map((c) => (
                    <option key={String(c)} value={String(c)}>
                      {String(c)}
                    </option>
                  ))}
                </select>
              ) : spec.kind === "bool" ? (
                <select
                  value={String(config[spec.name])}
                  onChange={(e) => set(spec.name, controlValue(spec, e.target.value))}
                >
                  <option value="true">on</option>
                  <option value="false">off</option>
                </select>
              ) : (
                <span className="range">
                  <input
                    type="range"
                    min={spec.min}
                    max={spec.max}
                    step={spec.step ?? 1}
                    value={Number(config[spec.name])}
                    onChange={(e) => set(spec.name, controlValue(spec, e.target.value))}
                  />
                  <output>{String(config[spec.name])}</output>
                </span>
              )}
            </label>
          ))}
        </div>

        <div className="snippet">
          <span className="snippet-label">Python</span>
          <code>
            from {entry.module} import {entry.cls}
            <br />
            show({entry.cls}({Object.entries(config)
              .map(([k, v]) => `${k}=${typeof v === "string" ? `"${v}"` : v}`)
              .join(", ")}))
          </code>
        </div>
      </div>
    </motion.aside>
  );
}

function App(): React.ReactElement {
  const [pyodide, setPyodide] = React.useState<PyodideLike | null>(null);
  const [entries, setEntries] = React.useState<CatalogEntry[] | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [open, setOpen] = React.useState<CatalogEntry | null>(null);

  const kernelApiBaseUrl = React.useMemo(() => resolveKernelApiBaseUrl(), []);
  const sdkKeyId = React.useMemo(
    () => (import.meta.env.VITE_CADBUILDR_SDK_KEY_ID as string | undefined)?.trim() || undefined,
    [],
  );
  const hubBaseUrl = React.useMemo(
    () => (import.meta.env.VITE_CADBUILDR_HUB_BASE_URL as string | undefined)?.trim() || undefined,
    [],
  );
  const projectKey = React.useMemo(
    () => (import.meta.env.VITE_CADBUILDR_PROJECT_KEY as string | undefined)?.trim() || "stdlib",
    [],
  );
  // Optional pre-minted server-flow token (skips the hub mint). Useful for
  // self-hosted kernel-api or local verification.
  const sessionToken = React.useMemo(
    () => (import.meta.env.VITE_CADBUILDR_SESSION_TOKEN as string | undefined)?.trim() || undefined,
    [],
  );

  React.useEffect(() => {
    let cancelled = false;
    // Fast path: static manifest → the grid (static thumbnails) paints instantly,
    // no need to wait for Pyodide.
    const base = import.meta.env.BASE_URL ?? "/";
    fetch(`${base.endsWith("/") ? base : base + "/"}catalog.json`)
      .then((r) => (r.ok ? r.json() : null))
      .then((j) => {
        if (!cancelled && j) setEntries((cur) => cur ?? j);
      })
      .catch(() => {});
    // Pyodide boots in the background — only needed to render parts in the drawer.
    (async () => {
      try {
        const py = await bootstrapRuntime();
        if (cancelled) return;
        setPyodide(py);
        const manifest = await fetchManifest(py);
        if (cancelled) return;
        setEntries(manifest);
      } catch (e) {
        if (!cancelled && !entries) setError(e instanceof Error ? e.message : String(e));
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const byCategory = React.useMemo(() => {
    const map = new Map<string, CatalogEntry[]>();
    for (const e of entries ?? []) {
      if (!map.has(e.category)) map.set(e.category, []);
      map.get(e.category)!.push(e);
    }
    const ordered = [...map.keys()].sort(
      (a, b) => (CATEGORY_ORDER.indexOf(a) + 1 || 99) - (CATEGORY_ORDER.indexOf(b) + 1 || 99),
    );
    return ordered.map((cat) => [cat, map.get(cat)!] as const);
  }, [entries]);

  const partCount = entries?.length ?? 0;

  const content = (
    <div className="page">
      <header className="topbar">
        <span className="brand">
          <Boxes size={18} className="brand-icon" /> CADbuildr <span className="sep">/</span> stdlib
        </span>
        <span className="links">
          <a href="https://cadbuildr.com" target="_blank" rel="noreferrer">
            cadbuildr.com <ExternalLink size={12} style={{ verticalAlign: "-1px" }} />
          </a>
          <a href={REPO_HTTPS} target="_blank" rel="noreferrer">
            <Github size={14} style={{ verticalAlign: "-2px", marginRight: 4 }} />
            Source
          </a>
        </span>
      </header>

      <section className="hero">
        <h1>
          The standard library, <span className="emph">part by part.</span>
        </h1>
        <p className="lead">
          Every part below is parametric Python built on <code>cadbuildr-foundation</code>,
          rendered live in your browser. Browse by category, open a part, and dial in its
          size — the exact <code>import</code> + call is shown for you to paste.
        </p>
        <div className="badges">
          <span className="badge">{partCount} parts</span>
          <span className="badge gray">DIN / ISO grounded</span>
          <span className="badge gray">Pyodide → kernel-api → R3F</span>
        </div>
      </section>

      {error ? (
        <div className="viewer-status error big">{error}</div>
      ) : !entries ? (
        <div className="viewer-status big">
          <span className="spinner" />
          Booting in-browser Python &amp; loading the catalogue…
        </div>
      ) : (
        byCategory.map(([cat, items]) => (
          <section className="cat" key={cat}>
            <div className="cat-head">
              <h2>{cat}</h2>
              <span className="cat-count">{items.length}</span>
            </div>
            <div className="grid">
              {items.map((e) => (
                <PartCard key={e.id} entry={e} onOpen={setOpen} />
              ))}
            </div>
          </section>
        ))
      )}

      <footer className="foot">
        <a className="powered-by" href="https://cadbuildr.com" target="_blank" rel="noreferrer">
          <span>Powered by</span>
          <img src="cadbuildr-logo.svg" alt="CADbuildr" />
          <span className="cb">CADbuildr</span>
        </a>
        <span>MIT — fork freely.</span>
      </footer>

      <AnimatePresence>
        {open ? (
          <>
            <motion.div
              className="scrim"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setOpen(null)}
            />
            <Configurator pyodide={pyodide} entry={open} onClose={() => setOpen(null)} />
          </>
        ) : null}
      </AnimatePresence>
    </div>
  );

  if (!sdkKeyId && !sessionToken) {
    return (
      <div className="page">
        <div className="viewer-status error big" style={{ flexDirection: "column", gap: 8 }}>
          <strong>No SDK key configured.</strong>
          <span style={{ maxWidth: 420, textAlign: "center" }}>
            Set <code>VITE_CADBUILDR_SDK_KEY_ID</code> (or the GitHub Actions secret{" "}
            <code>CADBUILDR_SDK_KEY_ID</code>). Get a key from{" "}
            <a href="https://hub.cadbuildr.com/settings" target="_blank" rel="noreferrer">
              hub Settings
            </a>
            .
          </span>
        </div>
      </div>
    );
  }

  // Server flow (sessionToken) takes precedence and skips the hub mint; otherwise
  // use the publishable keyId browser flow.
  const providerAuth = sessionToken
    ? { sessionToken }
    : { keyId: sdkKeyId, projectKey };

  return (
    <CadbuildrProvider baseUrl={kernelApiBaseUrl} hubBaseUrl={hubBaseUrl} {...providerAuth}>
      {content}
    </CadbuildrProvider>
  );
}

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(<App />);
