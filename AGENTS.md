# Agent guide for the slapos repository

Read by AI coding assistants that follow the [agents.md](https://agents.md)
spec. Keep this file short: it holds only what an agent cannot read from the
code, and points to the plugins that hold the rest.

## Project overview

This repository is the [SlapOS](https://slapos.nexedi.com/) software release
list. `software/` is the core of the repository.

- `software/` — one directory per software release. A software release is a
  buildout profile that builds an application and deploys it into SlapOS
  partitions. Examples: ERP5, MariaDB, rapid-cdn.
- `stack/` — buildout stacks that several software releases share (monitor,
  resilient, haproxy, …).
- `component/` — build profiles for the libraries and tools that the stacks and
  the software releases compile.
- `slapos/recipe/` — **slapos.cookbook**, a Python package of 90+
  [zc.buildout](https://www.buildout.org/) recipes. The software releases use
  these recipes as tools. slapos.cookbook is not the product of this
  repository. The software release list is.
- `slapos/test/recipe/` — unit tests for the recipes.

## Install the agent plugins first

SlapOS development skills and the coding-rules knowledge base are not vendored
here. They live in the [slapos-agent-skill-marketplace](https://lab.nexedi.com/nexedi/slapos-agent-skill-marketplace)
marketplace, as [Agent Skills](https://agentskills.io) that any compatible
agent can load:

| Plugin | Use it for |
| --- | --- |
| `slapos-software-release` | add a component, template, parameter, service, promise, monitoring, logrotate or frontend to a software release |
| `slapos-build-deploy` | build a software release, request or destroy an instance, reprocess a partition |
| `slapos-diagnostics` | node status, build and instance logs, software release tests, test results |
| `slapos-coding-rules` | the harvested coding rules, plus a commit check hook |

Install with `/plugin marketplace add https://lab.nexedi.com/nexedi/slapos-agent-skill-marketplace.git`,
then `/plugin install <plugin>@slapos-agent-skill-marketplace`. The marketplace
`README.md` gives the manual path for other agents, and the machine-config
template that the build and deploy plugins need.

Do not re-derive a procedure that a plugin skill already documents. Load the
skill.

## Consult the coding rules before a substantive change

The `slapos-coding-rules` plugin collects conventions that only appear in merge
request review comments. Read the rules for the area you touch. Treat a
`promoted` or `accepted` rule as binding, and a `proposed` or `soft` rule as
advice. If a rule contradicts other documentation, report the conflict to the
user. Do not pick one silently.

## Tests

Two software releases in this repository run the tests. Read the `README.md` of
the one you need before you run a test. Each README gives the full session:
install the software release, request an instance, source the published
environment script, then run the test.

- `software/slapos-testing/README.md` — unit tests for the slapos eggs,
  slapos.cookbook included. The runner is nxdtest, driven by the `.nxdtest`
  file of each egg.
- `software/slapos-sr-testing/README.md` — integration tests for a software
  release, held in `software/<name>/test/`. The runner is python unittest.
  These tests deploy real instances.

On a machine that is already set up, the `slapos-diagnostics` plugin runs these
tests for you. Its `run-sr-test` skill starts an integration test in the
background with the environment sourced. Its `test-results` skill reads the
test results of a commit from the Nexedi ERP5 test result module.

## Code style

- Indent with 2 spaces. The `sts=2` vim modeline is standard.
- Target Python 3, but keep the code compatible with Python 2. Older files use
  `six`.
- Comments must be stateless. Describe what the code does, never what changed.
  Do not write "new API", "now uses X", "changed to Y" or "previously Z".

## Commit messages

- Format: `<module-or-area>: <summary starting with a lowercase verb>`. For
  example `instancenode: skip error() for missing partition`.
- Never credit an AI product or vendor anywhere in a commit. Do not name a
  vendor in the body, and do not add a vendor trailer or a "generated with"
  link. A commit describes the work, not the tools that produced it.
- If you want a trailer for AI assistance, use only the generic form:
  `Co-Authored-By: AI agent <ai-agent@noreply>`.

## Written English in published text

Commit messages, merge request descriptions and review comments follow
**ASD-STE100 Simplified Technical English**. ASD-STE100 is the controlled
English of the aerospace and defence industry. Terminal chat is exempt. You do
not need the specification. Apply these rules:

- One idea per sentence. Keep an instruction under 20 words.
- Use the active voice and a simple tense.
- Say what the change does, in words a non-native English reader understands on
  first read.
- Drop developer jargon: "wire format", "rescope", "indirection", "silent
  no-op", "drift", "happy path", "end-to-end", "exercises the X path".
- Cut adjectives and filler: "simply", "just", "actually", "essentially".
- Keep code identifiers, file paths, commit hashes and merge request numbers.
  They are precise.
- Repeat the noun. Do not write "it" or "this" when the subject can be unclear.

## Push safety

- Never push to a remote whose URL starts with `https://lab.nexedi.com/nexedi/`.
  That remote is read-only. Push to your personal fork.
- Always name both the remote and the branch: `git push <remote> <branch>`.
  Check the remote first with `git remote get-url <remote>`.
- Never reset a branch to another ref with `git checkout -B`, `git branch -f` or
  `git reset --hard`. Those commands drop the branch tracking configuration. To
  take in upstream changes, use `git rebase <remote>/master`.
