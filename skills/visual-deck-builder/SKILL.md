---
name: visual-deck-builder
description: >-
  Build image-model-driven PPT decks from a user topic, source materials, papers, reports, notes, datasets, existing slides, or style references. Use when the user asks to create, redesign, package, or QA a PowerPoint deck where every slide should first be generated as a high-quality full-slide image and packaged into PPTX with manifests, previews, and evidence-backed QA. Layered editable reconstruction is optional and only used when explicitly requested.
  This is the general deck-building entry. Prefer narrower skills only when the request is specifically an academic/research PPT workflow, a prompt/method clinic, a sci-employee course/video wrapper, or a recurring Chronicle research/script loop.
---

# Visual Deck Builder

Create high-quality visual PPT decks from whatever the user supplies: a topic, a document, a paper, a folder of materials, a style reference, or existing slide images. The main workflow is **spec first, full-slide image first, then image-only PPTX packaging**:

```
input -> intent/source resolver -> content plan -> slide_spec.json
      -> per-slide image prompt -> full-slide image
      -> deck.json -> image-only PPTX
      -> preview + render manifest + QA report
```

The deck is not a fixed "paper mode" or "topic mode". Route by the user input, but the default final slide is a complete full-slide image inside PPTX. Use layered editable reconstruction only when the user explicitly asks for editable PPT objects and accepts the extra QA loop.

## Boundary With Related PPT Skills

Treat this skill as the default entry for actual PPT/deck creation, redesign, packaging, or QA. Route away only when the user's request clearly matches a narrower asset:

- Use `research-ppt-generation` when the task is specifically an academic or research deck and needs paper/PDF-to-narrative planning, research audience structure, figure grounding, or academic template logic.
- Use `ppt-image-generation` when the user is asking for slide-image prompting strategy, image-model page briefs, route selection, or diagnosis of weak PPT image prompts, not for an end-to-end deck package.
- Use `sci-employee-ppt-making` only for the sci-employee wrapper: research training course pages, PPT-to-video,讲稿/字幕/配音闭环, or persona-specific teaching delivery.
- Use `chronicle-ai-ppt-open-source-research-loop` only for the recurring AI PPT open-source ranking/gallery loop.
- Use `chronicle-weekly-ai-deck-script` only to turn an existing image-based AI frontier deck into a clean page-ordered speaker script.

Do not create another PPT skill for a new deck style until this routing fails for at least two real tasks.

## Core Rules

1. Treat `slide_spec.json` as the source of truth for content, evidence, rendered image paths, and optional editable text metadata.
2. Use an actual raster image generation/editing backend for each full-slide page image. Do not draw target slides with SVG, HTML, Canvas, PIL, matplotlib, PPT shapes, or screenshots and call that image generation.
3. Every slide gets a full-slide rendered image with complete composition and intended page text. This image is the default delivery source.
4. The default final PPTX is image-only: one full-slide picture per slide, with no required editable text boxes.
5. Do not judge image-only decks with the editable reconstruction gate. Use `scripts/audit_image_only_deck.py` for the primary path.
6. Layered editable reconstruction is an opt-in route. Never place editable text directly on top of the same text already burned into an image layer.
7. Keep source-grounded decks source-grounded. If the input is a topic only, allow the model to create plausible structure, but mark unsupported examples/data as assumptions or omit specific claims.
8. Save reproducible artifacts: `slide_spec.json`, `prompts/`, `slides/`, `deck.json`, `render_manifest.json`, PPTX, previews, and QA notes.
9. Keep the public workflow centered on this skill's own input routing, source grounding, spec planning, full-slide image QA, packaging, and release gates. Treat any vendored composer utility as an implementation detail, not as the product identity.
10. Never write API tokens into skill files, manifests, logs, prompts, or final replies. Read tokens from environment variables only.

## Input Routing

Classify input before generating:

- `topic_only`: user gives a topic, goal, audience, or theme but no source material.
- `source_grounded`: user provides papers, PDFs, reports, notes, webpages, data, or extracted text.
- `style_reference`: user provides screenshots, templates, brand images, color references, or old PPTs.
- `existing_slide_edit`: user provides slide images or PPT/PDF pages to redesign, continue, or make editable.
- `mixed`: combine source grounding with style references and user constraints.

Read [references/input-routing.md](references/input-routing.md) when routing is unclear.

## Standard Workflow

### Script Requirements

Local packaging and QA scripts need a Python environment with:

- `Pillow`
- `python-pptx`

If imports fail, switch to an environment that has these packages or install them before running `scripts/audit_image_only_deck.py`, `scripts/compose_layered_deck.py`, `scripts/render_layered_preview.py`, `scripts/validate_visual_deck.py`, or optional editable reconstruction tests.

### 1. Resolve Requirements

Infer reasonable defaults unless the user asks for exact choices:

- audience and use case
- page count
- language
- aspect ratio
- visual style
- source citations/evidence requirements
- whether existing slide images should be converted, continued, or redesigned

If a missing detail changes the deck materially and cannot be inferred, ask one concise question.

### 2. Build Content Plan

For source-grounded input:

- extract claims, entities, methods, results, figures, and must-use terminology
- preserve exact names and numbers
- record where each important claim came from
- avoid claims not supported by the source

For topic-only input:

- generate a useful narrative from the topic and user intent
- prefer conceptual frameworks, examples, and comparisons over fabricated numbers
- flag any invented case studies, market data, or citations as assumptions unless verified

### 3. Write `slide_spec.json`

Every slide must include:

- `slide_id`
- `purpose`
- `title`
- `body_text`
- `must_show`
- `visual_brief`
- `delivery_mode`: usually `image_only`
- `image_prompt`
- `rendered_image` once generated
- `editable_text` only when an optional overlay or editable reconstruction is requested
- `evidence` when source-grounded
- `status`

Use the schema and examples in [references/slide-spec-contract.md](references/slide-spec-contract.md).

### 4. Generate Full-Slide Image Prompts

Create self-contained prompt files for each slide:

- `prompts/NN-slide.md`: full finished slide image with complete composition, strong aesthetics, all intended page text, and no placeholders.

Each prompt must include:

- slide aspect ratio and language context
- style and color constraints
- what must appear on the final full-slide image
- what text must be exact or should be avoided if too small
- reference image role if provided: `style_only`, `preserve_structure`, `use_elements`, or `edit_target`

For generated decks, the rendered full-slide image is the PPT source. For existing slide images, use the user's slide image directly only when the user asks for packaging or style-preserving continuation. Show generated images with `view_image` before accepting them. A local path in a prompt is not a real image input.

For `existing_slide_edit`, each slide spec must include `source_visual_target` or the deck must include `source_visual_targets`. This proves which source page is being packaged, redesigned, or optionally reconstructed and prevents accidental reuse of an old run artifact.

For any `style_reference` route, add `reference_guard` to the deck or slide spec before generating:

- `style_reference_policy`: usually `layout_density_only`, `palette_only`, or `preserve_structure`.
- `allowed_text_source`: usually `slide_spec`.
- `forbidden_terms`: brands, years, metrics, topic words, and example labels that appear in the reference but must not migrate into this deck.

When using any public example as a reference, inherit only layout density, hierarchy, and reconstruction mechanics. Do not inherit its topic, brands, dates, numbers, or example copy.

### 5. Render Full-Slide Images With Image Model

Use the best available backend in the current environment:

- Codex `image_gen` if available in chat.
- Giiisp/SiTian Imagine when `GIIISP_AUTH_TOKEN` is set.
- Project-specific image provider if working inside an app.

Read [references/image-runtime.md](references/image-runtime.md) before calling Giiisp or another HTTP image API.

Before optional extraction, run a backend/input preflight:

```powershell
python scripts/preflight_extraction_backend.py --target visual_targets/01.png --run-root . --slide-id 01 --out qa/preflight-01.json
```

If preflight reports `blocked`, stop and record the blocker. Do not generate replacement slides or layers with local code as a substitute for image-model output.

For every generated slide image, update `render_manifest.json`:

```json
{
  "slides": [
    {
      "slide_id": "03",
      "prompt_file": "prompts/03-slide.md",
      "backend": "giiisp|codex-imagegen|project-provider",
      "generated_source": "provider run id or source image path",
      "copied_to": "slides/03.png",
      "status": "completed"
    }
  ]
}
```

If image generation is blocked, write the blocker to the manifest and stop. Do not replace a blocked slide with programmatic art.

### 6. Build `deck.json` And Compose Image-Only PPTX

Build a simple deck manifest:

```json
{
  "slide_width_in": 13.333,
  "slide_height_in": 7.5,
  "units": "fraction",
  "slides": [
    {"background": "slides/01.png"},
    {"background": "slides/02.png"}
  ]
}
```

Compose with the available image PPT composer, for example:

```powershell
python scripts/gorden_image2pptx/compose_pptx.py deck.json out/deck-image.pptx --preview-dir previews
```

The output should have exactly one full-slide picture per slide.

### 7. Optional Editable Reconstruction

Use the older background/frame/icons/text reconstruction path only when the user explicitly requests editable PPT objects. Treat it as experimental for dense Chinese real-world slides. It requires separate extraction prompts, layer manifests, visual comparison, text audits, and manual/multimodal review.

### 8. Build `layered_deck.json` For Optional Editable Runs

Layer stack per slide:

1. `background`: full-slide image with no ordinary text, no frame, no icons.
2. `frame`: full-slide transparent PNG containing structure, chart geometry, panels, separators, fills, arrows, and non-text scaffolding.
3. `icons`: positioned transparent PNG items for icons, decorations, pictorial objects, and stylized text.
4. `texts`: real PPT text boxes for ordinary editable text.

Read [references/reconstructed-editable.md](references/reconstructed-editable.md) for the layout contract. Read [references/editable-reconstruction-route.md](references/editable-reconstruction-route.md) for the visual-target reconstruction route and QA loop.

### 9. Compose Editable PPTX For Optional Editable Runs

Use the reconstruction composer for source-image extraction work:

```powershell
python scripts/gorden_image2pptx/compose_pptx.py layered_deck.json out/deck-reconstructed-editable.pptx --preview-dir previews
```

Use `scripts/compose_layered_deck.py` only when a simple internal fixture or compatibility case already follows this skill's normalized `layered_deck.json` schema:

```powershell
python scripts/compose_layered_deck.py layered_deck.json out/deck-reconstructed-editable.pptx
```

This creates an optional editable PPTX. Text is real PPT text; frame and icon layers are movable images. Do not use this path as the default unless the user asks for editability.

For reconstruction composer layouts, keep `fit_text` enabled unless there is a deliberate typography reason to disable it. Dense Chinese pages should use real CJK-capable font names in the PPTX, and the preview path must resolve a CJK font on the current OS. A preview with black CJK glyph boxes, unreadable overflow, or title/body overlap is a failed visual QA artifact even when the PPTX has editable text boxes.

### 10. Render QA Previews

Use `scripts/render_layered_preview.py` to create visual QA previews from `layered_deck.json`:

```powershell
python scripts/render_layered_preview.py layered_deck.json --out-dir previews --show-boxes
```

The preview renderer is for inspection only. Do not use preview images as PPT source layers or as a replacement for image-model-generated background, frame, or icon assets.

### 11. QA

Run image-only validation before primary delivery:

```powershell
python scripts/audit_image_only_deck.py out/deck-image.pptx --spec slide_spec.json --render-manifest render_manifest.json --deck-json deck.json --out qa/image-only-pptx.json
python scripts/audit_visible_text_review.py qa/visible-text-review.json --min-slides 1 --out qa/visible-text-review-audit.json
```

For optional editable reconstruction, run the editable validation gates:

```powershell
python scripts/validate_visual_deck.py slide_spec.json --layers layered_deck.json --layer-manifest layer_manifest.json
```

Audit the final PPTX structure:

```powershell
python scripts/audit_pptx_editability.py out/deck-reconstructed-editable.pptx --out qa/pptx-editability.json --fail-flattened
python scripts/audit_pptx_text_against_spec.py slide_spec.json out/deck-reconstructed-editable.pptx --out qa/pptx-text-vs-spec.json
python scripts/audit_layered_layout.py layered_deck.json --out qa/layered-layout.json --fail-on-warn
python scripts/audit_visual_quality.py layered_deck.json --out qa/visual-quality.json
python scripts/gorden_image2pptx/icon_coverage_audit.py layered_deck.json qa/icon-coverage-expected.json --out qa/icon-coverage.json
python scripts/gorden_image2pptx/build_frame_residue_contract.py layered_deck.json --icon-coverage-expected qa/icon-coverage-expected.json --out qa/frame-residue-regions.json
python scripts/gorden_image2pptx/frame_residue_audit.py layered_deck.json qa/frame-residue-regions.json --out qa/frame-residue.json
python scripts/audit_visual_acceptance.py qa/visual-review.json --compare qa/visual/report.json --out qa/visual-acceptance.json --fail-on-warn
```

`build_frame_residue_contract.py` emits bbox-only skeleton regions by default. Add explicit `--color-family teal_green`, `--color-family any_saturated`, or another supported family only when the slide spec/extraction plan says those movable decorations must not remain in the frame layer.

When icon coverage or visual acceptance fails on a dense page, generate targeted next-pass prompts instead of repeating a broad extraction prompt:

```powershell
python scripts/gorden_image2pptx/build_extraction_prompt_pack.py qa/icon-coverage.json qa/icon-coverage-expected.json --out-dir prompts/coverage-next-pass --language zh
```

Open the current visual target with `view_image` before using any generated prompt. These prompt files assume the just-opened image is the edit target; local paths inside prompts are not image inputs.

If `audit_layered_layout.py` reports text overlap, icon crowding, cramped text, or edge clipping, repair the normalized layer coordinates before recomposing:

```powershell
python scripts/repair_layered_layout.py layered_deck.json --out layered_deck.repaired.json --report qa/layered-layout-repair.json
python scripts/audit_layered_layout.py layered_deck.repaired.json --out qa/layered-layout-repaired.json --fail-on-warn
python scripts/compose_layered_deck.py layered_deck.repaired.json out/deck-reconstructed-editable.pptx
```

Use the repair script only for coordinate-level cleanup of already extracted layers. It must not replace visual-target generation, image-model layer extraction, or manual visual QA.

For planning-stage specs without layer assets, use `--allow-planning`; do not use that flag for final delivery QA.

QA must check:

- `slide_spec.json` parses and every slide has required fields
- primary delivery slides use `delivery_mode: image_only` or clearly imply image-only delivery through `rendered_image`
- every slide has a generated or source-provided full-slide image
- `deck.json` covers every final slide and points to readable slide images
- `render_manifest.json` records image-model provenance for every generated slide
- the final image-only PPTX passes `audit_image_only_deck.py`: one full-slide picture per slide and no required editable text boxes
- previews are manually compared with `slides/` for unreadable text, bad aesthetics, wrong aspect ratio, drift, repeated layouts, or chroma-key artifacts
- `qa/visible-text-review.json` records visible-text QA for every slide, including allowed text, forbidden terms, unsupported numbers, unsupported dates, unsupported names, readability, and notes
- `audit_visible_text_review.py` passes before release; use `--fail-on-warn` for source-grounded decks that require exact wording
- `style_reference` routes include `reference_guard`, and the visual target is checked for reference semantic bleed
- `existing_slide_edit` routes declare `source_visual_target` or `source_visual_targets`
- source-grounded decks carry evidence
- no primary slide uses `programmatic`, `PIL`, `SVG`, `HTML`, `Canvas`, matplotlib, screenshots, or copied local mockups as a substitute for image-model output
- token strings are absent from prompts, manifests, reports, scripts, logs, and final replies

Optional editable reconstruction QA must check:

- `layered_deck.json` covers every spec slide
- every slide has background and frame assets
- icons/decorations are positioned when needed
- dense visual-target reconstruction runs include `qa/icon-coverage-expected.json` and pass `scripts/gorden_image2pptx/icon_coverage_audit.py`, so important source regions are covered by actual movable icon/decor assets instead of only by total icon count
- dense visual-target reconstruction runs include `qa/frame-residue-regions.json` when the slide spec declares areas where movable decorations must not remain in the frame layer; generate a skeleton from icon/decor ownership evidence with `build_frame_residue_contract.py`, add explicit `forbidden_residue` checks only where the slide plan warrants them, and require `scripts/gorden_image2pptx/frame_residue_audit.py` to pass
- ordinary text is real PPT text in `texts`
- the final PPTX passes `audit_pptx_editability.py` and is not flagged as flattened image-only
- the final PPTX passes `audit_pptx_text_against_spec.py`, with no missing or extra editable text against `slide_spec.json`
- reconstruction composer previews show readable CJK text and fitted dense text; do not accept a deck whose preview only passes after ignoring renderer black boxes, text overflow, or doubled text
- the final `layered_deck.json` passes `audit_layered_layout.py --fail-on-warn`, so dense pages do not ship with overlapping text, crowded icons, cramped text boxes, or edge-clipped editable elements
- `audit_visual_quality.py` is reviewed for dense decks, especially repeated card-only layouts, missing chart/table/legend semantics, and overly mechanical text-box patterns
- `audit_visual_acceptance.py` passes against actual human or multimodal visual review notes; do not ship a deck just because structural audits pass
- image layer files exist and are readable
- `layer_manifest.json` records image-model provenance for each required visual target and layer
- no layer uses `programmatic`, `PIL`, `SVG`, `HTML`, `Canvas`, matplotlib, screenshots, or copied final-slide crops as its source
- previews are manually compared with `visual_targets/` for missing layers, doubled text, bad alignment, unreadable text, weak aesthetics, and visual drift
- if the preview renderer cannot display Chinese or other CJK text correctly, inspect PPTX text structure and use another renderer or direct PowerPoint review before marking `preview_readability` and `text_rendering` as pass

For primary release or regression checks, run the image-only package audit against a real run:

```powershell
python scripts/audit_image_only_deck.py out/deck-image.pptx --spec slide_spec.json --render-manifest render_manifest.json --deck-json deck.json --out qa/image-only-pptx.json
python scripts/audit_visible_text_review.py qa/visible-text-review.json --min-slides 1 --out qa/visible-text-review-audit.json
```

For optional editable reconstruction regression checks, run:

```powershell
python scripts/self_test_visual_deck.py
```

For deeper QA and originality guidance, read [references/qa-and-originality.md](references/qa-and-originality.md).

## Output Structure

Use an isolated run directory:

```
visual_deck_runs/<timestamp>_<slug>/
|-- input_summary.md
|-- slide_spec.json
|-- prompts/
|   `-- 01-slide.md
|-- slides/
|   `-- 01.png
|-- deck.json
|-- render_manifest.json
|-- qa_report.json
|-- qa/
|   `-- image-only-pptx.json
|   `-- visible-text-review.json
|   `-- visible-text-review-audit.json
|-- previews/
|   `-- slide_01.png
`-- out/
    `-- deck-image.pptx
```

Optional editable reconstruction runs may additionally include `visual_targets/`, `layers/`, `layered_deck.json`, `layer_manifest.json`, overlay previews, and `out/deck-reconstructed-editable.pptx`.

## When To Read References

- Routing or mixed inputs: [references/input-routing.md](references/input-routing.md)
- JSON schema and editable layer contract: [references/slide-spec-contract.md](references/slide-spec-contract.md)
- Optional editable visual-target reconstruction route: [references/editable-reconstruction-route.md](references/editable-reconstruction-route.md)
- Optional reconstructed editable PPTX path: [references/reconstructed-editable.md](references/reconstructed-editable.md)
- Giiisp/SiTian, Codex imagegen, or provider token handling: [references/image-runtime.md](references/image-runtime.md)
- QA gates and avoiding "wrapper" positioning: [references/qa-and-originality.md](references/qa-and-originality.md)
