import argparse
import json
from typing import List

from scripts.cli.cli_helper import TileFiles, format_source, is_argo
from scripts.files.fs import read
from scripts.standardising import run_standardising


def main() -> None:
    # pylint: disable-msg=too-many-locals
    parser = argparse.ArgumentParser()
    parser.add_argument("--preset", dest="preset", required=True, help="Standardised file format. Example: webp")
    parser.add_argument("--target", dest="target", help="Target output", required=True)
    parser.add_argument(
        "--from-file", dest="from_file", required=False, help="The path to a json file containing the input tiffs"
    )
    arguments = parser.parse_args()

    # FIXME: `source` has to be a list to be parsed in `format_source()`
    source = [json.dumps(json.loads(read(arguments.from_file)))]

    tile_files: List[TileFiles] = format_source(source)
    concurrency: int = 1
    if is_argo():
        concurrency = 4

    run_standardising(
        tile_files,
        arguments.preset,
        concurrency,
        arguments.target,
    )


if __name__ == "__main__":
    main()
