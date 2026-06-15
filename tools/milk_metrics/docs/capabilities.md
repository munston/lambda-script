# Image metrics capability note

Current image-metrics commands are declared by the metrics gizmo as `analyze`, `penalty-mask`, and `restore`. In practical terms, the image side can support deterministic analyzer runs, diagnostic penalty-mask generation, and restoration-style processing for supplied image files.

The current image side should be treated as an analyzer and transformer scaffold. It does not yet provide a full interactive screen loop, metric adaptation loop, or stochastic image-update loop against a classifier.

The next development step is to add a closed-loop optimizer around the analyzer:

1. decode or load an image fixture;
2. compute analyzer metrics and any penalty mask;
3. generate a bounded stochastic candidate update;
4. re-score the candidate;
5. accept changes that improve the selected metric while preserving hard safety and visual-coherence constraints;
6. write a report containing the accepted trajectory.

This fixture patch adds `adult_reference_pose.png.b64` as a local reference image for that development path.
