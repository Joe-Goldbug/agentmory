import assert from "node:assert/strict"
import fs from "node:fs"
import os from "node:os"
import path from "node:path"

const outboxRoot = process.argv[2] || fs.mkdtempSync(path.join(os.tmpdir(), "lwm-opencode-test-"))
process.env.LWM_ROOT = outboxRoot
const { default: plugin } = await import("../integrations/opencode/lwm-workmem")

// A local transport double only: no OpenCode server or provider requests.
const requests: any[] = []
let identityReady = false
let failStop = false
const shell = (_strings: TemplateStringsArray, ...values: any[]) => {
  const request = values.find((v) => typeof v === "string" && v.startsWith("{"))
  requests.push(JSON.parse(request))
  return { quiet() { return this }, nothrow() {
    if (failStop && requests.at(-1)?.phase === "stop") throw new Error("controlled host exit after capture")
    return Promise.resolve({ exitCode: 0, text: () => JSON.stringify({ context_markdown: "project marker", ...(identityReady ? { project_id: "fixture-project", project_path: "/tmp/project" } : {}) }) })
  } }
}
const hooks: any = await plugin({ directory: "/tmp/project", $: shell } as any)
for (const id of ["turn1", "turn2"]) {
  await hooks["chat.message"]({ sessionID: "s", messageID: id }, { message: { id }, parts: [{ type: "text", text: "Please pass tests" }] })
  await hooks["tool.execute.after"]({ sessionID: "s", callID: id, tool: "bash", args: {} }, { output: "FAIL: pytest exit 1" })
  await hooks["experimental.text.complete"]({ sessionID: "s", partID: id }, { text: "<think>irrelevant deliberation</think>Tests still failing" })
  for (const type of ["session.idle", "session.idle", "session.error"]) await hooks.event({ event: { type, properties: { sessionID: "s" } } })
}
await hooks.event({ event: { type: "session.deleted", properties: { info: { id: "s" } } } })
const stops = requests.filter((r) => r.phase === "stop")
assert.equal(stops.length, 2)
assert.notEqual(stops[0].task_id, stops[1].task_id)
assert(stops.every((r) => r.handoff.verifications[0].includes("FAIL")))
assert(!JSON.stringify(stops).includes("Please pass tests"))
assert(!JSON.stringify(stops).includes("irrelevant deliberation"))
assert(JSON.stringify(stops).includes("Tests still failing"))
const output = { system: ["native instruction"] }
await hooks["experimental.chat.system.transform"]({}, output)
assert.equal(output.system[0], "native instruction")
assert(output.system[1].includes("project marker"))
const sdkHooks: any = await plugin({ directory: "/tmp/project", $: shell, client: { session: { messages: async () => ({ data: [
  { info: { role: "assistant", parentID: "old-turn" }, parts: [{ type: "text", text: "Old unrelated report", id: "old" }] },
  { info: { role: "assistant", parentID: "sdk-turn" }, parts: [
    { type: "reasoning", text: "private thought" },
    { type: "tool", callID: "c", tool: "read", state: { status: "completed", output: 'interval_seconds=21600; run_on_boot=true' } },
    { type: "text", text: "Actual file read; launchd unknown", id: "final" },
  ] },
] }) } } } as any)
await sdkHooks["chat.message"]({ sessionID: "sdk", messageID: "sdk-turn" }, { message: { id: "sdk-turn" }, parts: [] })
await sdkHooks.event({ event: { type: "session.idle", properties: { sessionID: "sdk" } } })
const sdkStop = requests.at(-1)
assert(sdkStop.handoff.verifications[0].includes("run_on_boot=true"))
assert(!JSON.stringify(sdkStop).includes("private thought"))
assert(!JSON.stringify(sdkStop).includes("Old unrelated report"))
await hooks["chat.message"]({ sessionID: "events", messageID: "u-native" }, { message: { id: "u-native" }, parts: [] })
await hooks.event({ event: { type: "message.updated", properties: { info: { id: "a-native", sessionID: "events", role: "assistant", parentID: "u-native" } } } })
await hooks.event({ event: { type: "message.part.updated", properties: { part: { id: "tool-native", messageID: "a-native", type: "tool", tool: "read", callID: "c-native", state: { status: "completed", output: '"run_on_boot": true; "interval_seconds":21600' } } } } })
await hooks.event({ event: { type: "session.idle", properties: { sessionID: "events" } } })
assert(requests.at(-1).handoff.verifications[0].includes('"run_on_boot": true'))
identityReady = true
const outboxHooks: any = await plugin({ directory: "/tmp/project", $: shell } as any)
await outboxHooks.event({ event: { type: "session.created", properties: { info: { id: "outbox-session" } } } })
await outboxHooks["chat.message"]({ sessionID: "outbox-session", messageID: "outbox-turn" }, { message: { id: "outbox-turn" }, parts: [{ type: "text", text: "private request" }] })
await outboxHooks["tool.execute.after"]({ sessionID: "outbox-session", callID: "read", tool: "read" }, { output: '"interval_seconds": 21600; "run_on_boot": true' })
failStop = true
for (let i = 0; i < 2; i++) await outboxHooks.event({ event: { type: "session.idle", properties: { sessionID: "outbox-session" } } })
const day = new Date().toISOString().slice(0, 10)
const outbox = path.join(outboxRoot, "raw/events/inbox", day)
const files = fs.readdirSync(outbox).filter((name) => name.endsWith(".json"))
assert.equal(files.length, 1)
const durable = JSON.parse(fs.readFileSync(path.join(outbox, files[0]), "utf8"))
assert(durable.verification[0].includes('"run_on_boot": true'))
assert.equal(durable.project_id, "fixture-project")
assert.equal(durable.source.kind, "native-plugin-outbox")
assert(!JSON.stringify(durable).includes("private request"))
process.env.LWM_ANALYSIS_JOB = "1"
assert.deepEqual(await plugin({ directory: "/tmp/project", $: shell } as any), {})
console.log("OpenCode: two turns, repeated idle/error/delete, results, context, analysis bypass passed")
