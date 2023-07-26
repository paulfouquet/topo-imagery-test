import os
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial
from multiprocessing import Pool
from typing import List

import ulid
from linz_logger import get_log

from scripts.cli.cli_helper import TileFiles
from scripts.files.file_tiff import FileTiff
from scripts.files.fs import exists, read, write
from scripts.gdal.gdal_helper import get_gdal_version, run_gdal
from scripts.gdal.gdal_preset import get_build_vrt_command
from scripts.logging.time_helper import time_in_ms

# import tqdm


def run_standardising(
    todo: List[TileFiles],
    preset: str,
    concurrency: int,
    target_output: str = "/tmp/",
) -> List[FileTiff]:
    """Run `standardising()` in parallel (`concurrency`).

    Args:
        todo: list of TileFiles (tile name and input files) to standardise
        preset: gdal preset to use. See `gdal.gdal_preset.py`
        cutline: path to the cutline. Must be `.fgb` or `.geojson`
        concurrency: number of concurrent files to process
        source_epsg: EPSG code of the source file
        target_epsg: EPSG code of reprojection
        target_output: output directory path. Defaults to "/tmp/"

    Returns:
        a list of FileTiff wrapper
    """
    # pylint: disable-msg=too-many-arguments
    start_time = time_in_ms()

    gdal_version = get_gdal_version()
    get_log().info("standardising_start", gdalVersion=gdal_version, fileCount=len(todo))

    with Pool(concurrency) as p:
        standardized_tiffs = p.map(
            partial(
                standardising,
                preset=preset,
                target_output=target_output,
            ),
            todo,
        )
        p.close()
        p.join()

    get_log().info("standardising_end", duration=time_in_ms() - start_time, fileCount=len(standardized_tiffs))

    return standardized_tiffs


def download_tiffs(files: List[str], target: str) -> List[str]:
    """Download a tiff file and some of its sidecar files if they exist to the target dir.

    Args:
        files: links source filename to target tilename
        target: target folder to write too

    Returns:
        linked downloaded filename to target tilename

    Example:
    ```
    >>> download_tiff_file(("s3://elevation/SN9457_CE16_10k_0502.tif", "CE16_5000_1003"), "/tmp/")
    ("/tmp/123456.tif", "CE16_5000_1003")
    ```
    """
    downloaded_files: List[str] = []
    for file in files:
        target_file_path = os.path.join(target, str(ulid.ULID()))
        input_file_path = target_file_path + ".tiff"
        get_log().info("download_tiff", path=file, target_path=input_file_path)

        write(input_file_path, read(file))
        downloaded_files.append(input_file_path)

        base_file_path = os.path.splitext(file)[0]
        # Attempt to download sidecar files too
        for ext in [".prj", ".tfw"]:
            try:
                write(target_file_path + ext, read(base_file_path + ext))
                get_log().info("download_tiff_sidecar", path=base_file_path + ext, target_path=target_file_path + ext)

            except:  # pylint: disable-msg=bare-except
                pass

    return downloaded_files


def download_one_file(destination: str, s3_file: str) -> None:
    """
    Download a single file from S3
    Args:
        bucket (str): S3 bucket where images are hosted
        output (str): Dir to store the images
        client (boto3.client): S3 client
        s3_file (str): S3 object name
    """
    get_log().debug("download_file", path=s3_file)
    write(os.path.join(destination, f"{str(ulid.ULID())}.tiff"), read(os.path.join(s3_file)))
    # client.download_file(Bucket=bucket, Key=s3_file, Filename=os.path.join(destination, f"{str(ulid.ULID())}.tiff"))


def downloads_multithread_tiffs(inputs: List[str], destination: str, concurrency: int = 10) -> None:
    # Creating only one session and one client
    # The client is shared between threads
    func = partial(download_one_file, destination)

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        # Using a dict for preserving the downloaded file for each future, to store it as a failure if we need that
        futures = {executor.submit(func, input): input for input in inputs}
        for future in as_completed(futures):
            # TODO: add returned dowload to list.
            if future.exception():
                print(future.exception())
                get_log().info("Failed Download", error=future.exception())


def create_vrt(source_tiffs: List[str], target_path: str, add_alpha: bool = False) -> str:
    """Create a VRT from a list of tiffs files

    Args:
        source_tiffs: list of tiffs to create the VRT from
        target_path: path of the generated VRT
        add_alpha: add alpha band to the VRT. Defaults to False.

    Returns:
        the path to the VRT created
    """
    # Create the `vrt` file
    vrt_path = os.path.join(target_path, "source.vrt")
    run_gdal(command=get_build_vrt_command(files=source_tiffs, output=vrt_path, add_alpha=add_alpha))
    return vrt_path


# pylint: disable-msg=too-many-locals
def standardising(
    files: TileFiles,
    preset: str,
    target_output: str = "/tmp/",
) -> FileTiff:
    """Apply transformations using GDAL to the source file.

    Args:
        file: path to the file to standardise
        preset: gdal preset to use. See `gdal.gdal_preset.py`
        source_epsg: EPSG code of the source file
        target_epsg: EPSG code of reprojection
        cutline: path to the cutline. Must be `.fgb` or `.geojson`
        target_output: output directory path. Defaults to "/tmp/"

    Raises:
        Exception: if cutline is not a .fgb or .geojson file

    Returns:
        a FileTiff wrapper
    """
    standardized_file_name = files.output + ".tiff"
    standardized_file_path = os.path.join(target_output, standardized_file_name)
    tiff = FileTiff(files.input, preset)
    tiff.set_path_standardised(standardized_file_path)

    # Already proccessed can skip processing
    if exists(standardized_file_path):
        get_log().info("standardised_tiff_already_exists", path=standardized_file_path)
        return tiff

    tmp_path = tempfile.mkdtemp()

    downloads_multithread_tiffs(files.input, tmp_path)

    return tiff
