VIDEO_COMPRESSION_SETTINGS = {
    "small": {  # < 10MB
        "crf": "23",
        "preset": "medium",
        "max_resolution": None,
    },
    "medium": {  # 10MB - 50MB
        "crf": "25",
        "preset": "medium",
        "max_resolution": "854:480",
    },
    "large": {  # > 50MB
        "crf": "27",
        "preset": "fast",
        "max_resolution": "1280:720",
    },
}

IMAGE_COMPRESSION_SETTINGS = {
    "jpeg": {"quality": 85, "optimize": True},
    "png": {"optimize": True, "compress_level": 6},
    "webp": {"quality": 85, "method": 6},
}


