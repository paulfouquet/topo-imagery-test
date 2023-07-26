import argparse
import json
import sys
from typing import List

from linz_logger import get_log

from scripts.cli.cli_helper import TileFiles, format_source, is_argo, valid_date
from scripts.files.fs import read
from scripts.standardising import run_standardising


def main() -> None:
    # pylint: disable-msg=too-many-locals
    parser = argparse.ArgumentParser()
    parser.add_argument("--preset", dest="preset", required=True, help="Standardised file format. Example: webp")
    parser.add_argument("--source", dest="source", nargs="+", required=False, help="The path to the input tiffs")
    parser.add_argument(
        "--from-file", dest="from_file", required=False, help="The path to a json file containing the input tiffs"
    )
    parser.add_argument("--source-epsg", dest="source_epsg", required=True, help="The EPSG code of the source imagery")
    parser.add_argument(
        "--target-epsg",
        dest="target_epsg",
        required=True,
        help="The target EPSG code. If different to source the imagery will be reprojected",
    )
    parser.add_argument("--cutline", dest="cutline", help="Optional cutline to cut imagery to", required=False, nargs="?")
    parser.add_argument("--collection-id", dest="collection_id", help="Unique id for collection", required=True)
    parser.add_argument(
        "--start-datetime", dest="start_datetime", help="Start datetime in format YYYY-MM-DD", type=valid_date, required=True
    )
    parser.add_argument(
        "--end-datetime", dest="end_datetime", help="End datetime in format YYYY-MM-DD", type=valid_date, required=True
    )
    parser.add_argument("--target", dest="target", help="Target output", required=True)
    arguments = parser.parse_args()

    source = arguments.source
    from_file = arguments.from_file

    if not source and not from_file:
        get_log().error("source_or_from_file_not_specified")
        sys.exit(1)

    if from_file:
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
