---
name: drive-flow
description:
  Drive a running Flow Control (flow) text editor through its remote client.
  Use it inside a flow terminal panel (FLOW_SOCKET is set). Also use it to
  open files, show a location, edit buffers, run commands, or read editor,
  terminal or log state in flow.
---

# Drive a running flow

Flow Control (`flow`) is a text editor. A running flow listens on a remote
control socket. The `flow` binary is also the client: it connects to that
socket, sends commands, prints the replies and exits.

The user starts flow. You only connect to an instance that already runs.
Never start a flow yourself.

## Connect

Find out which flow to use before you send a command.

1. If `FLOW_SOCKET` is set, you run inside a flow terminal panel. A plain
   `flow --exec ...` connects to that flow.
2. If the user gave a server name (flow started with `--server NAME`), use
   `flow --connect NAME --exec ...`.
3. Else, run `flow --list-servers --json`. Each line is one running instance
   with its socket path and its projects, current project first. If exactly
   one instance has the project you work on, connect with its `socket`
   value. If none or more than one has it, ask the user.

If `FLOW_SOCKET` is not set, always give `--connect`. Without a socket,
`flow --exec` starts a new editor in your terminal and runs the commands
there.

For remote machines, Docker containers and the limits of a forwarded socket,
read `reference/connecting.md`.

## Rules for every call

- Run `flow` with `</dev/null`. If standard input is a pipe or a file, flow
  opens it as a new `*stdin*` buffer in the user's editor.
- If you parse the output, give `--json`. Each reply is one JSON line:
  `{"id": N, "command": NAME, "reply": VALUE}`. A command sends zero or more
  data replies, then the reply `"ok"`.
- Exit code 0 means that flow accepted every command. Exit code 1 means that
  a command failed. The error is on stderr, and the commands after it did
  not run.
- An `ok` reply (the acknowledgment) means that flow accepted the command.
  It does not always mean that the command finished. `navigate` and
  `apply_workspace_edit` acknowledge after they finish. `save_buffer`
  acknowledges before the file is written.
- `--exec "cmd:arg:arg;cmd"` splits at every `;` and `:`. An argument that
  is an integer is sent as an integer, all others as strings. Arguments with
  a `:`, and arguments that are JSON objects or arrays, need `--exec-file`.
  Read `reference/exec-syntax.md` for both forms.

## Find commands

`flow --exec get_commands --json` lists every command of the running flow:
`["command", name, description, argument_types, key_hint]`. Commands with an
empty description are hidden from the command palette, but you can run them.
The list comes from the running instance, so it is always current.

## Read the editor state

These queries change nothing. Lines and columns are 1-based. A BUFID (buffer
id) looks like `["BUFID", 3]`. Queries that take a BUFID also take the
integer alone.

- `get_focus`: `["focus", kind, name, id, mode]`. kind is `mini_mode`,
  `overlay`, `panel`, `editor` or `home`.
- `get_buffers`:
  `["buffer", BUFID, path, dirty, hidden, ephemeral, file_type, lines]`,
  most recently used first. A file inside the project has a path relative to
  the project directory.
- `get_editors`: `["editor", BUFID, view_index, active, [cursors]]`. A
  cursor is `[line, column, selection]`, primary cursor first. A selection
  is `[begin_line, begin_column, end_line, end_column]` or null.
- `get_buffer_text BUFID [first_line last_line]`: `["line", number, text]`
  for each line, with unsaved changes. If the buffer is dirty, read the
  buffer, not the disk.
- `get_selection_text [BUFID]`: `["selection", number, text]` for each
  selection.
- `get_diagnostics [BUFID]`:
  `["diagnostic", BUFID, severity, [begin_line, begin_column, end_line, end_column], source, code, message]`
  from the language servers.
- `get_log [count]`: `["log", time, level, source, message]`, oldest first.
  Some errors, for example the reason that a navigation failed, go only to
  the log.
- `get_terminals`, `get_terminal_text`, `get_terminal_output`: read
  `reference/terminals.md`.
- `get_version_info`, `get_keybinds`, `get_widget_tree`: text as
  `["line", number, text]` replies, for bug reports and debugging.

## Before you send an editing command

Most editing commands act on the active editor. Run `get_focus` first. If
kind is `mini_mode` or `overlay`, a prompt or a palette is open, and it gets
the command instead of the editor. Tell the user, or ask before you close
it. If kind is `home`, no editor is open, and editor commands fail with
`CommandNotFound`.

The user can change the focus between two of your calls. To change a file,
use `apply_workspace_edit`, which edits by file path, not the active editor.

## Edit a file

`apply_workspace_edit` takes the format of an LSP workspace edit. Put it in
a script file and run it with `flow --exec-file FILE </dev/null`:

```
apply_workspace_edit [["/abs/path/main.c", null, [[[1, 11, 1, 12, "42"]], null, null, null, null]]]
```

Each edit is `[row, pos, end_row, end_pos, text]`. It replaces the range
with the text.

- Rows are 0-based, and pos is a byte offset in the line. This is not the
  1-based numbering of the queries.
- All edits of one file refer to the text before the edit. Sort them and do
  not let them overlap.
- Give null for the version and for the four hashes.
- If the file is not open, flow loads it and edits it in memory, as a hidden
  buffer. It does not save it.
- A multi-file edit stops at the first file that fails. The files before it
  stay changed.

If the user wants the change on disk, save it with `save_buffer PATH`. The
path is absolute, or the path that `get_buffers` shows. `save_buffer` with a
path that matches no buffer replies `ok` and does nothing. The
acknowledgment comes before the write, so run `get_buffers` again until
dirty is `false`.

Flow keeps the edit in its undo history, so the user can undo it.

## Open a file or a location

To show the user a location, give the file as an argument, with `--no-wait`:

```
flow --connect NAME --no-wait src/main.c:42:7 </dev/null
```

Without `--no-wait`, the client waits until the user closes the file, as an
`$EDITOR` does.

To open a location from a script, use `navigate`:

```
navigate {"file": "/abs/path/src/main.c", "line": 42, "column": 7}
```

`navigate` acknowledges after the file is open, or fails with the reason.

Inside a flow terminal, opening a file moves the focus from the terminal to
the editor. The user then types into the editor, not into your terminal. If
you open a file only for your own work, give `--no-focus`.

## Run commands in a terminal

`flow --hold --run-in-terminal -- CMD ARGS` runs a command in a new terminal
panel, waits until it exits and exits with its exit code. `--hold` keeps the
terminal open, so you can read the output. With `--no-wait`, it returns at
once. Read `reference/terminals.md` to read the output of the user's
terminals.

## See what the user sees

`get_screen` returns the last frame that flow drew. Use it to see what the
user looks at, for example a prompt, a menu, a message or a palette that
`get_focus` reports.

- In the terminal UI, the replies are `["screen", cols, rows]`,
  `["cursor", row, col, visible, shape]`, then `["line", row, text]` for
  each row of the screen. Rows and columns are 1-based. row and col are null
  when the cursor is hidden.
- In the GUI, the client writes the frame to `flow-screenshot-<ms>.png` in
  its current directory and replies `["screenshot", path]`. Read the PNG
  file, then delete it.

A change shows only after flow draws it. If the screen does not show a
change yet, run `inject_need_render` before `get_screen`.

The user drives flow too, so do not send keys or mouse events to it.

## Long running clients

`--keep-open` keeps the client connected after the script and prints later
replies, until flow quits or you stop the client. `follow_log [count]`
streams new log entries. `get_actors` lists the actors, and
`follow_trace PIID` streams the messages of one actor. Use these to debug
flow, with a timeout.
