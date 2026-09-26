"use strict";

const cp = require("child_process");
const crypto = require("crypto");
const os = require("os");
const path = require("path");
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
  return configuration().get("binary") || process.env.LWM_BIN || "lwm";
}

function sessionId() {
  return `ide-${crypto.randomUUID()}`;
}

function bridge(phase) {
  const projectPath = workspacePath();
  if (!projectPath) {
    return Promise.resolve({ status: "skipped", reason: "no_workspace" });
  }

  if (phase === "start" && !activeSession) {
    activeSession = sessionId();
  }
  const currentSession = activeSession || sessionId();
  const tool = configuration().get("toolId") || "vscode";
  const integration = configuration().get("integration") || "vscode-extension";
  const request = {
    phase,
    tool,
    project_path: projectPath,
    session_id: currentSession,
    source: "ide-extension",
    host_proof: {
      integration,
      event: phase,
      session_id: currentSession
    }
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

function activate(context) {
  const start = () => bridge("start");
  const stop = () => {
    if (!activeSession || stopPromise) {
      return stopPromise || Promise.resolve({ status: "skipped", reason: "not_started" });
    }
    stopPromise = bridge("stop");
    return stopPromise;
  };

  context.subscriptions.push(vscode.commands.registerCommand("llm-workmem.startSession", start));
  context.subscriptions.push(vscode.commands.registerCommand("llm-workmem.stopSession", stop));
  void start();
  context.subscriptions.push({ dispose: () => void stop() });
}

function deactivate() {
  return stopPromise || (activeSession ? bridge("stop") : undefined);
}

module.exports = { activate, deactivate };
