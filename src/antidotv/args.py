import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=f"Anti stars in SystemVerilog files. Up to 99.9% efficiency."
    )

    parser.add_argument(
        "path",
        type=str,
        help="File to analyze and search for stars in.",
    )

    parser.add_argument(
        "root",
        type=str,
        help="Root of the SystemVerilog project.",
    )

    return parser
