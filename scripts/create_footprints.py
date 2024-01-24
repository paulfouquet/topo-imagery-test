import argparse
import json
import os
import tempfile
from functools import partial
from multiprocessing import Pool

from linz_logger import get_log

from scripts.files.files_helper import SUFFIX_FOOTPRINT, get_file_name_from_path, is_tiff
from scripts.files.fs import exists, read, write
from scripts.gdal.gdal_helper import run_gdal
from scripts.logging.time_helper import time_in_ms


def create_footprint(source_tiff: str, tmp_path: str, target: str) -> str | None:
    if not is_tiff(source_tiff):
        get_log().debug("create_footprint_skip_not_tiff", file=source_tiff)
        return None

    basename = get_file_name_from_path(source_tiff)
    tmp_footprint = os.path.join(tmp_path, f"{basename}{SUFFIX_FOOTPRINT}")
    target_footprint = os.path.join(target, f"{basename}{SUFFIX_FOOTPRINT}")
    # Verify the footprint has not been already generated
    if exists(tmp_footprint):
        get_log().info("footprint_already_exists", path=tmp_footprint)
        return None
    local_tiff = os.path.join(tmp_path, f"{basename}.tiff")
    # Download source tiff
    write(local_tiff, read(source_tiff))

    # Generate footprint
    run_gdal(
                ["gdal_footprint", "-t_srs", "EPSG:4326"],
                local_tiff,
                tmp_footprint,
            )
    
    write(target_footprint, read(tmp_footprint))
    return target_footprint


def main() -> None:
    start_time = time_in_ms()
    get_log().info("create_footprints_start")
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--from-file", dest="from_file", required=True, help="The path to a json file containing the input tiffs"
    )
    parser.add_argument("--target", dest="target", required=True, help="The path to save the capture-area.")
    arguments = parser.parse_args()
    from_file = arguments.from_file
    source = json.loads(read(from_file))

    concurrency = 25
    footprint_list = []

    with tempfile.TemporaryDirectory() as tmp_path:
        for tiff_list in source:
            with Pool(concurrency) as p:
                footprint_list_current = p.map(
                    partial(
                        create_footprint,
                        tmp_path=tmp_path,
                        target=arguments.target,
                    ),
                    tiff_list,
                )
                p.close()
                p.join()
                footprint_list.extend(footprint_list_current)

       
    
    get_log().info("create_capture_area_end", duration=time_in_ms() - start_time)


if __name__ == "__main__":
    main()
