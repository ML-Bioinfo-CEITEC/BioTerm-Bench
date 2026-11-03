#!/usr/bin/env python3
"""Scaffolding shared by the v1.0 hard-candidate generators.

Two deliberate differences from the older task generators:

1. **The answer key is not mounted.** Older tasks bind ``../gold:/gold:ro`` into
   the *same* container the agent works in, so a curious agent can read the
   expected output. Harbor uploads ``tests/`` only inside ``verify()``, after the
   agent has finished, so embedding the expected answer in ``check.py`` closes
   that hole. (In the existing runs the hole was never exploited -- 1 of 400
   trajectories so much as mentions ``/gold``, and that trial scored 0 -- but
   harder tasks give a stuck model more reason to go looking.)

2. **Comparison is structural, not textual.** ``check.py`` parses both sides into
   rows and compares field by field, with a numeric tolerance where the contract
   allows rounding, so a trailing newline or column padding is never the thing
   that fails a run.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

TASKS = Path(__file__).resolve().parent.parent / "tasks"

DOCKERFILE = "FROM bioterm-base:v1\nRUN mkdir -p /app/output\n"

# No ../gold mount: the expected answer lives in tests/check.py, which the agent
# never sees.
COMPOSE = "services:\n  main:\n    volumes:\n      - ../data:/app/data:ro\n"

TEST_SH = """#!/usr/bin/env bash
set -euo pipefail

mkdir -p /logs/verifier

if python3 /tests/check.py; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
"""

TASK_TOML = """version = "1.0"

[metadata]
author_name  = "Petr Simecek"
author_email = "simecek@mail.muni.cz"
difficulty   = "hard"
category     = "{category}"
tags         = [{tags}]

[verifier]
timeout_sec = 120.0

[agent]
timeout_sec = 1200.0

[environment]
build_timeout_sec = 600.0
docker_image      = "bioterm-base:v1"
cpus              = 2
memory            = "4G"
storage           = "5G"
"""

CHECK_HEADER = '''#!/usr/bin/env python3
"""Grader for {name}.

The expected answer is embedded here rather than mounted from ../gold: Harbor
uploads tests/ only at verification time, so nothing in this file is visible to
the agent while it works.
"""
from __future__ import annotations

import sys
from pathlib import Path

OUT = Path("{outfile}")

EXPECTED = """\\
{expected}"""


def fail(msg: str) -> None:
    print(f"FAIL: {{msg}}", file=sys.stderr)
    sys.exit(1)


def rows(text: str) -> list[list[str]]:
    out = []
    for line in text.replace("\\r\\n", "\\n").split("\\n"):
        if not line.strip():
            continue
        out.append(line.rstrip("\\n").split("\\t"))
    return out


def main() -> None:
    if not OUT.is_file():
        fail(f"missing {{OUT}}")
    got = rows(OUT.read_text())
    want = rows(EXPECTED)
    if not got:
        fail("output is empty")
    if got[0] != want[0]:
        fail(f"header must be {{want[0]}}; got {{got[0]}}")
    if len(got) != len(want):
        fail(f"expected {{len(want) - 1}} data rows, got {{len(got) - 1}}")
    ncol = len(want[0])
    for i, (g, w) in enumerate(zip(got[1:], want[1:]), start=2):
        if len(g) != ncol:
            fail(f"line {{i}}: expected {{ncol}} tab-separated columns, got {{len(g)}}")
        for j, (gv, wv) in enumerate(zip(g, w)):
            col = want[0][j]
            try:
                wf = float(wv)
            except ValueError:
                if gv != wv:
                    fail(f"line {{i}} column {{col}}: actual={{gv}} gold={{wv}}")
                continue
            try:
                gf = float(gv)
            except ValueError:
                fail(f"line {{i}} column {{col}}: actual={{gv}} is not numeric, gold={{wv}}")
            if abs(gf - wf) > max({tol}, {rtol} * abs(wf)):
                fail(f"line {{i}} column {{col}}: actual={{gv}} gold={{wv}}")
    print("ok")


main()
'''


MAX_INSTRUCTION_WORDS = 199


def write_task(
    name: str,
    category: str,
    tags: list[str],
    instruction: str,
    expected: str,
    solve: str,
    outfile: str,
    tol: float = 1e-6,
    rtol: float = 0.0,
) -> Path:
    """Materialise one candidate task directory."""
    words = len(instruction.split())
    if words >= MAX_INSTRUCTION_WORDS:
        raise SystemExit(
            f"{name}: instruction is {words} words, limit {MAX_INSTRUCTION_WORDS - 1}"
        )

    d = TASKS / name
    for sub in ("data", "environment", "solution", "tests", "gold"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    (d / "environment" / "Dockerfile").write_text(DOCKERFILE)
    (d / "environment" / "docker-compose.yaml").write_text(COMPOSE)
    (d / "tests" / "test.sh").write_text(TEST_SH)
    (d / "task.toml").write_text(
        TASK_TOML.format(category=category, tags=", ".join(f'"{t}"' for t in tags))
    )
    (d / "instruction.md").write_text(textwrap.dedent(instruction).strip() + "\n")
    (d / "tests" / "check.py").write_text(
        CHECK_HEADER.format(
            name=name,
            outfile=outfile,
            expected=expected.replace("\\", "\\\\").replace('"""', '\\"\\"\\"'),
            tol=tol,
            rtol=rtol,
        )
    )
    # The gold file exists on disk so a human can audit the key and the
    # generator can be re-run against it. It is deliberately NOT mounted by
    # environment/docker-compose.yaml, so the agent cannot read it; the grader
    # carries its own embedded copy.
    (d / "gold" / Path(outfile).name).write_text(expected)
    (d / "solution" / "solve.sh").write_text(solve)
    (d / "solution" / "solve.sh").chmod(0o755)
    (d / "tests" / "test.sh").chmod(0o755)
    return d


# The multi-file grader is assembled by concatenation rather than str.format:
# the expected answers go in as repr(), which escapes quotes, backslashes and
# newlines correctly by construction. An earlier .format-based version with
# triple-quoted payloads emitted a check.py with an unterminated string.
MULTI_CHECK_PREAMBLE = '''#!/usr/bin/env python3
# Grader for {name}.
#
# This task has several deliverables and every one of them must be right.
# The expected answers are embedded here rather than mounted from ../gold:
# Harbor uploads tests/ only at verification time, so nothing in this file is
# visible to the agent while it works.
from __future__ import annotations

import sys
from pathlib import Path

'''

MULTI_CHECK_BODY = r'''

def fail(msg: str) -> None:
    print("FAIL: " + msg, file=sys.stderr)
    sys.exit(1)


def rows(text: str) -> list[list[str]]:
    out = []
    for line in text.replace("\r\n", "\n").split("\n"):
        if not line.strip():
            continue
        out.append(line.split("\t"))
    return out


def check(path: str, expected: str) -> None:
    p = Path(path)
    if not p.is_file():
        fail("missing " + path)
    got, want = rows(p.read_text()), rows(expected)
    if not got:
        fail(path + ": output is empty")
    if got[0] != want[0]:
        fail(path + ": header must be " + str(want[0]) + "; got " + str(got[0]))
    if len(got) != len(want):
        fail(path + ": expected " + str(len(want) - 1) + " data rows, got "
             + str(len(got) - 1))
    ncol = len(want[0])
    for i, (g, w) in enumerate(zip(got[1:], want[1:]), start=2):
        where = path + " line " + str(i)
        if len(g) != ncol:
            fail(where + ": expected " + str(ncol) + " columns, got " + str(len(g)))
        for gv, wv, col in zip(g, w, want[0]):
            try:
                wf = float(wv)
            except ValueError:
                if gv != wv:
                    fail(where + " column " + col + ": actual=" + gv + " gold=" + wv)
                continue
            try:
                gf = float(gv)
            except ValueError:
                fail(where + " column " + col + ": actual=" + gv + " is not numeric")
            if abs(gf - wf) > TOL:
                fail(where + " column " + col + ": actual=" + gv + " gold=" + wv)


for _path, _expected in EXPECTED.items():
    check(_path, _expected)
print("ok")
'''


def write_multi_task(
    name: str,
    category: str,
    tags: list[str],
    instruction: str,
    outputs: dict[str, str],
    solve: str,
    tol: float = 1e-6,
) -> Path:
    """Materialise a candidate whose contract spans several output files."""
    words = len(instruction.split())
    if words >= MAX_INSTRUCTION_WORDS:
        raise SystemExit(
            f"{name}: instruction is {words} words, limit {MAX_INSTRUCTION_WORDS - 1}"
        )

    d = TASKS / name
    for sub in ("data", "environment", "solution", "tests", "gold"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    (d / "environment" / "Dockerfile").write_text(DOCKERFILE)
    (d / "environment" / "docker-compose.yaml").write_text(COMPOSE)
    (d / "tests" / "test.sh").write_text(TEST_SH)
    (d / "tests" / "test.sh").chmod(0o755)
    (d / "task.toml").write_text(
        TASK_TOML.format(category=category, tags=", ".join(f'"{t}"' for t in tags))
    )
    (d / "instruction.md").write_text(textwrap.dedent(instruction).strip() + "\n")

    body = MULTI_CHECK_PREAMBLE.format(name=name)
    body += "EXPECTED = {\n"
    for path, text in outputs.items():
        body += f"    {path!r}: {text!r},\n"
    body += "}\n\nTOL = " + repr(float(tol)) + "\n"
    body += MULTI_CHECK_BODY
    (d / "tests" / "check.py").write_text(body)

    for path, text in outputs.items():
        (d / "gold" / Path(path).name).write_text(text)
    (d / "solution" / "solve.sh").write_text(solve)
    (d / "solution" / "solve.sh").chmod(0o755)
    return d
