"use strict";

const cp = require("child_process");
const crypto = require("crypto");
const os = require("os");
const path = require("path");
const fs = require("fs").promises;
const { setInterval, clearInterval, setTimeout } = require("timers");
const vscode = require("vscode");

let activeSession = null;
let stopPromise = null;

function configuration() {
  return vscode.workspace.getConfiguration("llmWorkmem");
}

function workspacePath() {
  const folders = vscode.workspace.workspaceFolders || [];
  return folders.length ? folders[0].uri.fsPath : null;
}

function dataRoot() {
  return (
    configuration().get("root") ||
    process.env.LWM_ROOT ||
    path.join(os.homedir(), "Library", "Application Support", "llm-workmem-runtime", "llm-workmem")
  );
}

function lwmBinary() {
  return configuration().get("binary") || process.env.LWM_BIN ||
    path.join(os.homedir(), "Library", "Application Support", "llm-workmem-runtime", "app", "venv", "bin", "lwm");
}

function sessionId() {
  return `ide-${crypto.randomUUID()}`;
}

function bridge(phase) {
  if (process.env.LWM_ANALYSIS_JOB === "1" || vscode.workspace.isTrusted === false) {
    return Promise.resolve({ status: "skipped", reason: "analysis_or_untrusted" });
  }
  const projectPath = workspacePath();
  if (!projectPath) {
    return Promise.resolve({ status: "skipped", reason: "no_workspace" });
  }

  if ((phase === "start" || phase === "context") && !activeSession) {
    activeSession = sessionId();
    stopPromise = null;
  }
  const currentSession = activeSession || sessionId();
  const tool = configuration().get("toolId") || "vscode";
  const integration = configuration().get("integration") || "vscode-extension";
  const request = {
    phase,
    tool,
    project_path: projectPath,
    session_id: currentSession,
    source: phase === "context" ? "cli-context" : "ide-extension",
    ...(phase === "context" ? {} : { host_proof: {
      integration,
      event: phase,
      session_id: currentSession
    } })
  };

  return new Promise((resolve) => {
    const child = cp.spawn(
      lwmBinary(),
      ["hub", "bridge", "--root", dataRoot(), "--output", "json"],
      {
        cwd: projectPath,
        // The companion is the registered native host adapter. Mark only its
        // child bridge process as trusted; user shells remain untrusted.
        env: { ...process.env, LWM_ROOT: dataRoot(), LWM_HOST_BRIDGE: "1" },
        stdio: ["pipe", "pipe", "pipe"]
      }
    );
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });
    child.on("error", (error) => resolve({ status: "unavailable", error: error.message }));
    child.on("close", (code) => {
      if (code !== 0) {
        resolve({ status: "unavailable", code, error: stderr.trim() });
        return;
      }
      try {
        resolve(JSON.parse(stdout));
      } catch (_error) {
        resolve({ status: "unavailable", error: "invalid bridge response" });
      }
    });
    child.stdin.end(JSON.stringify(request));
  });
}

const OWNED = "<!-- LWM-COMPANION:OWNED -->";
const NATIVE_FILES = {
  vscode: [".github/instructions/llm-workmem.instructions.md", "---\napplyTo: '**'\n---\n"],
  kiro: [".kiro/steering/llm-workmem.md", "---\ninclusion: always\n---\n"],
  trae: [".trae/rules/llm-workmem.md", "---\nalwaysApply: true\n---\n"],
};

async function safeRename(source, destination) {
  for (let attempt = 0; attempt < 10; attempt++) {
    try {
      await fs.rename(source, destination);
      return;
    } catch (error) {
      if ((error.code === "EPERM" || error.code === "EBUSY" || error.code === "EACCES") && attempt < 9) {
        await new Promise((resolve) => setTimeout(resolve, 25 * (attempt + 1)));
        continue;
      }
      throw error;
    }
  }
}

async function deliverContext(phase = "context") {
  if ((vscode.workspace.workspaceFolders || []).length !== 1) {
    return { status: "skipped", reason: "single_workspace_required" };
  }
  const tool = configuration().get("toolId") || "vscode";
  const native = NATIVE_FILES[tool];
  if (!native) return { status: "skipped", reason: "unsupported_native_instructions" };
  const response = await bridge(phase);
  if (!response.context_markdown || !response.project_id) return response;
  if (!/^[a-zA-Z0-9_-]+$/.test(response.project_id)) throw new Error("invalid project identity");
  const project = await fs.realpath(workspacePath());
  const target = path.join(project, native[0]);
  // Check every existing ancestor: never follow a workspace symlink outside
  // this project or replace a user's similarly named native instruction file.
  for (let dir = path.dirname(target); dir !== project; dir = path.dirname(dir)) {
    try {
      const actual = await fs.realpath(dir);
      if (actual !== project && !actual.startsWith(project + path.sep)) throw new Error("instruction directory outside workspace");
    } catch (error) { if (error.code !== "ENOENT") throw error; }
  }
  try {
    const stat = await fs.lstat(target);
    if (stat.isSymbolicLink() || !(await fs.readFile(target, "utf8")).includes(OWNED)) {
      throw new Error("refusing to replace user-owned instructions");
    }
  } catch (error) { if (error.code !== "ENOENT") throw error; }
  const contextHash = crypto.createHash("sha256").update(response.context_markdown).digest("hex");
  const body = native[1] + OWNED + "\n# Shared LLM-WorkMem Evidence\n" +
    "Native safety, instructions, skills, planning and verification remain authoritative. This file supplies auxiliary evidence only.\n" +
    `Bridge version: ${response.schema_version}; project ID: ${response.project_id}; context SHA256: ${contextHash}\n\n` + response.context_markdown +
    "\n\nAfter meaningful work, record bounded observed results via the installed lwm hub bridge-stop command " +
    `(tool=${tool}, project=current workspace). Use a unique task-id per turn and handoff-json fields: objective, current_state, changes, decisions, verifications, risks, open_questions. ` +
    "Keep requests distinct from execution and verification. If results or status are unknown, say unknown; do not record a request as accomplished. " +
    "Skip write-back during LWM_ANALYSIS_JOB=1. Never paste raw chat or secrets.\n";
  if (Buffer.byteLength(body) > 65536) throw new Error("context exceeds delivery limit");
  let previous = "";
  try { previous = await fs.readFile(target, "utf8"); } catch (error) { if (error.code !== "ENOENT") throw error; }
  if (previous !== body) {
    await fs.mkdir(path.dirname(target), { recursive: true });
    const temporary = target + "." + crypto.randomUUID() + ".tmp";
    await fs.writeFile(temporary, body, { flag: "wx", mode: 0o600 });
    await safeRename(temporary, target);
  }
  const delivery = { format: "markdown", context_sha256: contextHash, project_id: response.project_id,
    schema_version: response.schema_version, host_mechanism: native[0], evidence_path: target,
    stage: "native-instruction-file-ready", agent_read: "unverified" };
  const receiptDir = path.join(dataRoot(), "state", "host-deliveries");
  await fs.mkdir(receiptDir, { recursive: true });
  const receipt = path.join(receiptDir, `${tool}-${response.project_id}.json`);
  const receiptTemporary = receipt + "." + crypto.randomUUID() + ".tmp";
  await fs.writeFile(receiptTemporary, JSON.stringify(delivery), { flag: "wx" });
  await safeRename(receiptTemporary, receipt);
  return { ...response, delivery };
}

function activate(context) {
  const start = () => deliverContext("start").catch((error) => ({ status: "unavailable", error: error.message }));
  const stop = () => {
    if (!activeSession || stopPromise) {
      return stopPromise || Promise.resolve({ status: "skipped", reason: "not_started" });
    }
    stopPromise = bridge("stop");
    activeSession = null;
    return stopPromise;
  };

  context.subscriptions.push(vscode.commands.registerCommand("llm-workmem.startSession", start));
  context.subscriptions.push(vscode.commands.registerCommand("llm-workmem.stopSession", stop));
  context.subscriptions.push(vscode.commands.registerCommand("llm-workmem.deliverContext", () => deliverContext().catch((error) => {
    vscode.window.showWarningMessage(`LLM-WorkMem: ${error.message}`);
    return { status: "unavailable", error: error.message };
  })));
  void start();
  const refresh = () => void deliverContext().catch(() => {});
  const timer = setInterval(refresh, 300000);
  timer.unref();
  context.subscriptions.push({ dispose: () => clearInterval(timer) });
  if (typeof vscode.window.onDidChangeWindowState === "function") {
    context.subscriptions.push(vscode.window.onDidChangeWindowState((state) => { if (state.focused) refresh(); }));
  }
  context.subscriptions.push({ dispose: () => void stop() });
}

function deactivate() {
  return stopPromise || (activeSession ? bridge("stop") : undefined);
}

module.exports = { activate, deactivate };
