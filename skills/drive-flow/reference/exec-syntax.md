# Command syntax and output

## `--exec`

```
flow --exec "get_focus;get_buffer_text:3:1:20" </dev/null
```

- Commands are separated by `;`, and arguments by `:`.
- An argument that parses as an integer is sent as an integer. All other
  arguments are strings.
- An argument cannot contain `;` or `:`. A path with a Windows drive letter
  (`C:\...`) and a `file:line` link need `--exec-file`.
- flow runs the commands one at a time. It stops at the first command that
  fails and skips the rest.

## `--exec-file`

```
flow --exec-file script.flow </dev/null
```

The file has one command on each line: the command name, then zero or more
JSON values, separated by spaces. Empty lines and lines that start with `#`
are ignored.

```
# open a location, then show the cursors
navigate {"file": "/abs/path/src/main.c", "line": 42, "column": 7}
get_editors
navigate_file_link "/abs/path/src/main.c:42:7"
```

Write the script to a file. Do not pipe it into `flow` and do not use
`/dev/stdin`, because flow reads piped standard input as a new buffer.

## File arguments

```
flow --connect NAME --no-wait src/main.c:42:7 +10 notes.txt </dev/null
```

The client opens each file argument in the running flow. Without
`--no-wait`, the client then waits until the user closes the files, as an
`$EDITOR` does. `FILE:LINE`, `FILE:LINE:COLUMN` and `+LINE FILE` give a
location. The client makes a relative path absolute against its own current
directory. `--literal` turns off the `:LINE` and `+LINE` syntax for a file
name that contains a `:`.

## Output

- No flag: text. One line for each data reply, with the elements of the top
  level array separated by tabs. Strings print as they are, all other values
  as JSON. Acknowledgments print nothing. Errors go to stderr.
- `--json`: one JSON object for each reply,
  `{"id": N, "command": NAME, "reply": VALUE}`. The id is the position of
  the command in the script, from 1. Data replies, `"ok"` and errors all
  print.
- `--cbor`: the same values as a CBOR sequence.

The text format is easy to read, but a tab or a newline in a string breaks
its columns. If you parse the output, use `--json`.

## Exit codes and waiting

- Exit code 0: flow accepted every command.
- Exit code 1: a command failed, or the connect failed. The error is on
  stderr, for example
  `flow exec: error in std.log: goto_line failed: CommandNotFound: goto_line`.
- Without flags, the client waits for all replies, then disconnects.
- `--no-wait`: the client exits after flow acknowledges all requests.
- `--keep-open`: the client stays connected after the script and prints
  later replies (`follow_log`, `follow_trace`) until flow quits or the
  client is stopped. A failed request still ends it with exit code 1. It
  cannot be used with `--no-wait`.
- `--log-stdout`: log the client's replies and buffer events. With `--exec`,
  `--exec-file` or `--json`, these log lines go to stderr.

## Errors that are not on stderr

Some failures go only to the flow log. If a command acknowledges but the
result is not what you expect, run `get_log 20`.
