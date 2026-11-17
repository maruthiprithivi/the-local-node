"""Command line entry point: ctxlayer list-backends | plan --dry-run | run."""
import argparse
import os
import sys

from . import adapters, plan, workload


def _color():
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty() or bool(os.environ.get("FORCE_COLOR"))


def cmd_list_backends(args):
    w = max(len(n) for n in adapters.REGISTRY) + 3
    g = max(len(x) for x in adapters.GROUPS) + 3
    print(f"{'backend':<{w}}{'group':<{g}}status")
    for b in adapters.REGISTRY.values():
        print(f"{b.name:<{w}}{b.group:<{g}}{adapters.STATUS_TEXT[b.status]}")


def cmd_plan(args):
    wl = workload.load(args.workload)
    be = adapters.get(args.backend)
    steps = plan.build(wl, be, args.entity)
    assert plan.check_read_back_rule(steps), "plan breaks the read back rule"
    mode = "dry run, nothing executes" if args.dry_run else "plan only"
    print(f"plan for {be.name} on {wl.name}, {mode}")
    sec = None
    for i, s in enumerate(steps, 1):
        if s.section != sec:
            sec = s.section
            print(f"\n{sec}")
        line = f"{'  >' if s.action == 'read_back' else '   '} step {i:<3}{s.text}"
        print(f"\033[32m{line}\033[0m" if s.action == "read_back" and _color() else line)
    print("\nmeasures")
    for key, text in plan.MEASURES:
        print(f"    {key:<15}{text}")
    print("\nnothing was executed")


def cmd_run(args):
    from .runner import run
    wl = workload.load(args.workload)
    be = adapters.get(args.backend)
    if be.status != adapters.READY:
        sys.exit(f"{be.name} is {adapters.STATUS_TEXT[be.status]}; it cannot run yet")
    run(wl, be, args.entity, args.out, getattr(args, "run_id", None))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ctxlayer", description="Context layer harness: join, move, leave, read back.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list-backends", help="list backend adapters and their status").set_defaults(fn=cmd_list_backends)
    for name, fn, hlp in (("plan", cmd_plan, "print the plan for a run without executing it"),
                          ("run", cmd_run, "execute the plan against a ready backend")):
        p = sub.add_parser(name, help=hlp)
        p.add_argument("--backend", required=True)
        p.add_argument("--workload", default=workload.DEFAULT_WORKLOAD)
        p.add_argument("--entity", "--person", dest="entity", help="only this entity ID (a person, agent, MCP server or skill)")
        if name == "plan":
            p.add_argument("--dry-run", action="store_true", help="print only, never execute (plan never executes)")
        else:
            p.add_argument("--out", default="runs", help="folder for raw outputs")
            p.add_argument("--run-id", default=None, help="run id; default is backend, UTC time, seed, git sha")
        p.set_defaults(fn=fn)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
