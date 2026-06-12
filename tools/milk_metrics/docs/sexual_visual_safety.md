# Sexual Visual Safety Doctrine

This document expands the classification constitution from the perspective of sexual visual safety. It treats the metric set as a way to reason about charged adult visual material while preserving the subject as a person, keeping the image legible under ordinary visual description, and avoiding the failure modes that make an image feel unsafe, repellent, exploitative, or incoherent.

The framework is not a detector for explicit content. It is a structured language for adult, non-explicit, surface-auditable image recognition. The goal is to classify how an image carries charge safely: through personhood, composure, context, fabric, posture, expression, visual coherence, and controlled implication rather than through procedural depiction, coercive framing, humiliation, dehumanisation, or body-part reduction.

## Why sexual visual safety comes first

The central claim of the framework is that erotic relevance and visual safety are not separate stages. In this methodology, charge is only valuable when the image remains coherent, person-retaining, and non-repellent. A high local score on contour, smoothness, colour, or garment boundary does not by itself create a strong image. The same local feature can support safety when integrated into whole-person presentation, or undermine safety when isolated, over-sharpened, made crude, or detached from the subject.

This is why the metric set must begin from gates and relation rather than from body-region scoring. The classifier should first ask whether the image preserves an adult subject with self-possession, composure, and situational control. Only after that should it ask whether a stomach line, hip-line, garment threshold, blush, shadow, pose, crop, or colour field supports milk, peach, coal, or toy/cartoonisation.

## The cohesive measure set

The measure set should be understood as four interacting registers under one safety directive.

Milk is the safety register. It governs private charge, ordinary surface explanation, self-authored presentation, garment-led thresholds, soft enclosure, and whole-person retention. Milk asks whether the image can remain charged while still being described as composed adult glamour, private-room styling, camera-aware posture, fabric relation, or restrained visual presentation. Milk fails when the image becomes crude, coercive, humiliating, dehumanising, age-ambiguous, or procedurally explicit.

Peach is the warmth register. It governs bodily appeal as soft, integrated body presence: hip-line warmth, relaxed contour, fabric-held shape, body coherence, and physical ease. Peach should never be reduced to local anatomical targeting. It is strongest when bodily warmth remains attached to the subject as a person. Peach fails when the crop or emphasis turns the body into a detached surface, when contour becomes access logic, or when shape overpowers relation.

Coal is the pressured-feeling register. It governs private inward intensity: guarded disclosure, bashful resolve, contained embarrassment, shadowed composure, and self-possessed vulnerability. Coal is not fear, helplessness, shame-as-harm, or distress. Coal requires mutual recognition: the subject still appears present, aware, and in control of the presentation. The classifier should treat coal as low-confidence unless expression and posture are readable, because coal depends heavily on affect.

Toy/cartoonisation is the idealisation register. It governs whether simplification heightens the subject into an alive, coherent, self-possessed ideal form. Positive toy/cartoonisation produces clarity, charm, stylised coherence, and living presence. Failed toy/cartoonisation produces plastic skin, mannequin posture, vacant eyes, malformed shape, uncanny polish, childlike objecthood, or passive display.

The animation directive is the governing synthesis. It says that all four registers must preserve personhood, consented presentation, composure, whole-body coherence, surface auditability, and visual life. Milk supplies safety, peach supplies warmth, coal supplies inward pressure, and toy/cartoonisation supplies idealised simplification. None of these registers should be allowed to override the directive.

## Adult-only scope and age stability

The framework is only valid for clearly adult material. Age stability is a gate, not a score to optimise. The classifier should not treat youthful freshness, softness, slimness, or cute styling as automatically unsafe, because adult visual cultures can use softness, bashfulness, and cute presentation as authored adult material. At the same time, the classifier must prevent collapse into age ambiguity, dependency, helplessness, school-coded vulnerability, or undeveloped presentation.

This distinction matters because sexual visual safety depends on adult agency. A fresh or soft adult presentation may support milk when it remains self-possessed, composed, and camera-aware. The same softness becomes unsafe when the subject reads as underage, dependent, unaware, or stripped of control. Therefore the code should avoid any simple younger-equals-better logic. It should classify age stability through personhood, self-possession, non-child-coded styling, and contextual adulthood rather than through a single body metric.

## Surface auditability

Surface auditability means that the visible image can be explained through ordinary visual features without needing to name a hidden sexual procedure. The classifier should reward ordinary cues: clothing, fabric boundary, posture, hand placement, gaze, light, room privacy, mirror relation, crop integrity, body coherence, and expression. It should penalise cues that require crude procedural interpretation, extreme local inspection, or dehumanised access logic.

This is the reason garment thresholds are important. A waistband, hem, strap, sleeve, or fabric edge can carry visual charge while remaining an ordinary visible boundary. But the same boundary becomes unstable when cropped too tightly, sharpened too aggressively, or separated from personhood. The measure set must therefore combine threshold strength with crop integrity and relation context.

## Personhood and self-authored presentation

Personhood is the primary stabiliser. It is visible through face, gaze, posture, whole-body coherence, camera awareness, mirror authorship, shoulder line, hand control, and the sense that the subject is participating in the image rather than being reduced by it. Personhood can survive rear-facing or close framing if recognition, posture, and composition preserve the subject. Personhood weakens when the body becomes anonymous, fragmented, passive, object-like, or merely inspected.

Self-authored presentation is the second stabiliser. The image should read as controlled presentation rather than capture, accident, helplessness, or use. In code, this is difficult to detect directly, so early proxies are crude: face context, upper-body context, whole-body crop, mirror framing, posture continuity, and background relation. Later models may add pose, gaze, and expression classification, but the doctrine must remain explicit: self-authored presentation is a global relation, not a pixel feature.

## Safe-risk and authored vulnerability

Some visual cues resemble risk while remaining safe when authored by a coherent adult subject. Bashfulness, timidity, cute styling, protected embarrassment, and soft vulnerability can support coal or milk when the subject remains self-possessed, camera-aware, and situationally in control. These cues should not be automatically sanitised or denied. They are part of adult visual expression.

The safety boundary is agency. Authored vulnerability is a chosen presentation. Unsafe vulnerability reads as helplessness, fear, coercion, humiliation, dependency, or loss of personhood. The classifier should therefore separate bashful composure from fear, contained embarrassment from humiliation, guarded disclosure from evasion, and softness from passivity.

## Cuteness, softness, and recognition failure

Adult cute styling can be a legitimate authored register. Recognition systems often fail by either flattening cute styling into child-coded risk or denying that the styling is cute at all. Both errors are analytically poor. The correct task is to recognise adult semantic ownership of softness, cuteness, bashfulness, decorative styling, and pop-compressed presentation while distinguishing it from actual age ambiguity, helplessness, or agency-poor templates.

This matters for classification because some of the most relevant images may use softness rather than dominance, guardedness rather than overt confidence, or approachable vulnerability rather than hard glamour. A robust classifier should not force every safe adult image into mature-coded glamour. It should recognise self-possessed softness as a valid adult form.

## Fragmentation and crop discipline

Close crops are useful for measuring primitives such as surface smoothness, compression artefacts, garment boundary, and contour continuity. They are not sufficient for global register scoring. A stomach crop can tell us about smoothness, navel-line quality, or edge artefacts, but it cannot by itself prove milk, peach, coal, or self-authorship.

The report must therefore distinguish crop-level analysis from person-level analysis. Crop-level outputs should say: this crop supports a surface primitive. Person-level outputs should require context: face, posture, setting, body continuity, camera relation, or other evidence of subject retention. This prevents the system from mistaking an attractive local surface for a complete safe image.

## Repellence and visual aversion

Visual safety includes avoiding repellent cues. Ugliness, uncanny deformation, malformed anatomy, plastic vacancy, extreme artefacting, smeared texture, dead eyes, broken limbs, or mannequin-like passivity can collapse the visual relation even when other metrics look strong. This is especially important for generated images and heavy stylisation. A classifier should not treat smoothness or polish as automatically positive. Smoothness becomes harmful when it becomes plastic. Simplification becomes harmful when it becomes vacancy.

The toy/cartoonisation register exists partly to guard this boundary. It should reward alive idealisation and penalise object-like simplification. In generated-image workflows, this may require shape-coherence metrics, face-liveliness metrics, limb-continuity checks, and artefact maps.

## Public and private context

Private context supports milk and coal because it stabilises the visual relation. Bedrooms, mirror shots, soft interiors, enclosed lighting, and personal settings can support private charge. Public context can weaken safety by creating social exposure, surveillance, or performance pressure. However, outdoor imagery can still be private when the setting reads as secluded, enclosed, and personally directed rather than socially public.

The current code uses crude public-context proxies such as street-depth and sidewalk-like regions. These are provisional. They should be treated as soft gates requiring review, not as absolute judgements. A forest clearing, remote beach, or isolated outdoor scene may support privacy even though it is outdoors.

## Restoration versus transformation

The restoration search must never be allowed to create the score it is measuring. It may reduce compression artefacts, smooth block noise, or improve legibility slightly. It should not warp geometry, invent contours, reshape the body, intensify local signals, or create a more favourable image. This is why the code includes distortion and edge-loss penalties.

A valid restoration report should show original score, restored score, change map, and component changes. If the improvement comes mainly from reduced blockiness while edge preservation remains acceptable, the restoration is useful. If the improvement comes from visible distortion, blur, or shape change, the gate layer should limit or reject it.

## Reporting from a sexual visual safety perspective

A good report should be able to say: the image supports milk because private context, controlled posture, garment threshold, and subject coherence are present; peach is supported by warm body contour and fabric-held shape; coal is weak because expression is unreadable; toy is limited by artefacts; and a soft public-context gate reduces the global interpretation.

The report should avoid collapsing into a single score. The whole value of this methodology is that it preserves the reasons. Scores support comparison, but explanations support judgement.

## Future classifier development

The current rule-based system is a scaffold. It should evolve toward a multi-stage classifier:

1. Raw image and crop metadata.
2. Low-level proxies: smoothness, edge preservation, compression artefacts, colour regions, boundary structure.
3. Mid-level visual grammar: personhood, crop integrity, garment threshold, body coherence, setting privacy, stylisation coherence.
4. Register inference: milk, peach, coal, toy/cartoonisation.
5. Gate correction: age stability, personhood collapse, coercive or harm reading, public pressure, fragment dominance, uncanny artefacts.
6. Human-readable explanation.

The central requirement is that every new metric must name its safety function. It must state what it supports, what it can accidentally over-reward, and what gate prevents misuse.
