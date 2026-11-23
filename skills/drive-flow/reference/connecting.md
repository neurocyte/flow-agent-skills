# Connecting to flow

The client finds the socket in this order:

1. `--connect NAME` or `--connect /abs/path.sock`. A name is the file
   `<state>/run/NAME.sock`.
2. The `FLOW_SOCKET` environment variable.

If neither is set, `flow` starts a new editor. `--connect disable` (or
`--no-connect`) also starts a new editor.

`<state>` is `$XDG_STATE_HOME/flow`. If `XDG_STATE_HOME` is not set, it is
`~/.local/state/flow`. On Windows without `HOME`, it is `%APPDATA%\flow`.

If the socket does not exist, the client exits with code 1:

```
flow ERROR: connect to /home/u/.local/state/flow/run/work.sock failed: No such file or directory
```

## Inside a flow terminal

flow sets `FLOW_SOCKET` and `FLOW_TERMINAL` for each terminal panel, and
`FLOW_SOCKET` for the shell commands that it runs. A plain `flow --exec ...`
connects to that flow.

Only this configuration has terminal focus handling: when the client opens a
file, flow takes the focus from the terminal and restores a maximized panel.
`--no-focus` turns it off, and `--focus` forces it.

## A named instance

The user starts flow with `--server NAME`, and the socket is
`<state>/run/NAME.sock`. Use `flow --connect NAME`. If the user did not give
a name, ask for it.

## An instance with no name

Each flow listens on `<state>/run/flow-<pid>.sock` by default. Run:

```
flow --list-servers --json </dev/null
```

Each line is one instance:

```
{"name":"flow-4721","pid":4721,"version":"v0.8.0","socket":"/home/u/.local/state/flow/run/flow-4721.sock","projects":["/home/u/src/app","/home/u/src/lib"]}
```

The first project is the current project of that instance. The others are
its background projects, most recently used first. If exactly one instance
has your project as its current project, connect with its `socket`. If none
or more than one has it, ask the user.

An instance that does not reply in time is reported as not responding.
`--list-servers` removes the socket files of crashed instances and reports
each removed file on stderr.

## A forwarded socket

The user forwards a socket of another machine to a local socket, for
example:

```
ssh -L /tmp/flow-remote.sock:/home/u/.local/state/flow/run/NAME.sock host
flow --connect /tmp/flow-remote.sock
```

`socat` can do the same. Three limits apply:

1. The client makes file arguments absolute against the local directory. If
   the paths are not the same on both machines, a file argument opens the
   wrong file or fails. Paths in `--exec` commands have the same limit.
2. A socket path longer than about 100 bytes fails. This is the Unix socket
   path limit.
3. The local `flow` must be compatible with the remote flow. The client and
   the server exchange their versions at the start of each connection.

## An agent in a Docker container

The agent runs in a container and flow runs on the host. The user sets up
the forward, and the agent only connects. If the user mounts the project at
the same path in the container, the paths are the same on both sides. Else,
the paths are different. The path limit of a forwarded socket applies.

### Bind mount of the run directory (Linux, native Docker)

Mount the directory, not the socket file. A mounted socket file keeps the
old file after flow makes a new socket, so a restarted flow is not
reachable.

```
docker run -v ~/.local/state/flow/run:/run/flow ...
flow --connect /run/flow/NAME.sock
```

The socket mode is 0600, so the user in the container must have the uid of
the host user. Docker Desktop on macOS and Windows does not pass Unix
sockets through its file sharing, so this forward does not work there.

### Relay into the container filesystem (Linux, native Docker)

This works for a container that already runs, with no change to the image.

```
pid=$(docker inspect -f '{{.State.Pid}}' CONTAINER)
sudo socat UNIX-LISTEN:/proc/$pid/root/tmp/flow.sock,fork,user=CUID,mode=0600 \
  UNIX-CONNECT:$HOME/.local/state/flow/run/NAME.sock
flow --connect /tmp/flow.sock
```

Only `socat` runs as root. CUID is the uid of the user in the container, who
must have write permission on the socket. If the container restarts, its pid
changes, and the user starts the relay again.

### sshd over `docker exec` (Docker Desktop and all other cases)

```
ssh -N -o ProxyCommand='docker exec -i CONTAINER /usr/sbin/sshd -i' \
  -o StreamLocalBindUnlink=yes \
  -R /tmp/flow.sock:$HOME/.local/state/flow/run/NAME.sock user@container
flow --connect /tmp/flow.sock
```

The image needs openssh-server, host keys and an `authorized_keys` entry for
the key of the host user. No container network and no sshd daemon are
necessary.
