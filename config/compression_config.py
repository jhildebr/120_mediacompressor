VIDEO_COMPRESSION_SETTINGS = {
    # Unified settings - independent of source file size
    # Optimized for fast loading in step-by-step content
    "default": {
        "target_bitrate": "1200k",  # 1.2 Mbps target
        "max_bitrate": "2000k",     # 2 Mbps max
        "bufsize": "4000k",         # 2x maxrate for smooth VBR
        "preset": "fast",           # Faster encoding, minimal quality loss
        "max_resolution": "1280:720",  # Max 720p, aspect ratio preserved
    },
}

IMAGE_COMPRESSION_SETTINGS = {
    "jpeg": {"quality": 85, "optimize": True},
    "png": {"optimize": True, "compress_level": 6},
    "webp": {"quality": 85, "method": 6},
}


