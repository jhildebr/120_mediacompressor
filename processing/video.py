import logging
import os
import subprocess
import tempfile
import time
from typing import Dict

from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceExistsError
from processing import generate_processed_blob_sas_url


def _build_ffmpeg_cmd(input_path: str, output_path: str, job: Dict) -> list[str]:
    cmd: list[str] = [
        "ffmpeg",
        "-i",
        input_path,
        "-c:v",
        "libx264",
        "-crf",
        "23",
        "-preset",
        # Use ultrafast to minimize CPU time; adjust CRF to keep quality reasonable
        "ultrafast",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        "-y",
        output_path,
    ]

    try:
        file_size: int = int(job.get("file_size", 0))
    except Exception:  # pragma: no cover - defensive
        file_size = 0

    if file_size > 50 * 1024 * 1024:
        cmd.extend(["-vf", "scale=1280:720"])  # HD
    elif file_size > 10 * 1024 * 1024:
        cmd.extend(["-vf", "scale=854:480"])  # SD

    return cmd


def process_video(blob_name: str, job: Dict) -> Dict:
    """Process video compression with FFmpeg and upload to 'processed' container."""
    logging.info("=== VIDEO PROCESSING STARTED for %s ===", blob_name)
    start_time = time.time()

    blob_service = BlobServiceClient.from_connection_string(
        os.environ["AzureWebJobsStorage"]
    )

    # Download original file
    logging.info("Downloading original file from uploads container: %s", blob_name)
    uploads_client = blob_service.get_blob_client(container="uploads", blob=blob_name)

    with tempfile.NamedTemporaryFile(suffix=".mp4") as temp_input:
        logging.info("Writing downloaded file to temp file (streaming): %s", temp_input.name)
        downloader = uploads_client.download_blob(max_concurrency=4)
        downloader.readinto(temp_input)
        temp_input.flush()
        logging.info("Downloaded file size: %s bytes", os.path.getsize(temp_input.name))

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_output:
            output_path = temp_output.name
            logging.info("Created output temp file: %s", output_path)

        try:
            # 1) Fast path: container rewrite only (stream copy) if source is already compatible
            # This is near-instantaneous for small files.
            fast_cmd = [
                "ffmpeg",
                "-i",
                temp_input.name,
                "-c:v",
                "copy",
                "-c:a",
                "copy",
                "-movflags",
                "+faststart",
                "-y",
                output_path,
            ]
            logging.info("Attempting fast stream-copy: %s", " ".join(fast_cmd))
            fast = subprocess.run(
                fast_cmd, capture_output=True, text=True, timeout=int(os.getenv("MAX_PROCESSING_TIME", "300"))
            )
            if fast.returncode != 0:
                logging.info("Fast path failed, falling back to re-encode. stderr: %s", fast.stderr)
                # 2) Fallback: re-encode with ultrafast preset
                cmd = _build_ffmpeg_cmd(temp_input.name, output_path, job)
                logging.info("Running FFmpeg re-encode: %s", " ".join(cmd))
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=int(os.getenv("MAX_PROCESSING_TIME", "300"))
                )
                logging.info("FFmpeg return code: %s", result.returncode)
                logging.info("FFmpeg stdout: %s", result.stdout)
                logging.info("FFmpeg stderr: %s", result.stderr)
                if result.returncode != 0:
                    raise RuntimeError(f"FFmpeg failed: {result.stderr}")

            # Upload compressed video with 'processed-' prefix in 'processed' container
            output_blob_name = blob_name.replace('upload-', 'processed-')
            logging.info("Uploading compressed video to processed container: %s", output_blob_name)
            # Ensure 'processed' container exists
            try:
                blob_service.get_container_client("processed").create_container()
            except ResourceExistsError:
                pass
            with open(output_path, "rb") as compressed_file:
                blob_service.get_blob_client(
                    container="processed", blob=output_blob_name
                ).upload_blob(compressed_file, overwrite=True, max_concurrency=4)

            original_size = int(job.get("file_size", 1)) or 1
            compressed_size = os.path.getsize(output_path)
            compression_ratio = compressed_size / float(original_size)
            
            logging.info("Original size: %s, Compressed size: %s, Ratio: %s", 
                        original_size, compressed_size, compression_ratio)

            result_dict = {
                "status": "success",
                "original_size": original_size,
                "compressed_size": compressed_size,
                "compression_ratio": compression_ratio,
                # Provide SAS URL for secure, time-limited access
                "output_url": generate_processed_blob_sas_url(output_blob_name),
                "processing_time": time.time() - start_time,
            }
            
            logging.info("=== VIDEO PROCESSING COMPLETED SUCCESSFULLY for %s ===", blob_name)
            logging.info("Result: %s", result_dict)
            return result_dict

        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)


