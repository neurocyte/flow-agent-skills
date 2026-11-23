#!/bin/sh
# Store the Claude Code session id on the flow terminal that runs this session.
# get_terminals then reports it. Outside a flow terminal this does nothing.
[ -n "$FLOW_SOCKET" ] && [ -n "$FLOW_TERMINAL" ] || exit 0
command -v flow >/dev/null 2>&1 || exit 0
session=$(sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([A-Za-z0-9-]*\)".*/\1/p' | head -n 1)
[ -n "$session" ] || exit 0
flow --exec "set_terminal_session:$FLOW_TERMINAL:$session" </dev/null >/dev/null 2>&1
exit 0
