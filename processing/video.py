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
    """Build FFmpeg command for VBR H.264 compression (web-compatible MP4)."""
    # H.264 with VBR encoding, no audio, max 1280x720
    # Optimized for fast loading: 720p @ 1.2 Mbps is ideal for instructional content
    cmd: list[str] = [
        "ffmpeg",
        "-i",
        input_path,
        "-c:v",
        "libx264",  # H.264 codec (web-compatible)
        "-b:v",
        "1200k",  # Target bitrate: 1.2 Mbps
        "-maxrate",
        "2000k",  # Max bitrate: 2 Mbps
        "-bufsize",
        "4000k",  # Buffer size (2x maxrate for smooth VBR)
        "-preset",
        "fast",  # Faster encoding, minimal quality loss
        "-vf",
        # Scale to max 1280x720, ensure dimensions divisible by 2 (H.264 requirement)
        "scale='min(1280,iw)':'min(720,ih)':force_original_aspect_ratio=decrease,scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-an",  # Remove audio
        "-movflags",
        "+faststart",  # Enable streaming
        "-y",
        output_path,
    ]

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
            # Convert to H.264 MP4 for fast compression
            cmd = _build_ffmpeg_cmd(temp_input.name, output_path, job)
            logging.info("Running FFmpeg H.264 compression: %s", " ".join(cmd))
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=int(os.getenv("MAX_PROCESSING_TIME", "300"))
            )
            logging.info("FFmpeg return code: %s", result.returncode)
            logging.info("FFmpeg stdout: %s", result.stdout)
            logging.info("FFmpeg stderr: %s", result.stderr)
            if result.returncode != 0:
                raise RuntimeError(f"FFmpeg failed: {result.stderr}")

            # Upload compressed video with 'processed-' prefix in 'processed' container
            # Always change extension to .mp4 since all videos are converted to H.264 MP4
            output_blob_name = blob_name.replace('upload-', 'processed-').rsplit('.', 1)[0] + '.mp4'
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


