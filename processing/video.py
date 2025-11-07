import json
import logging
import os
import subprocess
import tempfile
import time
from typing import Dict, Optional

from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceExistsError
from processing import generate_processed_blob_sas_url
from processing.config import get_video_config


def _get_video_info(input_path: str) -> Optional[Dict]:
    """Get video metadata using ffprobe.

    Returns:
        Dict with codec_name, width, height, bit_rate, or None if failed
    """
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=codec_name,width,height,bit_rate",
            "-of", "json",
            input_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

        if result.returncode != 0:
            logging.warning("ffprobe failed: %s", result.stderr)
            return None

        data = json.loads(result.stdout)
        if not data.get("streams"):
            return None

        return data["streams"][0]
    except Exception as exc:
        logging.warning("Failed to get video info: %s", str(exc))
        return None


def _should_skip_reencoding(input_path: str, config: Dict) -> bool:
    """Check if video is already optimal and can skip re-encoding.

    A video is optimal if:
    - Already H.264 codec
    - Resolution ≤ target max resolution
    - Bitrate ≤ optimal threshold

    Args:
        input_path: Path to input video
        config: Encoding configuration

    Returns:
        True if re-encoding can be skipped
    """
    if not config.get("skip_reencoding_if_optimal", False):
        return False

    video_info = _get_video_info(input_path)
    if not video_info:
        # If we can't get info, better to re-encode to be safe
        return False

    try:
        is_h264 = video_info.get("codec_name") == "h264"
        width = int(video_info.get("width", 9999))
        height = int(video_info.get("height", 9999))
        bitrate = int(video_info.get("bit_rate", 9999999))

        max_width = config.get("max_width", 1280)
        max_height = config.get("max_height", 720)
        bitrate_threshold = config.get("optimal_bitrate_threshold", 1500000)

        is_resolution_ok = width <= max_width and height <= max_height
        is_bitrate_ok = bitrate <= bitrate_threshold

        should_skip = is_h264 and is_resolution_ok and is_bitrate_ok

        if should_skip:
            logging.info(
                "Video is already optimal (H.264, %dx%d, %d kbps) - skipping re-encoding",
                width, height, bitrate // 1000
            )
        else:
            logging.info(
                "Video needs re-encoding: codec=%s, %dx%d, %d kbps",
                video_info.get("codec_name"), width, height, bitrate // 1000
            )

        return should_skip

    except (ValueError, TypeError) as exc:
        logging.warning("Error checking video optimization: %s", str(exc))
        return False


def _build_ffmpeg_cmd(input_path: str, output_path: str, config: Dict, skip_reencoding: bool = False) -> list[str]:
    """Build FFmpeg command for VBR H.264 compression (web-compatible MP4).

    Args:
        input_path: Input video file path
        output_path: Output video file path
        config: Encoding configuration from get_video_config()
        skip_reencoding: If True, use stream copy (fast, no re-encoding)

    Returns:
        FFmpeg command as list of strings
    """
    cmd: list[str] = [
        "ffmpeg",
        "-i",
        input_path,
    ]

    if skip_reencoding:
        # Stream copy - no re-encoding, just remux and apply faststart
        logging.info("Using stream copy (no re-encoding)")
        cmd.extend([
            "-c:v", "copy",  # Copy video stream without re-encoding
        ])
    else:
        # Full re-encoding with configured parameters
        max_width = config.get("max_width", 1280)
        max_height = config.get("max_height", 720)

        cmd.extend([
            "-c:v", "libx264",  # H.264 codec (web-compatible)
            "-b:v", config.get("target_bitrate", "800k"),
            "-maxrate", config.get("max_bitrate", "1200k"),
            "-bufsize", config.get("buffer_size", "2400k"),
            "-preset", config.get("preset", "veryfast"),
            "-vf",
            # Scale to max resolution, ensure dimensions divisible by 2 (H.264 requirement)
            f"scale='min({max_width},iw)':'min({max_height},ih)':force_original_aspect_ratio=decrease,scale=trunc(iw/2)*2:trunc(ih/2)*2",
        ])

    # Audio handling
    if config.get("remove_audio", True):
        cmd.extend(["-an"])  # Remove audio

    # Streaming optimization
    if config.get("enable_faststart", True):
        cmd.extend(["-movflags", "+faststart"])

    # Overwrite output
    cmd.extend(["-y", output_path])

    return cmd


def process_video(blob_name: str, job: Dict) -> Dict:
    """Process video compression with FFmpeg and upload to 'processed' container.

    Args:
        blob_name: Name of blob in uploads container
        job: Job metadata dict, can include:
            - encoding_profile: Profile name (default, fast, high_quality, hd)
            - encoding_config: Dict of config overrides (preset, target_bitrate, etc.)

    Returns:
        Processing result dict with status, sizes, compression ratio, etc.
    """
    logging.info("=== VIDEO PROCESSING STARTED for %s ===", blob_name)
    start_time = time.time()

    # Load encoding configuration
    profile = job.get("encoding_profile", "default")
    config_overrides = job.get("encoding_config", {})
    config = get_video_config(profile, **config_overrides)

    logging.info("Using encoding profile: %s (preset=%s, bitrate=%s)",
                 profile, config.get("preset"), config.get("target_bitrate"))

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
            # Check if we can skip re-encoding
            skip_reencoding = _should_skip_reencoding(temp_input.name, config)

            # Build FFmpeg command
            cmd = _build_ffmpeg_cmd(temp_input.name, output_path, config, skip_reencoding)

            if skip_reencoding:
                logging.info("Running FFmpeg stream copy (fast): %s", " ".join(cmd))
            else:
                logging.info("Running FFmpeg H.264 compression: %s", " ".join(cmd))

            # Execute FFmpeg
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=config.get("max_processing_time", 300)
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
            processing_time = time.time() - start_time

            logging.info("Original size: %s, Compressed size: %s, Ratio: %s",
                        original_size, compressed_size, compression_ratio)

            result_dict = {
                "status": "success",
                "original_size": original_size,
                "compressed_size": compressed_size,
                "compression_ratio": compression_ratio,
                # Provide SAS URL for secure, time-limited access
                "output_url": generate_processed_blob_sas_url(output_blob_name),
                "processing_time": processing_time,
                # Encoding metadata
                "encoding_profile": profile,
                "encoding_preset": config.get("preset"),
                "target_bitrate": config.get("target_bitrate"),
                "skipped_reencoding": skip_reencoding,
            }

            logging.info("=== VIDEO PROCESSING COMPLETED SUCCESSFULLY for %s ===", blob_name)
            logging.info("Processing time: %.2fs (skipped_reencoding=%s)", processing_time, skip_reencoding)
            logging.info("Result: %s", result_dict)
            return result_dict

        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)


