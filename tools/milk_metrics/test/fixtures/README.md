# Image metric fixtures

This directory contains image fixtures for local image-metric development.

`adult_reference_pose.png.b64` is a base64-encoded PNG fixture supplied for analyzer testing. It is stored as text because the JSON patch transport currently accepts UTF-8 file operations only.

Decode it locally with:

```bat
python tools\milk_metrics\test\fixtures\decode_fixture.py adult_reference_pose.png.b64 tools\milk_metrics\test\fixtures\adult_reference_pose.png
```

The original PNG SHA-256 is:

```text
a3e0af130ea5406eeeb19b0049590d7463db51cf563e877a9c42d57fc0c3e006
```

Use this fixture for local analyzer checks, not as a quick compile gate.
