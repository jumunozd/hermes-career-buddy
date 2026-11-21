# Writer / Claude Code handoff

## Deliverable and boundary
Maintain this folder independently of Career Development OS. It contains the voice profile, references and learning record. The document-building skill/specification owns content structure, format, selection criteria compliance and output tooling. Job Application Engine owns professional facts. The user Writing Voice changes expression only. No Hermes or Job Application Engine changes were performed.

## Writer contract (portable; not a Hermes configuration schema)
Supply: document type and authoring rules; audience/relationship; communication purpose; confirmed recipient needs; verified facts with source references; exact dates/commitment levels; draft if present; latest contextual preference record. Retain fact/source mapping internally through both variants.
Load SKILL.md and relevant references before drafting. Ask one question at a time when critical context is missing. Return two usable variants by default. On the user’s selection, persist the contextual decision automatically and use it in later drafts. Return only a requested final version after selection. Do not expose analysis or lessons unless requested.

Suggested integration instruction for Writer:
“Apply candidate-writing-voice as the voice layer. Use the document-authoring instructions for structure and requirements and Job Application Engine evidence for facts. Preserve facts and certainty. Consult current contextual decisions. Ask about missing key context. Offer two variants unless the user requests a single final version. Persist explicit choices in the maintained decision record without asking again; report unsaved updates honestly.”

## Hermes verification — checked 2026-11-08
Official source: https://hermes-agent.nousresearch.com/docs/user-guide/features/skills
Current public documentation describes SKILL.md with YAML name/description, supporting references, progressive loading through skill_view and a default ~/.hermes/skills directory. That is a documented default, not a verified project destination. This package uses the portable common subset and the documented When to Use / Procedure / Pitfalls / Verification headings.

Hermes executable was detected locally, but `hermes --version` failed because its install lock was not writable. Target deployment/version was not established. No installation, configuration edits or invocation test was attempted. Compatibility with the project's exact version remains PENDING for Claude Code. Do not infer from current public docs that every deployment supports the same discovery or preload mechanisms.

## Integration tasks for Claude Code
1. Identify the actual Career Development OS checkout, target Hermes version/commit and Writer launch mechanism. Read that version’s official docs/source. Preserve existing configuration.
2. Resolve the authorised skill destination/loading method for that environment; do not blindly copy to a presumed global folder or invent a config key. Obtain the user’s authorisation before changing existing Hermes setup or Job Application Engine.
3. Make all referenced files available and demonstrate Writer can load them. Keep one maintained copy of preferences, with reviewable/serialised updates. Do not introduce a separate learning service without need.
4. Connect the already-existing evidence source and document-authoring workflow. Demonstrate unsupported claims remain blocked and formal requirements survive voice edits.
5. Run the reproducible cases in quality-tests.md. Save exact inputs, two outputs, factual checks, version/model/settings and the user’s choice. Verify a selection persists and affects the next eligible draft across sessions.
6. Record integration status and resolved deployment details here. Do not mark target compatibility, memory persistence or voice fidelity passed without evidence.

## Limitations and open validation
Only two fresh original-to-rewrite cases have been approved; one is hypothetical. Earlier samples mix AI and user authorship. No full CV, selection criteria response or cover letter has been evaluated with the user using this package. Qualitative preferences are not an accuracy percentage. Automatic preference storage is an integration requirement, not a running capability in this deliverable. Exact target version and integration remain unresolved.
