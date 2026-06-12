/**
 * Runtime glue between the in-browser Python (Pyodide + cadbuildr-stdlib) and the
 * React showcase. The catalogue UI is built entirely from the manifest this module
 * fetches, so adding a part in Python needs zero changes here.
 */
import {
  initializeCadPyodideRuntime,
  runCadPythonCode,
  type PyodideLike,
} from "@cadbuildr/cad-pyodide-runtime";
import { type KernelDag } from "@cadbuildr/cad-kernel-r3f";

import { LOCAL_STDLIB_URL_SEGMENT, LOCAL_STDLIB_WHEEL_FILE } from "./stdlibLocal";

const FOUNDATION_IMPORT_PATH = "cadbuildr.foundation";
const FOUNDATION_DAG_UTILS_PATH = "cadbuildr.foundation.dag_utils";
const FOUNDATION_PACKAGE_NAME = "cadbuildr-foundation";
const FOUNDATION_VERSION = "^0.2.12";
const STDLIB_IMPORT_PATH = "cadbuildr.stdlib";

export type ParamSpec = {
  name: string;
  kind: "enum" | "number" | "bool";
  label?: string;
  default?: string | number | boolean;
  unit?: string;
  choices?: Array<string | number>;
  min?: number;
  max?: number;
  step?: number;
};

export type CatalogEntry = {
  id: string;
  category: string;
  subcategory: string;
  name: string;
  standard: string;
  description: string;
  module: string;
  cls: string;
  params: ParamSpec[];
  featured: boolean;
  example_config: Record<string, string | number | boolean>;
};

export type PartConfig = Record<string, string | number | boolean>;

function resolveStdlibWheelUrl(): string {
  const explicit = (import.meta.env.VITE_STDLIB_PACKAGE_WHEEL_URL as string | undefined)?.trim();
  if (explicit) return explicit;
  const base = import.meta.env.BASE_URL ?? "/";
  const normalized = base.endsWith("/") ? base : `${base}/`;
  return `${normalized}${LOCAL_STDLIB_URL_SEGMENT}/${LOCAL_STDLIB_WHEEL_FILE}`;
}

function foundationCompatibilityScript(): string {
  return `
from importlib import import_module
import sys
import types

foundation = import_module(${JSON.stringify(FOUNDATION_IMPORT_PATH)})
_submodules = ("gen", "gen.models", "gen.runtime", "dag_utils", "utils", "helpers", "constants")
for _prefix in ("cad_package", "cadbuildr"):
    legacy_alias = _prefix + ".foundation"
    sys.modules[legacy_alias] = foundation
    _root = sys.modules.get(_prefix)
    if _root is None:
        _root = types.ModuleType(_prefix)
        _root.__path__ = []
        sys.modules[_prefix] = _root
    setattr(_root, "foundation", foundation)
    for _suffix in _submodules:
        try:
            _mod = import_module(${JSON.stringify(FOUNDATION_IMPORT_PATH)} + "." + _suffix)
        except ModuleNotFoundError:
            continue
        sys.modules[legacy_alias + "." + _suffix] = _mod
`.trim();
}

function foundationShowRebindScript(): string {
  return `
import builtins
from importlib import import_module

_root = import_module(${JSON.stringify(FOUNDATION_IMPORT_PATH)})
_dag_utils = import_module(${JSON.stringify(FOUNDATION_DAG_UTILS_PATH)})
_hook = builtins.show
_root.show = _hook
_dag_utils.show = _hook
`.trim();
}

function stdlibInstallScript(wheelUrl: string): string {
  return `
import importlib
import micropip

wheel_url = ${JSON.stringify(wheelUrl)}
try:
    importlib.import_module(${JSON.stringify(STDLIB_IMPORT_PATH)})
    _needs_install = False
except Exception:
    _needs_install = True

if _needs_install and wheel_url:
    await micropip.install(wheel_url, deps=False)

importlib.import_module(${JSON.stringify(STDLIB_IMPORT_PATH)})
`.trim();
}

/** Boot Pyodide, install foundation + the stdlib wheel, and rebind show(). */
export async function bootstrapRuntime(): Promise<PyodideLike> {
  const pyodide = await initializeCadPyodideRuntime({
    packages: {
      foundation: FOUNDATION_VERSION,
      foundationPackageName: FOUNDATION_PACKAGE_NAME,
    },
    foundationImportPath: FOUNDATION_IMPORT_PATH,
    foundationDagUtilsPath: FOUNDATION_DAG_UTILS_PATH,
  });
  await pyodide.runPythonAsync(foundationCompatibilityScript());
  await pyodide.runPythonAsync(foundationShowRebindScript());
  await pyodide.runPythonAsync(stdlibInstallScript(resolveStdlibWheelUrl()));
  return pyodide;
}

/** Read the part catalogue manifest out of the installed stdlib. */
export async function fetchManifest(pyodide: PyodideLike): Promise<CatalogEntry[]> {
  const json = (await pyodide.runPythonAsync(
    `
import json
from cadbuildr.stdlib.catalog import get_catalog_manifest
json.dumps(get_catalog_manifest())
`.trim(),
  )) as unknown as string;
  return JSON.parse(json) as CatalogEntry[];
}

/** Build the Python that instantiates a configured part and shows it. */
export function buildRenderSource(entry: CatalogEntry, config: PartConfig): string {
  const cfgJson = JSON.stringify(config);
  return `
import json
from ${entry.module} import ${entry.cls}
from cadbuildr.foundation import show
show(${entry.cls}(**json.loads(${JSON.stringify(cfgJson)})))
`.trim();
}

/** Run a render and return the resulting kernel DAG (or null). */
export async function renderPart(
  pyodide: PyodideLike,
  entry: CatalogEntry,
  config: PartConfig,
): Promise<KernelDag | null> {
  const result = await runCadPythonCode(pyodide, buildRenderSource(entry, config), {
    foundationImportPath: FOUNDATION_IMPORT_PATH,
    foundationDagUtilsPath: FOUNDATION_DAG_UTILS_PATH,
  });
  return (result.dag as KernelDag | null) ?? null;
}

/** Default config for an entry: each param default, overlaid with the example. */
export function defaultConfig(entry: CatalogEntry): PartConfig {
  const cfg: PartConfig = {};
  for (const p of entry.params) {
    if (p.default !== undefined) cfg[p.name] = p.default;
  }
  return { ...cfg, ...entry.example_config };
}
