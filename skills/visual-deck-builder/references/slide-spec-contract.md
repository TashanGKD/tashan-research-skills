# Slide Spec Contract

`slide_spec.json` is the planning contract for image-model-driven PPT generation. It plans the content and full-slide image first, then records the rendered slide image used for image-only PPTX packaging. Editable reconstruction fields are optional and only used when the user explicitly requests editable PPT objects.

## Minimal Shape

```json
{
  "deck": {
    "title": "Deck title",
    "language": "zh",
    "aspect_ratio": "16:9",
    "audience": "researchers",
    "route": ["topic_only"],
    "style_brief": "clean visual report style",
    "reference_guard": {
      "style_reference_policy": "layout_density_only",
      "allowed_text_source": "slide_spec",
      "forbidden_terms": ["OpenAI", "GPT-4", "ChatGPT", "2023"]
    }
  },
  "slides": [
    {
      "slide_id": "01",
      "purpose": "Open the presentation with the core claim",
      "title": "Main title",
      "body_text": ["Point one", "Point two"],
      "must_show": ["keyword", "metric or source term"],
      "visual_brief": "full-slide image with strong hierarchy",
      "delivery_mode": "image_only",
      "image_prompt": "Generate the full finished slide image with all intended text and complete composition...",
      "rendered_image": "slides/01.png",
      "editable_text": [
        {
          "text": "Main title",
          "role": "title",
          "box": {"x": 0.08, "y": 0.10, "w": 0.72, "h": 0.12},
          "style": {"font_size": 30, "bold": true, "color": "111111"}
        }
      ],
      "evidence": [],
      "status": "planned"
    }
  ]
}
```

## Required Fields

Deck:

- `title`
- `language`
- `aspect_ratio`
- `route`
- `style_brief`

Slide:

- `slide_id`
- `purpose`
- `title`
- `body_text`
- `must_show`
- `visual_brief`
- `delivery_mode`: usually `image_only`
- `image_prompt`
- `rendered_image` after generation

Optional editable fields:

- `editable_strategy`: use `layered_editable` only for explicit editable reconstruction requests
- `layer_prompts`
- `editable_text`

After image generation:

- `status`: `image_rendered`, `composed`, `qa_passed`, `needs_retry`, or `blocked`

## Image Prompt

`image_prompt` must describe the complete final slide image:

- full finished slide image with strong composition
- all intended page text, no placeholders
- enough visual richness to serve as the delivery image
- exact terms that must appear, and dense text that should be simplified rather than hallucinated

The final primary PPTX uses `rendered_image` as a full-slide picture.

## Optional Layer Prompts

For explicit editable reconstruction requests, `layer_prompts` may contain:

- `visual_target`: full finished slide image with strong composition, all intended page text, no placeholders, and enough visual richness to serve as the aesthetic benchmark.
- `background`: text-free, frame-free background image extracted from or regenerated against the visual target.
- `frame`: structural visuals only, including panels, cards, fills, separators, arrows, chart geometry, and non-text scaffolding extracted from the visual target.
- `icons`: icons, decorative marks, pictorial objects, and stylized text that should stay as images, extracted from the visual target.

Do not use `visual_target` as a final editable PPT layer. It is a design target for optional extraction and visual QA.

## Editable Text

Editable text is optional metadata for overlays or explicit reconstruction. It is ordinary PPT text, not OCR guessed after the fact.

`box` uses fractions of the slide canvas:

- `x`, `y`: top-left
- `w`, `h`: width and height
- all values in `[0, 1]`

When editable reconstruction is requested, use editable text boxes for:

- titles
- section labels
- body bullets
- key metrics
- citations
- short callouts

Use the icon/decoration layer for stylized text that ordinary PPT fonts cannot reproduce cleanly.

## Evidence

For source-grounded decks, evidence items should be compact:

```json
{
  "source_id": "paper-1",
  "locator": "section 3.2 or page 5",
  "claim": "Exact or paraphrased claim used on the slide",
  "confidence": "direct|inferred"
}
```

## Reference Guard

Use `reference_guard` whenever `deck.route` includes `style_reference` or when borrowing layout patterns from public examples.

`reference_guard` prevents semantic bleed from the reference image into the generated visual target:

- `style_reference_policy`: what may be copied from the reference, such as `layout_density_only`, `palette_only`, `preserve_structure`, or `component_style_only`.
- `allowed_text_source`: usually `slide_spec`; the visual target should use only text planned in the spec.
- `forbidden_terms`: reference brands, dates, metrics, labels, and topic-specific words that must not appear in planned content or the generated target.

If the generated slide visually contains forbidden reference terms, reject the image and regenerate before packaging.

## Existing Slide Edit

When `deck.route` includes `existing_slide_edit`, each slide must include `source_visual_target`, or the deck must include `source_visual_targets`.

Use this field to identify the exact source slide image or rendered page being packaged, redesigned, or optionally reconstructed. Missing source targets are a validation error because they make it impossible to audit which page was used.
