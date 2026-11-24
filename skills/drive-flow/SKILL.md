---
name: drive-flow
description:
  Drive a running Flow Control (flow) text editor through its remote client.
  Use it inside a flow terminal panel (FLOW_SOCKET is set). Also use it to
  open files, show a location, edit buffers, run commands, or read editor,
  terminal or log state in flow. Use it for a guided or annotated
  walk-through, a code review or a code explanation that the user reads in
  flow.
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
   with its socket path and its projects, current project first. A matching
   instance has your working directory, or a parent directory of it, as its
   current project. If exactly one instance matches, connect with its
   `socket` value.
4. If no instance matches, or more than one matches, stop and ask the user
   which instance to use. Show each instance with its name and its current
   project. If only one instance runs, ask too. Do not choose from other
   signs, for example a background project, or a project that has the file
   that the user named.

If `FLOW_SOCKET` is not set, always give `--connect`. Without a socket,
`flow --exec` starts a new editor in your terminal and runs the commands
there.

For remote machines, Docker containers and the limits of a forwarded socket,
read `reference/connecting.md`.

## Check the version

This skill supports flow `v0.7.2-2149` and later. Do this check once, after
you find the instance and before you send other commands.

1. Run `flow --version </dev/null`. This is the version of the client.
2. Run `flow --exec get_version_info </dev/null`, with the same connect flag
   as your other calls. This is the version of the flow that you drive. If
   it fails with `CommandNotFound`, that flow is too old.
3. In both outputs, read the line `version: VERSION`. VERSION is a release
   (`v0.8.0`) or a development build (`v0.7.2-2149-g9d417cb3c`, which is
   2149 commits after `v0.7.2`). A `-dirty` suffix does not change the
   order.
4. Two kinds of version are supported: a release part later than `v0.7.2`,
   and `v0.7.2-N-g...` with N 2149 or more.

If one of the two versions is not supported, stop. Tell the user both
versions and the minimum version. The user can update flow, or install an
older tag of this skill that supports the older flow. If you cannot read a
version, tell the user what you found and ask before you continue.

## Rules for every call

- Run `flow` with `</dev/null`. If standard input is a pipe or a file, flow
  opens it as a new `*stdin*` buffer in the user's editor. The only
  exceptions are the calls in "Explain code in an info box" and "Show a list
  of locations".
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

These queries change nothing. Lines and columns are 1-based. The columns of
`get_editors` and `get_diagnostics` are screen columns: a tab goes to the
next tab stop, and a wide character counts 2. A BUFID (buffer id) looks like
`["BUFID", 3]`. Queries that take a BUFID also take the integer alone.

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

## Edit at the cursor

The user can ask you to change the code at the cursor, for example "add a
doc comment to this function".

1. Run `get_editors`. The editor with active `true` is the one that the user
   works in. Its first cursor is the primary cursor. The focus can be on a
   terminal panel, and the active editor is still the right one.
2. Run `get_buffers` and find the path of that BUFID.
3. Read the lines around the cursor with `get_buffer_text BUFID FIRST LAST`.
   The buffer can hold changes that are not saved, so do not read the file
   on disk.
4. Find the code to change in that text. The cursor column is a screen
   column, so use the cursor line only to find the code. Compute the byte
   offset of the edit from the line text.
5. Make the edit with `apply_workspace_edit`, as in "Edit a file". The path
   is absolute, or the path that `get_buffers` shows.

The edit goes into the buffer, not to the disk. The cursor moves with the
text, so it stays at the same code. Do not save unless the user asks. Tell
the user the new line numbers, so that they can read the change.

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

## Walk the user through code

This recipe is for these requests: a guided review, an annotated
walk-through of a fix or a change, a code tour, and an explanation of how
some code works. For these, show the walk-through in the editor, not only in
your reply. It needs flow `v0.7.2-2170` or later.

1. Pick the stops and put them in the order of the story. For a fix, show
   the path of the bug first, then each change.
2. Open the stops as a named file list, as in "Show a list of locations".
   Give each entry a short description of one line, for example
   `2. the lock is held here`. Keep the id of the list from the reply.
3. Write a full explanation in markdown for each stop. Run the follower
   script with the id and these explanations, as in "Follow the user
   through locations". When the user goes to a stop, the script shows its
   explanation in an info box at the code.
4. In your reply, give the name of the list. Tell the user to click the
   entries or to go to the next entry. Say how long the script runs, and
   that closing the list ends the walk-through.

Do steps 2 and 3 both. The list has room for one line only, and the info
boxes hold the explanation. Send the list and the boxes through hidden
buffers, as the two sections show. Do not write the walk-through to a file
in the project, and do not open such a file in the editor.

## Explain code in an info box

To explain a symbol to the user, select it in the editor and show your
explanation in an info box next to it. The box shows markdown, the same as a
hover box from a language server. It needs flow `v0.7.2-2159` or later, for
the client and for the flow that you drive. An older flow fails with
`CommandNotFound` or an unknown flag.

1. Find the byte offset of the symbol in the file, for example with
   `grep -bo 'name' FILE`. The offset counts bytes from the start of the
   file, with two bytes for each CRLF line end. If the buffer is dirty, the
   file on disk is out of date: compute the offset from `get_buffer_text`.
2. Count the characters of the symbol. Count characters, not bytes and not
   screen columns. `größe` is 5 characters and `名前` is 2.
3. Write your explanation to a markdown file.
4. Write a script file with these lines. NAME is a buffer name such as
   `*info-7f3a*`. Make it unique, and use no `:`, `;` or spaces in it.

   ```
   navigate {"file": "/abs/path/src/main.zig"}
   goto_byte_offset 1234
   select_right 9
   show_info_box "NAME"
   delete_buffer "NAME"
   ```

5. Run the script, with the markdown file as standard input:

   ```
   flow --connect SERVER --no-wait --scratch --hidden --file-name 'NAME' --exec-file SCRIPT < EXPLAIN.md
   ```

`--scratch --hidden --file-name NAME` puts standard input in a hidden
temporary buffer named NAME. The user does not see it, and the active editor
does not change. The script starts after flow has all of the input.
`show_info_box` shows the buffer text in a box at the selection, and
`delete_buffer` then removes the buffer.

Do not use `select_range` for this. Its columns are screen columns, so a tab
or a wide character before the symbol moves the selection.

If the exit code is 1, the buffer can still be there. Remove it with
`flow --exec 'delete_buffer:NAME' </dev/null`. A NAME that is still open
fails with `BufferAlreadyOpen`.

If the cursor leaves the selection, the box closes. With `--hidden`, the
client leaves the terminal focus as it is. Add `--focus` to move the focus
to the editor.

## Show a list of locations

To give the user locations to review, open them as a named file list. The
list shows in the panel at the bottom of the editor, for example with the
results of a code review. Each entry shows a location and your description
of it. The user clicks an entry, or goes to the next or the previous entry,
and flow opens the file there. It needs flow `v0.7.2-2163` or later, for the
client and for the flow that you drive. For a walk-through, also explain
each entry in an info box, as in "Walk the user through code".

1. Write a temporary text file outside the project, with one entry on each
   line:

   ```
   src/main.zig:120:9:19 parse_args ignores an empty value
   src/main.zig:200 the error message does not name the file
   ```

   The line starts with a file link, then a space and the description. A
   line that does not start with a link is not an entry.

2. Write a script file with these lines. NAME is the name of the list.
   BUFFER is a buffer name such as `*list-7f3a*`. Make it unique, and use no
   `:`, `;` or spaces in it.

   ```
   open_filelist "NAME" "BUFFER"
   delete_buffer "BUFFER"
   ```

3. Run the script, with the text file as standard input:

   ```
   flow --connect SERVER --no-wait --scratch --hidden --file-name 'BUFFER' --exec-file SCRIPT < LIST.txt
   ```

Flow reads the list from standard input into the hidden buffer BUFFER, and
`delete_buffer` removes it. Do not open the text file in the editor, and do
not give its path to `open_filelist`. If the list does not show, run
`show_filelist`.

From flow `v0.7.2-2168`, the client prints `filelist ID`. ID is the id of
the list. The other list commands take this id, see "Manage file lists".

A file link is `PATH:LINE`, `PATH:LINE:COLUMN` or
`PATH:LINE:COLUMN:END_COLUMN`. For a range over more than one line, use
`PATH:LINE:COLUMN:END_LINE:END_COLUMN`. A path is absolute, or relative to
the project directory.

- Lines and columns are 1-based. A column is a byte offset in the line, not
  a character or a screen column. `grep -bo` gives byte offsets from the
  start of the file, so subtract the offset of the line start.
- END_COLUMN is the column after the last byte of the range. To select
  `parse_args` that starts at column 9, give `9:19`.
- With a range, flow selects the range. Without one, it puts the cursor at
  the column.

The entries keep the order of the file. If you run `open_filelist` again
with the same NAME, the new entries replace the old ones. A list with no
entries closes.

If the exit code is 1, the buffer can still be there. Remove it with
`flow --exec 'delete_buffer:BUFFER' </dev/null`.

## Manage file lists

These commands need flow `v0.7.2-2171` or later. ID is a list id, and INDEX
is the 0-based position of an entry in the list.

- `get_filelists` replies `["filelist", ID, KIND, LABEL, COUNT, SELECTED]`
  for each list. SELECTED is the INDEX of the selected entry, or null.
- `get_filelist ID [FIRST LAST]` replies `["item", INDEX, PATH, BEGIN_LINE,
  BEGIN_COL, END_LINE, END_COL, SEVERITY, TEXT]` for each entry, or for the
  entries from FIRST to LAST. `get_filelist_item ID INDEX` replies one entry.
  Lines and columns are the same as in a file link. SEVERITY is `Error`,
  `Warning`, `Information` or `Hint`.
- `set_filelist_item ID INDEX PATH BEGIN_LINE BEGIN_COL END_LINE END_COL
  SEVERITY TEXT` replaces an entry. If INDEX is the count, it adds the entry
  at the end.
- `delete_filelist_item ID INDEX` removes an entry. A list with no entries
  closes.
- `select_filelist_item ID INDEX` selects an entry and goes to its
  location, as a click does. Use it to lead the user to a stop.
- `filelist_close ID` closes the list.

`open_filelist NAME BUFFER KIND` makes a list of another kind, and
`open_filelist ID BUFFER` replaces the entries of the list ID. Flow also
uses the kinds `diagnostics` and `references` for the results of the
language server, which replace their entries. For your own lists, use the
default kind.

## Follow the user through locations

To explain each location while the user steps through a list, run the
follower script. A walk-through uses it for every stop, see "Walk the user
through code". The script follows the selected entry of the list. When the
user selects an entry and the cursor reaches it, the script shows your
explanation in an info box at the cursor. It needs flow `v0.7.2-2170` or
later, for the client and for the flow that you drive.

1. Open the list as in "Show a list of locations", and keep its id.
2. Write a JSON file with one object for each location:

   ```
   [
     {"path": "src/main.zig", "line": 120, "markdown": "### parse_args\n\nAn empty value ..."},
     {"path": "src/main.zig", "line": 200, "markdown": "..."}
   ]
   ```

   path is absolute, or relative to the project directory. line is 1-based.
   Use the same path and the first line of each entry of the list.

3. Run the script in the background. It is `scripts/follow-info-boxes.py` in
   the directory of this skill:

   ```
   python3 -I SKILL_DIR/scripts/follow-info-boxes.py --connect SERVER --timeout 1800 ID ENTRIES.json
   ```

   Without `FLOW_SOCKET`, give `--connect` as for every other call.

The user selects an entry with a click, or with the next or the previous
entry. If the cursor leaves the entry and comes back while the entry is
still selected, the script shows the box again. If the cursor leaves the
range of the box, the box closes. A scroll does not close it.

These events stop the script: the user closes the list, flow quits, the
timeout ends, or you send SIGTERM. Tell the user that the script runs, and
for how long. If the script stopped and the user is not done, you can start
it again.

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

`follow_editors` streams the events of all editors, in all views, as
`["editor", BUFID, view_index, event]`. Some events:

- `["E", "pos", lines, row, col]`: the primary cursor moved.
- `["E", "sel", begin_row, begin_col, end_row, end_col]`, or
  `["E", "sel", "none"]`: the primary selection changed.
- `["E", "view", lines, rows, top_row]`: the view scrolled.
- `["E", "open", path, ...]` and `["E", "close"]`: the editor opened or
  closed a buffer.
- `["E", "dirty", true]`: the buffer has changes that are not saved.

Rows and columns in events are 0-based, and columns are screen columns. This
is not the numbering of the queries. When a navigation opens another file,
the `pos` and `sel` events of the new buffer come before its `open` event.
Use the BUFID to find the path, with `get_buffers`. The BUFID of `close` is
null.

`follow_filelist ID` streams the events of one file list:
`["filelist", ID, "selected", INDEX]` when the selection changes, with
null for no selection, `["filelist", ID, "changed"]` when the entries
change, and `["filelist", ID, "closed"]` when the list closes. The first
reply gives the current selection.
