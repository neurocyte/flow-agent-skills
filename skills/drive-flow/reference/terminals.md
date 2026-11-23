# Terminals

Flow has terminal panels. Each terminal has an integer id. A process in a
terminal panel gets this id in `FLOW_TERMINAL`.

## List the terminals

`get_terminals` replies once for each terminal:

```
["terminal", id, title, [argv], cwd, state, visible|hidden, focused|unfocused]
```

- state is `idle`, `alt_screen`, `activity`, `busy`, `bell`, `exited` or
  `exited_error`.
- cwd is the directory that the shell reports with OSC 7. It is empty until
  the shell reports one.

## Read the output of the last command

```
flow --json --exec get_terminal_output:ID </dev/null
```

The replies are `["command_output", exit_code, state]`, then
`["line", number, text]` for each line of the output. state is `running` or
`done`. exit_code is null while the command runs. A shell that does not
report exit codes also gives null.

This query needs shell integration marks (OSC 133 escape sequences that the
shell writes around its prompt and each command). Task terminals always have
them. Fish 4.0 and later writes them itself. Bash and zsh write them only
after the user adds them to the shell startup file.

If `get_terminal_output` replies only `ok`, the terminal has no marks. Then:

1. Use `get_terminal_text` (next section) for now.
2. Tell the user that shell integration is not set up.
3. Offer the setup from the "Shell integration" section of the flow help
   (the `open_help` command, or `help.md` in the flow repository). For bash,
   it adds `PS1` and `PS0` lines to `~/.bashrc`. For zsh, it adds
   `add-zsh-hook` lines to `~/.zshrc`. Both go after the lines that set
   `PS1`, and `133;D;$?` must come first in `PS1` for the exit code.

Do not edit the user's shell startup files unless the user asks. A change
applies only to shells that start after it, or after `source ~/.bashrc`.

## Read the whole terminal

```
flow --json --exec get_terminal_text:ID </dev/null
flow --json --exec get_terminal_text:ID:100:200 </dev/null
```

The replies are `["line", number, text]` for each line of the scrollback and
the screen. Soft-wrapped rows are joined, and blank rows at the end are
dropped. Tabs come back as spaces. A full-screen program (state
`alt_screen`) gives only its visible screen. It works for hidden terminals
too.

## Run a command

```
flow --connect NAME --hold --run-in-terminal -- zig build test </dev/null
```

flow opens a task terminal and runs the command. The client waits and exits
with the exit code of the command. With `--no-wait`, the client returns at
once.

Without `--hold`, a command that exits with code 0 closes its terminal, and
its output is gone. A command that fails keeps its terminal open. With
`--hold`, the terminal stays open in both cases. Then read the output with
`get_terminal_output` on the id from `get_terminals`. The new terminal is
the one with the highest id.

Do not type into a terminal of the user. The user can be at a prompt, in an
editor or in the middle of a command.
