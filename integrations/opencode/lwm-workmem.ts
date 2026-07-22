import type { Plugin } from "@opencode-ai/plugin"

const ROOT = "/Users/ethan/Library/Mobile Documents/com~apple~CloudDocs/Downloads/LLM-WorkMem"
const LWM = "/Users/ethan/Library/Application Support/llm-workmem-runtime/app/venv/bin/lwm"

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
    try {
      await $`${LWM} hub lifecycle ${phase} --tool opencode --project ${directory} --session-id ${sessionID} --root ${ROOT} --source native-hook`.quiet().nothrow()
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
      if (event.type === "session.deleted") await lifecycle("stop", event)
    },

    "experimental.chat.system.transform": async (_input, output) => {
      try {
        const result = await $`${LWM} hub context --tool opencode --project ${directory} --limit 6 ${ROOT}`
          .quiet()
          .nothrow()
        const context = result.exitCode === 0 ? result.text().trim() : ""
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

    "session.idle": async ({ event }) => {
      await finalize(event, "idle")
    },

    "session.error": async ({ event }) => {
      await finalize(event, "error")
    },
  }
}

export default LlmWorkmemPlugin
