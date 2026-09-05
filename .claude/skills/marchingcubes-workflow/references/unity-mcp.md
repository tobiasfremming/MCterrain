# Unity MCP in this repo

Three separate things, and most confusion comes from conflating them:

| thing | what it is | how to see it |
|---|---|---|
| **server** | a python `mcp-for-unity` process per port, started by *an* Editor (`--http-url http://127.0.0.1:<port>`, cwd = that project) | `Get-NetTCPConnection -State Listen` on 8080–8082; `debug_request_context` shows the server your session is on |
| **bridge** | each Editor's WebSocket to *a* server — not necessarily its own | `mcpforunity://instances` on that server |
| **session** | this Claude Code session's client, bound to the URL in `.mcp.json` at startup | `/mcp` reconnects; a port edit in `.mcp.json` may not take until the session restarts |

Two Editors are usually open: MarchingCubes (6000.2.6f2) and SpaceGame
(6000.3.11f1). Each starts its own server; SpaceGame's port drifts. After a
crash-restart, the MarchingCubes Editor once attached its bridge to
SpaceGame's server, so both instances showed up on one port and the
MarchingCubes server sat empty. The instance id is the identity; the port is
not.

## Before acting

```
mcpforunity://instances   → must contain MarchingCubes@<hash> 6000.2.6f2
```

If it shows only SpaceGame: the session is on SpaceGame's server. If it is
empty: the MarchingCubes bridge is elsewhere or reloading. Probe the other
ports with `scripts/mcpcall.py`:

```bash
python .claude/skills/marchingcubes-workflow/scripts/mcpcall.py 8082 resource mcpforunity://instances
```

If MarchingCubes is attached to a server this session cannot reach, drive it
through that script with the instance pinned:

```bash
export UNITY_INSTANCE=MarchingCubes@<hash>
python .../mcpcall.py 8082 read_console '{"action":"get","count":"10","types":["error"]}'
python .../mcpcall.py 8082 execute_code '{"action":"execute"}' --code-file snippet.cs
```

`mcpcall.py` speaks streamable HTTP (initialize → notifications/initialized →
tools/call, parses `data:` SSE lines) and injects `unity_instance` into every
call. With two instances on one server, `set_active_instance` in a fresh
session was not honoured and an `execute_code` ran in SpaceGame; explicit
routing is the only safe way. Tell the user the arrangement is wrong and ask
them to point the MarchingCubes bridge at its own port; do not restart
anything yourself.

## Reloads and crashes

- Every `refresh_unity` with compile drops the bridge for 20–60 s. Poll
  `mcpforunity://editor/state` (`advice.ready_for_tools`,
  `compilation.last_domain_reload_after_unix_ms`), do not spam tool calls.
- "Unity session not ready (ping not answered)" = reloading or gone. Check
  the process (`Get-Process Unity | select MainWindowTitle, Responding`).
- Crash dumps: `%LOCALAPPDATA%\Temp\Unity\Editor\Crashes\Crash_<date>\`
  (`Editor.log` + `crash.dmp`); grep `Crash!!!` and the stack after
  `OUTPUTTING STACK TRACE`. Both Editors append to the same
  `%LOCALAPPDATA%\Unity\Editor\Editor.log`, so lines interleave.
- After a crash the crash handler restarts the Editor; unsaved scene changes
  are gone and the bridge may attach anywhere.

## execute_code

- CodeDom compiler: C# 6. No `out _` discards, no tuples, no `?.` on Unity
  objects in the strict sense, `$"…"` fine. Roslyn is not installed here.
- Fails transiently ("Compiler failed to produce the assembly") right after
  entering play mode; retry once.
- Safety filter blocks `AssetDatabase.DeleteAsset`, `File.Delete`,
  `Process.Start`. Delete files from the shell and refresh instead.
- Reflection on private members works and is the way to time or inspect
  systems without adding debug code.
- Returning a string is the result channel; keep it under a few KB.

## Play mode

- Unfocused Editor + `runInBackground = false` → frame 1 forever.
  `Application.runInBackground = true` in execute_code fixes it for the
  session.
- `Time.smoothDeltaTime` from execute_code is a fair fps estimate;
  `manage_profiler get_frame_timing` is not (reports 99 ms with an idle main
  thread when unfocused).
- Asset edits made in play mode (ScriptableObject fields, materials) persist
  after exiting. Restore them explicitly.
- `manage_camera screenshot` without a camera uses `ScreenCapture` and needs
  a visible Game view; with `camera: "Main Camera"` it renders directly and
  always works. Files land in `Assets/Screenshots/<name>.png` (plus `.meta`).

## Scripts

- `scripts/mcpcall.py` — the probe/driver client.
- `scripts/compile_check.py` — offline C# compile.
- `scripts/export_skills.py` — marketplace export.
