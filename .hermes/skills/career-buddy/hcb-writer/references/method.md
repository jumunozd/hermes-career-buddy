# Writer method pack: CV, cover letter, selection criteria

Distilled 2026-11-14 from the Job Application Engine: `rules/cv.md`, `rules/cover-letter.md`,
`rules/template.md`, `voice/precedence.md`, `FEEDBACK_2026-10-21_taswater.md` (the user's instructions)
and `AGENTS.md`. This replaces reading those files one by one. If a rule here and the Engine ever
disagree, the Engine wins and this pack must be refreshed (`knowledge/SOURCES.md`).
Facts are NOT here: they are in `facts-digest.md` (generated). Never write a fact that is not there.

## 0. Hard rules (verify.py / fit.py enforce most of them)
- Name "The user", never accented. Zero em dashes anywhere. Australian English
  (organise, standardised, recognised, licence noun, programme, centre).
- Never invent a figure, date or title; never round or "improve" one. Missing -> Missing Fact Request.
- Approximate figures carry "approximately" or "around". Every percentage carries its base in the
  same sentence. Never add overlapping groups (Panorama training: ~15 trained, ~5 on the system).
- No first person in CV bullets (letter: yes). No empty adjectives or self-labels: magnitudes persuade.
- De-inflation: every noun phrase must survive "what exactly was it?".
- Titles, dates and fixed phrases come only from `facts-digest.md` roles; never a title the user did not hold.
- Prohibited patterns and attribution rules: see `facts-digest.md` §Prohibitions. They block delivery.
- CV max 2 pages, letter max 1 page, selection criteria statement max 2 pages: enforced by code.

## 1. Pasada 1: analysis and selection (nothing is drafted before this exists)
1. Classify the employer -> voice sector (`voice.md`): government/GBE/council/utility/critical
   infrastructure/health/education -> government voice; private/tech/consulting/mining -> private voice.
2. Keyword table, 15-25 rows, LITERAL words of the ad (never paraphrased). Source weight, high to low:
   job title and selection criteria > PD duties > terms repeated 3+ times > desirables.
   Clusters: domain, process, risk/reliability, stakeholder, behavioural. It lives in `targets.yaml` `keywords`.
3. Match Depth per keyword:
   | Depth | Meaning | Use |
   |---|---|---|
   | Direct | same or very similar work | may open the CV; written as direct |
   | Transferable | similar work, other context | always with its context; NEVER written as Direct |
   | Adjacent | exposure, coursework, certification | one line, Skills or Certifications |
   | Gap | no defensible evidence | out of the CV; letter only, once |
4. Write `targets.yaml` (`schemas.md`): ad -> capability tags with weight 1-3; then
   `bin/hcb engine select --folder <v>`. Draft ONLY from IN units of `selection.json`. A tie (EMPATE)
   is resolved with `prefer`/`exclude` plus a written reason. To use an OUT unit, add it to `prefer`.
5. **Transversal pattern** (The user, 2026-10-21): find the ad sentence describing the ideal candidate;
   if a pattern repeats across several roles in the facts, it goes in the capability line, the first
   Summary sentence and the letter thesis. Count roles honestly ("in three different businesses").
6. **Sales thesis** (Chile first):
   a. For each essential criterion, look for evidence FIRST in `block: origin` roles (Chile).
   b. For each `block: australia` role: one line naming the ad skill it proves; that skill titles its bullets.
   c. One sentence: "<role and scope in Chile> plus <transferable skills proven in Australia> fit
      <ad role> because <main criterion>." Summary and letter thesis are written from it.
   d. Gaps: criterion with no evidence anywhere = gap; named once, end of the letter, max two sentences.
7. Professional Title branch (§3) and why. 8. All questions for the user together, in one message (to the PM).

Ad vs Position Description: the ad is the main grid; the PD gives literal vocabulary and "Challenges"
for the letter's role-understanding paragraph. Record the PD date; if older and different, assess
against the ad and note the difference.

## 2. Keywords and synonyms (The user, 2026-10-26: using the ad's keywords is a priority)
A synonym of a fact is allowed to match the ad's keyword if ALL hold:
1. It names the same thing that happened, same scope.
2. It does not raise title, seniority, ownership (initiated -> built), frequency (on request -> monthly),
   scale or formality (signed log -> audit programme).
3. It is not a tool (Power BI, SQL, SAP...: only if literal in the facts; `kind: tool`).
4. It does not touch a job title. 5. It is not in the prohibitions / `never_with`.
Register each one in `targets.yaml` with `synonym_of` = literal wording from the facts. Keywords with
evidence go to the CV with the ad's word; soft skills are `demonstrated` (proved, never labelled);
`gap`/`excluded` always carry a reason. Highlight `**keyword**` only for status `cv`, max 2 per bullet.

## 3. Professional Title
Does the ad require an engineering degree, engineering work or technical analysis?
- Yes (Engineer, Analyst, Project Engineer): credential-led. `Industrial Engineer | <2-4 capability nouns>`.
- No (Officer, Coordinator, Administrator, Technician): capability-led, in the role's own vocabulary,
  e.g. `Operations and Reporting | Process Documentation and System Administration`. The credential moves
  to Education and a supporting clause of the Summary (never hidden or denied). Overqualification rule
  is a working hypothesis (one recruiter, July 2026): record where it is applied.
The identity line in the page 2 footer must match header line 2.

## 4. CV structure and budgets (the 7-second rule; 11 bullets is the reference CV)
Order (fixed): header, contact band, PROFESSIONAL SUMMARY, SKILLS, PROFESSIONAL EXPERIENCE (page 1);
experience continued, EDUCATION, CERTIFICATION (page 2). REFEREES only if the ad/portal asks.
| Element | Budget | Enforced by |
|---|---|---|
| Summary | max 55 words, 3 lines | fit.py (fails) |
| Skills | 3 lines, max 4 terms each, " \| " separated, NAMES ONLY | fit.py (fails) |
| Bullet | 15-25 words | fit.py (fails > 25, warns < 15) |
| Bullets total | max 12 | fit.py (trims by relevance) |
| Bullets per role | Chile 4, Australia 2, other international 1, concurrent 0 | select_evidence.py |
- Header: name, location (+ "willing to relocate to <city>" when relevant), phone, email, working rights,
  driver licence only if the role involves travel/field work. Values in `facts-digest.md` §Identity.
- Summary formula: (1) professional base in Chile with role, scope, years ("around three years",
  2019-2022; concurrent roles add no years); (2) transferable skills proven in Australia, naming the
  current job; (3) fit with the role. Opens with what he did, not a label. Employer named at most once,
  in the closing sentence. Max one learning-target sentence. If the main essential is Transferable, the
  first sentence asserts it with facts.
- Skills: every term must have a backing bullet in Experience; never repeat evidence sentences there;
  never learning targets.
- Experience: ONE heading. Blocks: Chile (`origin`) first, then Australia, then other international in
  one compact line. Inside a block: most relevant first, ties reverse-chronological. Country on each role
  line. Concurrent part-time roles nest under the main role ("Concurrent, part time"), no own dates.
  Result in the first words of a bullet; evidence closes the same bullet; low-relevance periods compress
  to one line. Context lines never self-diminishing ("currently working operationally on days off" is banned).
- Bullet shape: at most 4 of 6 bullets with `**Headline:** verb-result-method-evidence`; at least 2 in
  plain prose; no two bullets open the same way. Headlines name the concrete thing ("Build versus buy"),
  not a category ("Cost Reduction").
- The most relevant role must be on page 1 or opening page 2. The first Australian role usually carries
  `page_break_before: true`. No role block splits across pages.
- Hiding dates or the current job is never allowed: order changes framing, not facts.

## 5. Cover letter (proves fit and understanding; the CV proves capability)
Five layers, max one page, first sentence short, no sentence over ~35 words:
1. **Thesis**: short identity (what he is), credibility anchors, a specific fit thesis for THIS role.
2. **Role understanding**: who uses the role's output, which decisions depend on it, the risk context.
   About the employer's world, never meta-comment about the letter.
3. **Body mirroring criteria**: 3-4 headings taken from the ad (natural wording, core vocabulary kept),
   one paragraph each. **Explicit criterion statement**: for each essential with Direct/Transferable
   evidence, name the criterion in the ad's words and assert it, then prove it next sentence.
   Transferable form: "My <criterion> experience comes from <roles>." Chile first; Australia as proof of
   transfer ("Since moving to Australia I have applied the same <skill> to <fact>").
4. **Quantified evidence**: magnitudes, not adjectives; same number rules as the CV.
5. **Non-replicable close**: one real personal anchor (local presence in Tasmania, life decision,
   long-term commitment), professional, linked back to the work; brief thanks and availability.
- Gap: named ONCE, after the body, before the close, max two sentences: the gap + real gap-closing
  evidence (a case where the user entered a domain cold and became reliable). Include ALL critical missing
  domains; never in the first paragraph; no own heading.
- Values: demonstrated with facts; at most ONE literal employer value, anchored to a fact (record it).
- Addressed to a name or team; never "To Whom It May Concern". Date = generation date.
- Letter and CV never contradict any fact, figure or phrase. The letter compresses, never stretches.

## 6. Selection criteria statement (only when the portal asks)
`statement` block in content.json. Without portal format: separate doc, max 2 pages, one heading per
criterion with the LITERAL ad wording, 120-180 words per criterion, a short final block for
"highly regarded". Each criterion = one concrete case (situation, action, result), first person,
Chile first, may use evidence the CV left out. Degree criterion: the Engineers Australia skills
assessment project (`ea_skills_assessment`), always as team work. Gaps once, in the desirables block.

## 7. Verification
Automatic (must be green before judgement): `bin/hcb engine run --folder <v>` = fit.py + verify.py +
ats_check.py + keyword_check.py; `engine_unchanged` must be true.
Judgement, only these five:
1. Every Skills term has its backing bullet; no evidence sentence duplicated between Skills and Experience.
2. Every achievement bullet has its full chain, evidence closing the same bullet.
3. De-inflation: every noun phrase survives "what exactly was it?".
4. No Transferable written as Direct.
5. Nothing would fail an interview defensibility test.
Letter extras: every essential criterion has a paragraph; each paragraph has a verifiable fact with a
magnitude; the gap is named once with closing evidence; the close says something only the user could say.

## 8. Delivery notes for the PM (the user's instructions)
- If the ad names a hiring manager with a contact, recommend the user calls before applying and suggest
  2-3 concrete questions (see the daily digest call suggestion). The system never calls.
- If the ad is a republication, flag it and check the new version avoids the earlier weaknesses.
- SEEK and similar may auto-fill "current role" from the first CV entry: tell the user to check that field.

## Final rule
Between a stronger claim and a truer one, the truer wins. Between two equally true claims, the one
that sells wins: make transferable skills visible in the ad's words, say where they come from.

## Rules v2 (P-9, approved 2026-11-20): use for every new CV
- Set `"rules_version": "v2"` in content.json. Full rules: `engine/rules/cv.md`, section "Reglas v2".
- Write the bullets first; write the **summary last, as the hook for this offer**: first sentence = what the
  role needs (ad words) + the strongest matching proof; up to 90 words with 2-3 measured results and one
  target line. Fill `summary_claims` (each claim -> the evidence/credential ids that prove it below).
- Evidence without an employer (`role: null`, e.g. a personal AI project) goes in `projects`, keeping its
  `attribution_rule`. Optional `experience_headings` per block. Skills up to 8 terms per line.
- Percentages derived from a verified before/after pair: always with the base, "approximately".
- Ended roles in the past tense; keep the availability line; an aim (gap keyword) goes in the target line,
  never in the capability line.
- Layout: use `"layout": "compact"` and `"bullet_headlines": false` by default (the user, 2026-11-20); keep each employer line short enough for one line.
