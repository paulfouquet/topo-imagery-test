import argparse
import json
import os

import shapely.geometry
from boto3 import client
from linz_logger import get_log

from scripts.files.files_helper import SUFFIX_FOOTPRINT, ContentType
from scripts.files.fs import write
from scripts.files.fs_s3 import bucket_name_from_path, get_object_parallel_multithreading, list_files_in_uri
from scripts.logging.time_helper import time_in_ms
from scripts.stac.imagery.capture_aera import generate_capture_area
from scripts.stac.imagery.collection import CAPTURE_AREA_FILE_NAME


def main() -> None:
    start_time = time_in_ms()
    get_log().info("create_footprints_start")
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source", dest="source", required=True, help="The path to the footprints"
    )
    parser.add_argument("--target", dest="target", required=True, help="The path to save the capture-area.")
    parser.add_argument("--gsd", dest="gsd", required=True, help="The dataset gsd.")
    arguments = parser.parse_args()
    source = arguments.source

    concurrency = 25
     # Load polygons from local footprint files
    s3_client = client("s3")
    files_to_read = list_files_in_uri(source, [SUFFIX_FOOTPRINT], s3_client)
    polygons = []
    for key, result in get_object_parallel_multithreading(
        bucket_name_from_path(source), files_to_read, s3_client, concurrency
    ):
        content = json.load(result["Body"])
        if key.endswith(SUFFIX_FOOTPRINT):
            get_log().debug(f"adding geometry from {key}")
            if len(content["features"]) > 0:
                polygons.append(shapely.geometry.shape(content["features"][0]["geometry"]))

    capture_area_content = generate_capture_area(polygons, float(arguments.gsd.replace("m", "")))
    capture_area_target = os.path.join(arguments.target, CAPTURE_AREA_FILE_NAME)
    write(
            capture_area_target,
            json.dumps(capture_area_content).encode("utf-8"),
            content_type=ContentType.GEOJSON.value,
        )
       
    
    get_log().info("create_capture_area_end", duration=time_in_ms() - start_time)


if __name__ == "__main__":
    main()
