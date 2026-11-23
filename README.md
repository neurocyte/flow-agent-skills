# Agent skills for Flow Control

This repository has the `drive-flow` skill. The skill teaches a coding agent
to drive a running [Flow Control](https://flow-control.dev) editor through
the `flow` remote client. With the skill, an agent can:

- open files and locations in your editor
- read the open buffers, cursors, diagnostics, terminals and the log
- edit files by path and save them
- run commands in a terminal panel and read their output

The agent connects only to a flow that you started. It never starts one.

## Install in Claude Code

The repository is a Claude Code plugin and its own marketplace (a git
repository that lists installable plugins). Run these two commands in Claude
Code:

```
/plugin marketplace add neurocyte/flow-agent-skills
/plugin install flow@flow
```

## Install in other agents

The skill uses the open Agent Skills format. Copy the `skills/drive-flow`
directory into the skills directory of your agent:

```
git clone https://github.com/neurocyte/flow-agent-skills
cp -r flow-agent-skills/skills/drive-flow <skills directory of your agent>/
```

## Connect the agent to flow

The skill handles three configurations:

1. The agent runs in a flow terminal panel. It connects with no setup.
2. You start flow with `flow --server NAME` and tell the agent the name.
3. The agent finds the running instances with `flow --list-servers`. It uses
   the instance whose current project contains its working directory. If no
   instance or more than one does, it asks you.

For a flow on another machine, or an agent in a Docker container, forward
the flow socket and give the agent the local socket path.
`skills/drive-flow/reference/connecting.md` gives the forward commands and
their limits.

## Versions

The `master` branch of this repository supports flow `v0.7.2-2149` and
later. The agent checks the version of the `flow` client and of the flow
that it drives before it sends other commands. If a version is too old, the
agent stops and tells you.

Each flow release gets a tag with the same name in this repository. To use
the skill with an older flow release, add the marketplace at that tag:

```
/plugin marketplace add neurocyte/flow-agent-skills#v0.8.0
```

For other agents, clone the tag with `git clone --branch v0.8.0`.

## License

MIT, the same as flow.
