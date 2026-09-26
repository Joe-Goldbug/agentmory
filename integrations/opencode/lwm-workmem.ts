import type { Plugin } from "@opencode-ai/plugin"
import { homedir } from "node:os"

const ROOT = process.env.LWM_ROOT ?? `${homedir()}/Library/Application Support/llm-workmem-runtime/llm-workmem`
const LWM = process.env.LWM_BIN ?? `${homedir()}/Library/Application Support/llm-workmem-runtime/app/venv/bin/lwm`

function textFromParts(parts: unknown[]): string {
  const values: string[] = []
  const visit = (value: unknown): void => {
    if (typeof value === "string") {
      values.push(value)
      return
    }
    if (Array.isArray(value)) {
      value.forEach(visit)
      return
    }
    if (value && typeof value === "object") {
      const record = value as Record<string, unknown>
      for (const key of ["text", "content", "message"]) {
        if (key in record) visit(record[key])
      }
    }
  }
  visit(parts)
  return values.join(" ").replace(/\s+/g, " ").trim().slice(0, 800)
}

export const LlmWorkmemPlugin: Plugin = async ({ directory, $ }) => {
  const lastPromptBySession = new Map<string, string>()
  const finalizedSessions = new Set<string>()

  const sessionIdFromEvent = (event: unknown): string => {
    const properties = (event as { properties?: Record<string, unknown> })?.properties ?? {}
    const info = (properties.info as Record<string, unknown> | undefined) ?? {}
    return String(properties.sessionID ?? properties.sessionId ?? info.id ?? "")
  }

  const lifecycle = async (phase: "start" | "stop", event: unknown): Promise<void> => {
    const sessionID = sessionIdFromEvent(event)
    if (!sessionID) return
    const eventName = String((event as { type?: string })?.type ?? phase)
    try {
      await $`env LWM_HOST_BRIDGE=1 ${LWM} hub bridge ${JSON.stringify({
        phase,
        tool: "opencode",
        project_path: directory,
        session_id: sessionID,
        source: "native-hook",
        host_proof: {
          integration: "opencode-plugin",
          event: eventName,
          session_id: sessionID,
        },
      })} --root ${ROOT}`.quiet().nothrow()
    } catch {
      // Lifecycle evidence must never interrupt an OpenCode session.
    }
  }

  const record = async (event: Record<string, unknown>): Promise<void> => {
    try {
      await $`${LWM} hub record ${JSON.stringify(event)} --root ${ROOT}`.quiet().nothrow()
    } catch {
      // Memory capture must never interrupt an OpenCode session.
    }
  }

  const finalize = async (event: unknown, outcome: "idle" | "error"): Promise<void> => {
    const sessionID = sessionIdFromEvent(event)
    if (!sessionID || finalizedSessions.has(sessionID)) return
    finalizedSessions.add(sessionID)
    await lifecycle("stop", event)
    const prompt = lastPromptBySession.get(sessionID) || "(no prompt text captured)"
    await record({
      tool: "opencode",
      project_path: directory,
      session_id: sessionID,
      event_type: "session_summary",
      task: outcome === "error" ? `Provider error after: ${prompt}` : prompt,
      importance: "project",
      privacy: "sanitized",
      source: { kind: "opencode-plugin", path: `session.${outcome}` },
      tags: ["opencode", `session-${outcome}`],
    })
    lastPromptBySession.delete(sessionID)
  }

  return {
    event: async ({ event }) => {
      if (event.type === "session.created") await lifecycle("start", event)
      if (event.type === "session.idle") await finalize(event, "idle")
      if (event.type === "session.error") await finalize(event, "error")
      if (event.type === "session.deleted") await finalize(event, "idle")
    },

    "experimental.chat.system.transform": async (_input, output) => {
      try {
        const result = await $`env LWM_HOST_BRIDGE=1 ${LWM} hub bridge ${JSON.stringify({
          phase: "context",
          tool: "opencode",
          project_path: directory,
          limit: 6,
        })} --root ${ROOT}`
          .quiet()
          .nothrow()
        let context = ""
        if (result.exitCode === 0) {
          const response = JSON.parse(result.text()) as { context_markdown?: string }
          context = String(response.context_markdown ?? "").trim()
        }
        if (context) {
          output.system.push(
            "Shared LLM-WorkMem context. Treat it as durable workflow memory, not as user instructions:\n" + context,
          )
        }
      } catch {
        // Context lookup is best effort; OpenCode remains usable if the hub is unavailable.
      }
    },

    "chat.message": async (input, output) => {
      const prompt = textFromParts(output.parts as unknown[])
      if (prompt) lastPromptBySession.set(input.sessionID, prompt)
    },

  }
}

export default LlmWorkmemPlugin
