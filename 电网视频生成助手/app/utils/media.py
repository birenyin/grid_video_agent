from __future__ import annotations

from pathlib import Path

import imageio.v2 as imageio


def extract_first_frame(video_path: Path, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    reader = imageio.get_reader(video_path)
    try:
        frame = reader.get_data(0)
    finally:
        reader.close()
    imageio.imwrite(output_path, frame)
    return output_path
