import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Anti wildcards in Verilog and SystemVerilog files. Up to 99.9% efficiency."
    )

    parser.add_argument(
        "path",
        type=str,
        help="File to analyze and search for wildcards instantiations.",
    )

    parser.add_argument(
        "root",
        type=str,
        help="Root of the RTL project with all needed submodules.",
    )

    parser.add_argument(
        "--order",
        action="store_true",
        help="Order the I/Os after fixing the wildcards.",
    )

    return parser
