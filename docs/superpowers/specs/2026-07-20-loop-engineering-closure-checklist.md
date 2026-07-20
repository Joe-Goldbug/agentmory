# Loop Engineering Closure Checklist

`lwm hub closure <root>` is the final machine-readable gate for a scheduled
LLM-WorkMem loop.

Required checks:

- `loop`: latest loop is `completed_verified`;
- `evidence`: every recorded evidence path exists;
- `source`: source package is readable;
- `runtime`: runtime package is present and readable;
- `export`: `llms.txt` exists and is readable;
- `receipt`: latest full receipt is successful;
- `health`: strict health is healthy;
- `launchd`: the configured harvest agent is loaded.

The command returns exit code 0 only for `pass`, 1 for `degraded`, and 2 for
`blocked`. A static adapter file, a generated plist, or a previous successful
test cannot replace a fresh runtime receipt.
