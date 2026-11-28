# Mandatory voice layers (the user, 2026-11-26)

Workflow for every CV, letter and statement, in this order. No step is optional and none is skipped
for a "small" revision:

1. **Generate**: draft `content.json` from the IN units (SKILL step 7).
2. **Soul Voice**: the user's approved voice (`candidate-writing-voice`). Authority for register.
3. **Humanizer**: the bundled Hermes `humanizer` skill. Only removes AI writing tells.
4. **Fact verification**: `bin/hcb engine run` (fit, verify, ATS, keywords, style, naturalness) and the
   claim map. It runs AFTER the voice layers, so a reworded sentence can never slip past the fact checks.
5. **Recruiter**: separate review, including Q10 naturalness and authenticity.

## Precedence
Facts (fact bank, Engine rules) > Soul Voice > Humanizer > generic style advice.
If Humanizer suggests something Soul Voice does not allow, Soul Voice wins. In particular, ignore these
Humanizer defaults: adding opinions, humour, asides or "mess"; first person in CV bullets; informal or
casual wording; letting tangents in; removing a number with its base; replacing the ad's required terms;
changing "helped" to "led" or a shared result to an individual one.

## One rewrite, two checklists (P-16, 2026-11-28)
Passes 2 and 3 below are applied in the SAME rewrite of the draft (one round trip): go through the Soul Voice
checklist and the Humanizer patterns together, Soul Voice winning every conflict, then record both in
`voice_review`. The order record stays `generate, soul_voice, humanizer, fact_verification`.

## Pass 2: Soul Voice (load once per task)
Load `skill_view(name="candidate-writing-voice")`, then its `references/voice-profile.md`,
`references/decisions.md` and `references/examples.md`, plus this skill's `references/voice.md`
(sector, C1 and anti-slop rules). In this pipeline you return ONE final version (the PM's envelope is the
"explicit request for one final version" in the voice skill's step 5); two variants only when the user
asks for them.
Check every letter or statement paragraph, the Summary and each bullet against the profile:
- Golden rule: the reader's need first, then the user's contribution to it.
- Professional, warm and direct; enthusiasm shown as willingness to contribute, not excitement.
- Familiar, precise words ("simplify the reporting process", not "streamline reporting").
- Short sentences with one idea, varied rhythm; never every paragraph built the same way.
- Confident when evidence supports it; no needless hedging; honest about the gap, once.
- One or two concrete examples, not lists; verified numbers with their base.
- Human layer (voice.md §4): one sentence that shows how he thinks or what he noticed.
- Personal anchor in the letter close: one real anchor (the place, the move, the commitment).
- The Industrial Engineer positioning (`identity.positioning_principle`): AI as support, never headline.

## Pass 3: Humanizer (load once per task)
Load `skill_view(name="humanizer")`. Use the Soul Voice files above as its **voice calibration sample**
(its "Voice Calibration" section): match that, not its default "opinionated" voice.
- Letter, statement and Summary: scan all 34 patterns, then do its final pass ("What makes this obviously
  AI generated?"), answer briefly in `voice_review`, and fix what remains.
- CV bullets: patterns 7 (AI vocabulary), 9 (negative parallelisms), 10 (rule of three), 14-16 (dashes,
  bold, inline headers beyond the 4-of-6 rule), 23-25 (filler, hedging, generic conclusions) and 33
  (opener tics). Bullets stay concise and factual.
- Never add a fact, a feeling or a detail that is not in the fact bank.

## Record it (required output; `bin/hcb task validate` rejects a draft or revision without it)
```json
"voice_review": {
  "order": ["generate", "soul_voice", "humanizer", "fact_verification"],
  "soul_voice": {"loaded": ["voice-profile.md", "decisions.md", "examples.md", "voice.md"],
                 "sector": "government | private | mining",
                 "changes": ["short note per change"]},
  "humanizer": {"loaded": true, "patterns_fixed": [9, 25, 31],
                "overridden_by_soul_voice": ["short note, e.g. kept no humour in the letter"],
                "remaining_tells": "brief answer to the final-pass question"},
  "naturalness_check": "pass | warnings: N (from hcb naturalness)"
}
```
`hcb naturalness` (in `bin/hcb engine run`) fails banned AI words and phrases and lists warnings
(repeated "approximately", "not X but Y", maxim endings, generic closers, opener tics, no human layer).
Fix the failures; fix warnings unless Soul Voice or an Engine rule says otherwise, and say why in
`voice_review`.
