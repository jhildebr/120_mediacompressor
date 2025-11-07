"""Video encoding configuration profiles."""

import os
from typing import Dict, Any


# Default encoding profile for standard compression
DEFAULT_VIDEO_CONFIG = {
    # Quality settings
    "preset": "veryfast",  # FFmpeg preset: ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow
    "target_bitrate": "800k",  # Target video bitrate
    "max_bitrate": "1200k",  # Maximum bitrate for VBR
    "buffer_size": "2400k",  # Buffer size (2x max_bitrate recommended)

    # Resolution settings
    "max_width": 1280,
    "max_height": 720,

    # Smart encoding optimization
    "skip_reencoding_if_optimal": True,  # Skip re-encoding if already H.264, ≤720p, ≤1.5 Mbps
    "optimal_bitrate_threshold": 1500000,  # 1.5 Mbps - skip re-encoding if below this

    # Processing limits
    "max_processing_time": int(os.getenv("MAX_PROCESSING_TIME", "300")),  # 5 minutes default

    # Audio handling
    "remove_audio": True,  # Remove audio track

    # Streaming optimization
    "enable_faststart": True,  # Enable streaming (moov atom at beginning)
}


# High quality profile (slower, better quality)
HIGH_QUALITY_CONFIG = {
    **DEFAULT_VIDEO_CONFIG,
    "preset": "slow",
    "target_bitrate": "1200k",
    "max_bitrate": "2000k",
    "buffer_size": "4000k",
}


# Fast profile (faster processing, lower quality)
FAST_CONFIG = {
    **DEFAULT_VIDEO_CONFIG,
    "preset": "ultrafast",
    "target_bitrate": "600k",
    "max_bitrate": "900k",
    "buffer_size": "1800k",
    "skip_reencoding_if_optimal": True,
}


# High resolution profile (for 1080p content)
HD_CONFIG = {
    **DEFAULT_VIDEO_CONFIG,
    "max_width": 1920,
    "max_height": 1080,
    "target_bitrate": "1500k",
    "max_bitrate": "2500k",
    "buffer_size": "5000k",
    "preset": "fast",
}


def get_video_config(profile: str = "default", **overrides: Any) -> Dict[str, Any]:
    """Get video encoding configuration with optional overrides.

    Args:
        profile: Configuration profile name (default, high_quality, fast, hd)
        **overrides: Override specific config values

    Returns:
        Configuration dictionary

    Examples:
        # Use default profile
        config = get_video_config()

        # Use fast profile
        config = get_video_config("fast")

        # Use default with custom bitrate
        config = get_video_config(target_bitrate="1000k")

        # Use high quality with custom preset
        config = get_video_config("high_quality", preset="medium")
    """
    profiles = {
        "default": DEFAULT_VIDEO_CONFIG,
        "high_quality": HIGH_QUALITY_CONFIG,
        "fast": FAST_CONFIG,
        "hd": HD_CONFIG,
    }

    base_config = profiles.get(profile, DEFAULT_VIDEO_CONFIG).copy()
    base_config.update(overrides)

    return base_config
