import io
import os
import time
from typing import Dict

from PIL import Image
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceExistsError
from processing import generate_processed_blob_sas_url


def process_image(blob_name: str, job: Dict) -> Dict:
    """Process image compression and upload to 'processed' container."""
    start_time = time.time()

    blob_service = BlobServiceClient.from_connection_string(
        os.environ["AzureWebJobsStorage"]
    )

    original_blob = blob_service.get_blob_client(
        container="uploads", blob=blob_name
    ).download_blob()

    image_data = original_blob.readall()
    original_image = Image.open(io.BytesIO(image_data))

    file_extension = blob_name.lower().split(".")[-1]

    if file_extension in ["jpg", "jpeg"]:
        output_format = "JPEG"
        save_kwargs = {"quality": 85, "optimize": True}
    elif file_extension == "png":
        output_format = "PNG"
        save_kwargs = {"optimize": True}
    elif file_extension == "webp":
        output_format = "WebP"
        save_kwargs = {"quality": 85, "method": 6}
    else:
        output_format = "WebP"
        save_kwargs = {"quality": 85, "method": 6}
        blob_name = blob_name.rsplit(".", 1)[0] + ".webp"

    max_dimension = 2048
    if max(original_image.size) > max_dimension:
        original_image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

    output_buffer = io.BytesIO()
    original_image.save(output_buffer, format=output_format, **save_kwargs)
    compressed_data = output_buffer.getvalue()

    output_blob_name = blob_name.replace('upload-', 'processed-')
    # Ensure 'processed' container exists
    try:
        blob_service.get_container_client("processed").create_container()
    except ResourceExistsError:
        pass
    blob_service.get_blob_client(container="processed", blob=output_blob_name).upload_blob(
        compressed_data, overwrite=True
    )

    return {
        "status": "success",
        "original_size": len(image_data),
        "compressed_size": len(compressed_data),
        "compression_ratio": len(compressed_data) / float(len(image_data) or 1),
        # Provide SAS URL for secure, time-limited access
        "output_url": generate_processed_blob_sas_url(output_blob_name),
        "processing_time": time.time() - start_time,
        "format": output_format,
    }


