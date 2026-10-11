const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { EventEmitter } = require("node:events");
const project = process.argv[2];
const source = fs.readFileSync(path.join(__dirname, "../integrations/ide-companion/extension.js"), "utf8");

async function check(tool, file) {
  const folder = path.join(project, tool);
  fs.mkdirSync(folder, { recursive: true });
  const commands = {};
  const config = { toolId: tool, integration: `${tool}-extension`, root: path.join(project, "data") };
  const vscode = { workspace: { isTrusted: true, workspaceFolders: [{ uri: { fsPath: folder } }], getConfiguration: () => ({ get: (key) => config[key] }) },
    commands: { registerCommand: (id, fn) => { commands[id] = fn; return { dispose() {} }; } }, window: { showWarningMessage() {} } };
  const cp = { spawn: () => {
    const child = new EventEmitter();
    child.stdout = new EventEmitter(); child.stderr = new EventEmitter();
    child.stdin = { end: () => { queueMicrotask(() => {
      child.stdout.emit("data", JSON.stringify({ schema_version: 1, project_id: `project-${tool}`, context_markdown: "Bounded project marker" }));
      child.emit("close", 0);
    }); } };
    return child;
  } };
  const module = { exports: {} };
  vm.runInNewContext(source, { require: (id) => id === "vscode" ? vscode : id === "child_process" ? cp : require(id), module, process, Buffer, console });
  module.exports.activate({ subscriptions: [] });
  const result = await commands["llm-workmem.startSession"]();
  assert(result.delivery, JSON.stringify(result));
  assert.equal(result.delivery.agent_read, "unverified");
  const target = path.join(folder, file);
  assert(fs.readFileSync(target, "utf8").includes("Bounded project marker"));
  assert.equal(result.delivery.context_sha256.length, 64);
  fs.writeFileSync(target, "user-owned native instruction");
  const rejected = await commands["llm-workmem.startSession"]();
  assert.equal(rejected.status, "unavailable");
  assert.equal(fs.readFileSync(target, "utf8"), "user-owned native instruction");
  vscode.workspace.isTrusted = false;
  assert.equal((await commands["llm-workmem.startSession"]()).status, "skipped");
}
(async () => {
  await check("vscode", ".github/instructions/llm-workmem.instructions.md");
  await check("kiro", ".kiro/steering/llm-workmem.md");
  await check("trae", ".trae/rules/llm-workmem.md");
  console.log("Companion: native files for 3 hosts, hashes, ownership and workspace trust passed");
})().catch((error) => { console.error(error); process.exitCode = 1; });
