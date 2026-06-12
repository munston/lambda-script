# Visual Grammar

The visual grammar is the bridge between doctrine and code. It lists the visible evidence classes that the classifier may attempt to measure. Each class is a proxy source. None is sufficient by itself.

## Person and relation

Face, gaze, expression, shoulder line, head angle, and upper-body context support the personhood layer. They are imperfect proxies, but they help distinguish self-authored presentation from anonymous surface display. A visible face is not required in every image, because rear-facing or mirror compositions can still preserve mutual recognition, but some sign of subject presence must remain.

Camera relation is a separate feature. Direct camera address, mirror authorship, over-shoulder recognition, or controlled pose can all support self-authored participation. A passive crop, a hidden face with no compensating posture, or a pure torso fragment weakens this layer.

## Body coherence

Whole-body coherence means the image preserves the subject as a coherent figure. The classifier should track crop ratio, visible torso continuity, limb continuity, and whether the image concentrates too strongly on a single local body surface. The point is not to ban close crops. The point is to identify when the crop stops reading as a person and begins reading as detached surface.

## Garment thresholds

A garment threshold is an ordinary visible boundary: waistband, hem, strap, sleeve, neckline, fabric fold, or garment tension. In this framework, garment thresholds can carry private implication while remaining surface-auditable. The classifier should measure boundary clarity, fabric-to-skin contrast, and boundary continuity, while also penalising extreme local inspection.

The same primitive can support or harm the register depending on context. A clear waistband in a whole-person image can support milk or peach. A very tight crop of the same boundary can become fragmentary and lower the global score.

## Surface quality

Surface quality includes smoothness, local variance, edge harshness, compression artefacts, skin/fabric separation, and over-sharpening. The current code rewards smooth unstrained surface and compression cleanliness, while guarding against blur and distortion. This should be understood as a restoration diagnostic, not as a beauty classifier.

Smoothness should mean soft continuity rather than gym-like segmentation or carved definition. Edge preservation remains necessary because over-smoothing can erase structure and create a false improvement.

## Peach evidence

Peach evidence comes from hip-line warmth, soft contour, relaxed body presence, fabric-held shape, side/rear body coherence, and bodily appeal integrated with the person. Measurable proxies include contour continuity, fabric boundary, body-region continuity, and warm palette. The report must still check whether the person is retained.

## Coal evidence

Coal evidence comes from guarded expression, contained embarrassment, bashful resolve, inward pressure, shadowed composure, and deliberate disclosure. Pixel proxies are weak here. Face, gaze, posture compression, lowered light, and controlled body angle can support coal, but the classifier should mark coal inference as low-confidence unless human annotation confirms the affect.

Coal must be separated from fear. Fear, helplessness, vacant distress, or harm reading should fire gates rather than increase coal.

## Toy and cartoon evidence

Toy/cartoon evidence is about idealised simplification. Positive toy evidence includes clean shape language, coherent stylisation, lively expression, simplified but plausible anatomy, and retained personhood. Negative toy evidence includes plastic skin, mannequin posture, vacant eyes, malformed limbs, uncanny geometry, or childlike object presentation.

This register is especially important when analysing generated or stylised imagery, because technical polish can mask loss of life. The classifier should score artefact quality and shape coherence separately from ordinary sharpness.

## Context evidence

Setting and background decide whether the image reads as private, public, domestic, staged, or chaotic. Bedrooms, mirrors, soft interiors, blurred background, and enclosed lighting can support private context. Street depth, visible public circulation, institutional surroundings, or crowd cues can reduce privacy. Outdoor settings can still support privacy when they read as secluded rather than socially public.
