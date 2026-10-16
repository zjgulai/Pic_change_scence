export const meta = {
  name: 'fisheye-portrait-factory',
  description: 'End-to-end 180-degree fisheye candid action portrait generalization, verification, and generation workflow',
  whenToUse: 'Use when generating new 180-degree fisheye candid action portraits from a reference photo with strict identity preservation and physics verification',
  phases: [
    { title: 'Analyze', detail: 'Extract visual anchors from reference portrait' },
    { title: 'Design', detail: 'Draft generalized fisheye action themes in EN & ZH' },
    { title: 'Verify', detail: 'Verify identity lock, hand anatomy, fisheye optics, and safety wording' },
    { title: 'Generate', detail: 'Execute scripts/fisheye_portrait_pipeline.py and verify output files' }
  ]
}

const refImage = (args && args.referenceImage) || 'assets/images/portrait-source-reference-stable.png'
const requestedThemes = (args && Array.isArray(args.themes) && args.themes.length > 0)
  ? args.themes
  : [
      { slug: 'custom-theme', title: 'Custom Fisheye Action Snapshot', concept: (args && args.concept) || 'Dynamic foreground splash with candid laughter' }
    ]
const shouldGenerate = args && args.generate !== false

const ANCHOR_SCHEMA = {
  type: 'object',
  properties: {
    subjectAnchorSummary: { type: 'string' },
    outfitAndAccessories: { type: 'string' },
    environmentAndLighting: { type: 'string' }
  },
  required: ['subjectAnchorSummary', 'outfitAndAccessories', 'environmentAndLighting']
}

const PROMPT_SCHEMA = {
  type: 'object',
  properties: {
    slug: { type: 'string' },
    title: { type: 'string' },
    englishPrompt: { type: 'string' },
    chinesePrompt: { type: 'string' }
  },
  required: ['slug', 'title', 'englishPrompt', 'chinesePrompt']
}

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    passed: { type: 'boolean' },
    issues: { type: 'array', items: { type: 'string' } },
    refinedEnglishPrompt: { type: 'string' }
  },
  required: ['passed', 'issues', 'refinedEnglishPrompt']
}

const GEN_SCHEMA = {
  type: 'object',
  properties: {
    slug: { type: 'string' },
    outputPath: { type: 'string' },
    success: { type: 'boolean' },
    visualCheckSummary: { type: 'string' }
  },
  required: ['slug', 'outputPath', 'success', 'visualCheckSummary']
}

phase('Analyze')
const anchor = await agent(
  `Read the reference image at ${refImage} (or configs/portrait-fisheye-themes-stable.json if matching default) and extract exact visual anchors: facial structure, hairstyle, clothing, jewelry/pendant, and studio/lighting details.`,
  { label: 'analyze:ref-image', phase: 'Analyze', effort: 'low', schema: ANCHOR_SCHEMA }
)

const results = await pipeline(
  requestedThemes,
  t => agent(
    `Draft a 3:4 vertical 180-degree fisheye candid action image-to-image prompt pair (EN & ZH) for theme "${t.title}" (${t.slug}).
Concept: ${t.concept}
Visual Anchors to lock upfront:
- Subject: ${anchor ? anchor.subjectAnchorSummary : 'Same young East Asian woman from reference'}
- Outfit & Accessories: ${anchor ? anchor.outfitAndAccessories : 'Exact outfit and pendant from reference'}
- Environment: ${anchor ? anchor.environmentAndLighting : 'Original lighting and setting unless cross-scene specified'}
Rules:
1. Lead with preservation of identity, hair, outfit, and jewelry.
2. Specify true 180-degree diagonal fisheye lens tilted slightly down, extreme foreground forced perspective, centered face, and subtle optical circular vignette (no black ring frame).
3. High-speed flash freezing foreground particles/liquid along a physically coherent trajectory.
4. Exactly one person, no more than two arms and two five-fingered hands.`,
    { label: `design:${t.slug}`, phase: 'Design', effort: 'low', schema: PROMPT_SCHEMA }
  ),
  (draft, t) => agent(
    `Adversarially verify and refine the English prompt for "${t.title}" (${t.slug}):
1. Does it start with explicit identity, hair, outfit, and accessory preservation?
2. Does it enforce "exactly one person, no more than two arms and two five-fingered hands"?
3. Does it avoid safety-classifier false-positive trigger words (e.g., avoid combining "chest" + "leans into" + "ice pop")?
Draft:
${draft.englishPrompt}`,
    { label: `verify:${t.slug}`, phase: 'Verify', effort: 'low', schema: VERDICT_SCHEMA }
  ).then(v => ({
    ...draft,
    englishPrompt: (v && v.refinedEnglishPrompt) ? v.refinedEnglishPrompt : draft.englishPrompt
  })),
  async (verified, t) => {
    if (!shouldGenerate) {
      return { ...verified, generated: false }
    }
    const genRes = await agent(
      `Run python3 /Users/pray/project/Pic_ZYT/scripts/fisheye_portrait_pipeline.py --ref "${refImage}" --custom-slug "${t.slug}" --custom-prompt ${JSON.stringify(verified.englishPrompt)} --force, then Read the generated image at /Users/pray/project/Pic_ZYT/assets/images/portrait-edit-fisheye-${t.slug}-stable.png to verify visual quality.`,
      { label: `generate:${t.slug}`, phase: 'Generate', effort: 'low', schema: GEN_SCHEMA }
    )
    return { ...verified, generation: genRes }
  }
)

return { anchor, results: results.filter(Boolean) }
