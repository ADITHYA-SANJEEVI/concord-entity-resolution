"""Minimal C4 benchmark surface; existing C1-C3 verbs retain their semantics."""


def add_parsers(verbs):
    actions = verbs.add_parser("benchmark").add_subparsers(dest="action", required=True)
    for action in ("public", "scale"):
        parser = actions.add_parser(action)
        parser.add_argument("--output", required=True)
        parser.add_argument("--population", required=True)
        parser.add_argument("--run-id", required=True)
        parser.add_argument("--track", choices=("SYNTHETIC_PUBLIC",), required=True)
        if action == "scale":
            parser.add_argument("--model-run", required=True)
            parser.add_argument("--sizes", default="128,512,2048")
            parser.add_argument("--repetitions", type=int, default=3)
            parser.add_argument("--warmups", type=int, default=1)


def command(args):
    if args.action == "public":
        from concord.research.experiments import run_suite

        return run_suite(args)
    from concord.research.scale import run_scale

    return run_scale(args)
