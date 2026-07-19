# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

`mapping_tool.py` is a single-file video-mapping (projection warping) simulator. It projects a
source (test pattern, image, video file, or webcam) through a perspective transform into a
quadrilateral whose 4 corners are dragged with the mouse — the same core calibration technique
used by MadMapper, Resolume, HeavyM, etc. Comments and CLI/user-facing strings are in French.

## Running

```bash
pip install opencv-python numpy   # not currently installed in this environment
python3 mapping_tool.py                        # generated test pattern
python3 mapping_tool.py --source video.mp4      # looping video file
python3 mapping_tool.py --source image.jpg      # static image
python3 mapping_tool.py --source 0              # webcam index 0
python3 mapping_tool.py --width 1920 --height 1080
```

There is no build step, test suite, or linter configured in this repo.

### In-app controls

- Drag a corner handle (circle) with left click to move it
- `g` toggle warping grid overlay, `f` toggle fullscreen, `e` toggle edit mode (handles/grid)
- `s` save corner calibration to `calibration.json`, `l` reload it, `r` reset corners to full-screen quad
- `q` / `Esc` quit

## Architecture

Everything lives in `mapping_tool.py`, organized around three pieces:

- **`SourceReader`** — abstracts over a static image, a looping video file (`cv2.VideoCapture`,
  auto-rewinds via `CAP_PROP_POS_FRAMES` on EOF), a webcam (source arg is an int index), or a
  generated `make_test_pattern()` checkerboard/grid when no `--source` is given. `read()` always
  returns a frame resized to the configured output `(width, height)`.
- **`QuadWarper`** — owns the 4 destination corners (order: top-left, top-right, bottom-right,
  bottom-left), the mouse-drag interaction (`hit_test` / `on_mouse`), the homography computed via
  `cv2.getPerspectiveTransform` + `cv2.warpPerspective` (`homography()` / `warp()`), the debug
  overlay grid/handles (`draw_overlay`, edit-mode only, never baked into the final warped output),
  and calibration persistence (`save()` / `load()` to/from `calibration.json`, rescaling corners
  proportionally if the output canvas resolution changed since the file was saved).
- **`main()`** — argument parsing, OpenCV window/mouse-callback setup, and the render loop: read
  frame → warp → optionally draw overlay → `imshow` → handle key presses.

Calibration data round-trips through `calibration.json` (corner coordinates + the canvas
width/height they were calibrated at) — this file is written by the tool at runtime, not tracked
as source.
