import logging
import os
import subprocess
import tempfile
import time
from typing import Dict

from azure.storage.blob import BlobServiceClient


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
        "medium",
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
    start_time = time.time()

    blob_service = BlobServiceClient.from_connection_string(
        os.environ["AzureWebJobsStorage"]
    )

    # Download original file
    uploads_client = blob_service.get_blob_client(container="uploads", blob=blob_name)

    with tempfile.NamedTemporaryFile(suffix=".mp4") as temp_input:
        temp_input.write(uploads_client.download_blob().readall())
        temp_input.flush()

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_output:
            output_path = temp_output.name

        try:
            cmd = _build_ffmpeg_cmd(temp_input.name, output_path, job)
            logging.info("Running FFmpeg: %s", " ".join(cmd))

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=int(os.getenv("MAX_PROCESSING_TIME", "300"))
            )

            if result.returncode != 0:
                raise RuntimeError(f"FFmpeg failed: {result.stderr}")

            # Upload compressed video (same name in 'processed' container)
            output_blob_name = blob_name
            with open(output_path, "rb") as compressed_file:
                blob_service.get_blob_client(
                    container="processed", blob=output_blob_name
                ).upload_blob(compressed_file, overwrite=True)

            original_size = int(job.get("file_size", 1)) or 1
            compressed_size = os.path.getsize(output_path)
            compression_ratio = compressed_size / float(original_size)

            return {
                "status": "success",
                "original_size": original_size,
                "compressed_size": compressed_size,
                "compression_ratio": compression_ratio,
                "output_url": f"https://{os.getenv('BLOB_ACCOUNT_NAME','mediablobazfct')}.blob.core.windows.net/processed/{output_blob_name}",
                "processing_time": time.time() - start_time,
            }

        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)


