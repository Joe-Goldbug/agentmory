import type { Plugin } from "@opencode-ai/plugin"
import { homedir } from "node:os"
import { createHash } from "node:crypto"
import { mkdirSync, existsSync, writeFileSync, renameSync } from "node:fs"
import { join, resolve } from "node:path"

const ROOT = process.env.LWM_ROOT ?? `${homedir()}/Library/Application Support/llm-workmem-runtime/llm-workmem`
const LWM = process.env.LWM_BIN ?? `${homedir()}/Library/Application Support/llm-workmem-runtime/app/venv/bin/lwm`
type Turn = { id: string; prompt: string; results: Map<string, string>; reports: Map<string, string>; finalized: boolean }
const bounded = (value: unknown, limit = 240): string => typeof value === "string" ? value.trim().slice(0, limit) : ""
const assistantReport = (value: unknown): string => typeof value === "string" ? value.replace(/<think>[\s\S]*?<\/think>/gi, "").split("<think>")[0].trim() : ""

export const LlmWorkmemPlugin: Plugin = async ({ directory, $, client }) => {
  if (process.env.LWM_ANALYSIS_JOB === "1") return {}
  const turns = new Map<string, Turn>()
  const parents = new Map<string, { sessionID: string; parentID: string }>()
  const counts = { messages: 0, parts: 0, matches: 0, sdkMessages: 0 }
  let identity: { project_id: string; project_path: string } | undefined
  const persistResults = (id: string, turn: Turn): boolean => {
    if (!identity || (!turn.results.size && !turn.reports.size)) return false
    const hex = createHash("sha256").update(`opencode:${id}:${turn.id}`).digest("hex")
    const eventId = `${hex.slice(0, 8)}-${hex.slice(8, 12)}-5${hex.slice(13, 16)}-8${hex.slice(17, 20)}-${hex.slice(20, 32)}`
    const timestamp = new Date().toISOString()
    const target = join(ROOT, "raw", "events", "inbox", timestamp.slice(0, 10), `${eventId}.json`)
    const event = { schema_version: 2, event_id: eventId, timestamp, tool: "opencode",
      project_id: identity.project_id, project_path: identity.project_path,
      event_type: turn.results.size ? "verification" : "project_status", importance: "project", privacy: "sanitized",
      task: "Observed OpenCode turn results", task_id: `opencode:${id}:${turn.id}`, session_id: id,
      decisions: [], changes: [], files_touched: [], verification: Array.from(turn.results.values()).slice(-8),
      risks: Array.from(turn.reports.values()).slice(-8), open_questions: ["Task completion and claim support are unknown unless explicitly verified."],
      source: { kind: "native-plugin-outbox", path: "opencode/native-message-results", capture: counts },
      tags: ["opencode", "structured-summary", "native-outbox"] }
    try {
      const body = JSON.stringify(event)
      if (Buffer.byteLength(body) > 16384) return false
      mkdirSync(join(ROOT, "raw", "events", "inbox", timestamp.slice(0, 10)), { recursive: true, mode: 0o700 })
      if (existsSync(target)) return true
      const temporary = `${target}.${process.pid}.tmp`
      writeFileSync(temporary, body, { flag: "wx", mode: 0o600 })
      renameSync(temporary, target)
      return true
    } catch { return false }
  }
  const captureParts = (turn: Turn, parts: any[]) => {
    for (const part of parts) {
      if (part.type === "tool" && (part.state?.status === "completed" || part.state?.status === "error")) {
        const text = part.state.status === "error" ? part.state.error : part.state.output
        turn.results.set(part.callID, bounded(`Observed ${part.tool} output (${part.state.status}): ${text}`, 1000))
      } else if (part.type === "text" && !part.synthetic && !part.ignored) {
        const report = assistantReport(part.text)
        if (report) turn.reports.set(part.id, bounded("Assistant report (unverified): " + report))
      }
    }
  }
  const bridge = async (request: Record<string, unknown>) => {
    try {
      const result = await $`env LWM_HOST_BRIDGE=1 ${LWM} hub bridge ${JSON.stringify(request)} --root ${ROOT}`.quiet().nothrow()
      if (result.exitCode === 0) {
        try {
          const response = JSON.parse(result.text())
          if (typeof response.project_id === "string" && /^[a-zA-Z0-9_-]+$/.test(response.project_id) && typeof response.project_path === "string" && (resolve(directory) === resolve(response.project_path) || resolve(directory).startsWith(resolve(response.project_path) + "/"))) identity = response
        } catch {}
      }
      return result
    } catch { return undefined }
  }
  const sessionID = (event: unknown): string => {
    const p = (event as { properties?: Record<string, any> })?.properties ?? {}
    return String(p.sessionID ?? p.sessionId ?? p.info?.sessionID ?? p.info?.id ?? "")
  }
  const lifecycle = async (phase: "start" | "stop", event: unknown, turn?: Turn) => {
    const id = sessionID(event)
    if (!id) return
    const summary = turn && (turn.results.size || turn.reports.size) ? {
      task_id: `opencode:${id}:${turn.id}`,
      objective: "Observed OpenCode turn results",
      current_state: Array.from(turn.reports.values()).at(-1) || "Tool outputs observed; completion unknown",
      verifications: Array.from(turn.results.values()).slice(-8),
      risks: Array.from(turn.reports.values()).slice(-8),
      open_questions: ["Task completion and claim support are unknown unless explicitly verified."],
    } : undefined
    return bridge({
      phase, tool: "opencode", project_path: directory, session_id: id,
      task_id: turn ? `opencode:${id}:${turn.id}` : undefined,
      task: phase === "stop" ? `OpenCode turn stopped; completion unknown; capture=${JSON.stringify(counts)}` : undefined,
      handoff: summary, source: "native-hook",
      host_proof: { integration: "opencode-plugin", event: String((event as any)?.type ?? phase), session_id: id },
    })
  }
  const finalize = async (event: unknown) => {
    const id = sessionID(event)
    const turn = turns.get(id)
    if (!turn || turn.finalized) return
    turn.finalized = true
    // Native SDK fallback covers hosts that omit text/tool completion hooks.
    if (!turn.results.size && !turn.reports.size && client?.session?.messages) {
      try {
        let response: any
        try { response = await client.session.messages({ path: { id }, query: { directory, limit: 40 }, signal: AbortSignal.timeout(2500) }) } catch {}
        if (!Array.isArray(response?.data)) response = await (client.session.messages as any)({ sessionID: id, directory, limit: 40 }, { signal: AbortSignal.timeout(2500) })
        for (const message of response.data ?? []) {
          counts.sdkMessages++
          if (message.info.role !== "assistant" || message.info.parentID !== turn.id) continue
          captureParts(turn, message.parts)
        }
      } catch { /* The host must remain usable if local observation fails. */ }
    }
    const persisted = persistResults(id, turn)
    const result = await lifecycle("stop", event, persisted ? { ...turn, results: new Map(), reports: new Map() } : turn)
    // A failed local bridge may retry on the next callback; successful idle,
    // error and deleted callbacks share the same native message identity.
    if (!result || result.exitCode !== 0) turn.finalized = false
  }
  const readContext = async (): Promise<string> => {
    const result = await bridge({ phase: "context", tool: "opencode", project_path: directory, limit: 6 })
    if (!result || result.exitCode !== 0) return ""
    try { return String(JSON.parse(result.text()).context_markdown ?? "").trim() } catch { return "" }
  }
  return {
    event: async ({ event }) => {
      if (event.type === "message.updated" && event.properties.info.role === "assistant") {
        counts.messages++
        const info = event.properties.info
        if (parents.size >= 128 && !parents.has(info.id)) parents.delete(parents.keys().next().value!)
        parents.set(info.id, { sessionID: info.sessionID, parentID: info.parentID })
      }
      if (event.type === "message.part.updated") {
        counts.parts++
        const part = event.properties.part
        const parent = parents.get(part.messageID)
        const turn = parent && turns.get(parent.sessionID)
        if (turn && !turn.finalized && parent.parentID === turn.id) { counts.matches++; captureParts(turn, [part]) }
      }
      if (event.type === "session.created") await lifecycle("start", event)
      if (event.type === "session.idle" || event.type === "session.error" || event.type === "session.deleted") await finalize(event)
      if (event.type === "session.deleted") turns.delete(sessionID(event))
    },
    "chat.message": async (input, output) => {
      const id = input.messageID ?? output.message.id
      const previous = turns.get(input.sessionID)
      if (previous?.id === id) return
      // Flush pending results before a new turn can replace them.
      if (previous && !previous.finalized) await finalize({ type: "session.idle", properties: { sessionID: input.sessionID } })
      const prompt = output.parts.filter((p) => p.type === "text").map((p) => (p as any).text).join(" ").slice(0, 480)
      turns.set(input.sessionID, { id, prompt, results: new Map(), reports: new Map(), finalized: false })
    },
    "tool.execute.after": async (input, output) => {
      const turn = turns.get(input.sessionID)
      if (!turn || turn.finalized) return
      const text = bounded(output.output, 1000)
      if (!text) return
      if (turn.results.size >= 8 && !turn.results.has(input.callID)) turn.results.delete(turn.results.keys().next().value!)
      turn.results.set(input.callID, bounded(`Observed ${input.tool} output (status unknown): ${text}`, 1000))
    },
    "experimental.text.complete": async (input, output) => {
      const turn = turns.get(input.sessionID)
      const report = assistantReport(output.text)
      if (!turn || turn.finalized || !report) return
      if (turn.reports.size >= 8 && !turn.reports.has(input.partID)) turn.reports.delete(turn.reports.keys().next().value!)
      turn.reports.set(input.partID, bounded("Assistant report (unverified): " + report))
    },
    "experimental.chat.system.transform": async (_input, output) => {
      const context = await readContext()
      if (context) output.system.push("Shared LLM-WorkMem evidence only. Native instructions, skills and safety remain authoritative:\n" + context)
    },
    "experimental.session.compacting": async (_input, output) => {
      const context = await readContext()
      if (context) output.context.push(context)
    },
  }
}

export default LlmWorkmemPlugin
