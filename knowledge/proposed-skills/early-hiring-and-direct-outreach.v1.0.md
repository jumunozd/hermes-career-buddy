---
name: early-hiring-and-direct-outreach
description: Research skill for identifying early hiring signals, researching Tasmanian-compatible employers, verifying professional contacts, and preparing evidence-based outreach briefs for Hermes Career Buddy.
owner: research-agent
project: Hermes Career Buddy
version: 1.0
status: proposed-for-integration
language: en-AU
---

# Skill: Early Hiring Intelligence & Direct Outreach Research

## 1. Purpose

Find credible, relevant employment opportunities **before or alongside formal job advertisements** by monitoring early hiring announcements, organisational expansion, and workforce demand signals. Convert those signals into verified, actionable research briefs and Baserow records for the Career Development OS.

**This skill researches and recommends; it does not draft final outreach on behalf of the Recruiter Agent, contact people, apply for jobs, or send messages.**

## 2. Operating context

- Candidate: an Industrial Engineer assessed by Engineers Australia, actively seeking a professional foothold in Australia.
- Immediate geography: opportunities must permit the candidate to **work physically from Tasmania**. Prioritise hybrid roles based in Tasmania, then remote roles performable from Tasmania, then onsite Tasmania roles. A modest hybrid preference is a bonus, not an exclusion criterion.
- Relevant role families: industrial engineering; continuous improvement; process improvement; operations and production; maintenance/production planning; asset management support; engineering/project support; reliability and operational systems; graduate, trainee, internship and entry pathways; adjacent transferable-skills roles.
- Prioritise practical engineering and operational exposure rather than treating standalone AI-agent work as the primary career target.
- This is a **supplementary research channel**, not a replacement for the Job Hunter's official vacancies workflow.
- Use the project's current source files, role-target list and Master Specification as the authoritative source of detailed targeting rules. If they differ from this summary, escalate the conflict to the Project Manager rather than silently overriding either.

## 3. Triggers and schedule

1. **Friday scheduled research:** survey early-hiring signals and broader employment developments; feed the established Friday research output and Saturday Project Manager review.
2. **On-demand investigation:** research a company, named hiring announcement, industry development, or potential contact when requested by the Project Manager, Job Hunter or candidate.
3. **Time-sensitive discovery:** when the Job Hunter or another authorised workflow detects a recent, relevant hiring post, the Research Agent should validate and hand back findings promptly rather than waiting until Friday.

**Ownership boundary:** The Job Hunter remains responsible for weekday vacancy discovery, vacancy fit scoring and its current top-target and exploratory outputs. Research Agent focuses on underlying companies, hiring evidence, people and approach opportunities. Do not set up a second uncontrolled job scraping pipeline.

## 4. Signal taxonomy

### A. Fresh direct hiring announcements — highest urgency

Look for messages from organisations, hiring managers, engineering leaders and recruiters such as “we're hiring”, “joining our team”, “expanding our operations”, “looking for engineers”, “graduate opportunity”, and equivalents relevant to the target role families.

- **Priority trigger:** published within the last 24 hours.
- **Secondary trigger:** 2–7 days old, where the opportunity appears open.
- **Optional low-engagement clue:** fewer than 100 likes, when visible. This is **not** a qualification requirement or a proven measure of competitiveness.
- Record the original post URL, author, date, relevant text and any employer-specified application instructions.
- Do **not** recommend ignoring a mandated careers portal or application form. Use the official route and, where appropriate, propose a respectful supplementary introduction.

### B. Expansion and workforce-demand signals

Find verifiable signals that may precede recruitment:

- announced plant expansion, new production lines, mine or industrial investment;
- awarded contracts and new project mobilisation;
- new engineering, maintenance, infrastructure or renewable energy projects;
- grant or funding announcements linked to local headcount or operations;
- creation of a new site, shift or operations team;
- relevant graduate, internship and early-career intakes.

For startups, funding rounds may be a useful lead, but **a funding event alone is not proof of hiring**. Explain the plausible job-related impact and look for corroboration.

### C. High-fit proactive employer research

For Tasmania-relevant industrial, energy, mining, manufacturing, logistics, utilities, infrastructure, engineering consulting and operational employers, investigate plausible teams and entry points even without an advertised vacancy. Distinguish “speculative approach candidate” from “confirmed job vacancy”.

## 5. Source and verification rules

Prefer employer careers pages, verified company announcements, public hiring posts, official project announcements and reputable sector publications. LinkedIn posts can indicate an opportunity but should be checked for authenticity and relevance.

For each claim record:

- source URL;
- publication/observation date and research check date;
- source type (official, public professional post, reputable secondary or unverified);
- specific hiring evidence;
- whether the vacancy or opportunity is **confirmed**, **inferred** or **unverified**.

Never create a company vacancy, job title, hiring manager relationship, email address or recruiting intention from assumption. If evidence is inconclusive, say so.

## 6. Contact discovery

Research the **most appropriate professional contact** for each opportunity, in this order where relevant:

1. Person who published the hiring announcement or employer-nominated contact.
2. Hiring manager responsible for the relevant engineering/operations team.
3. Publicly identified internal recruiter or talent acquisition contact.
4. Relevant department manager or team leader.
5. Official careers/general recruitment contact as a fallback.

Record the person's name, current title, employer, why this person is relevant, a public source proving the link, and the source's observation date.

**Contact rules:**

- Use employer-published professional contact details or other clearly authorised public business channels.
- Do not scrape hidden personal data, collect private addresses, guess an email pattern and present it as verified, or use bulk harvested contact lists.
- Do not circumvent access controls, platform restrictions, consent requirements or anti-spam obligations.
- If the exact email address is not published, record `email_status: not_verified` and provide the verified public alternative (careers portal, professional LinkedIn profile, recruitment inbox, contact page).
- Do not assume that a LinkedIn profile proves a person is the hiring manager for a specific role.

## 7. Candidate relevance and fit

Evaluate using the Career Development OS's existing fit rules and role list; **do not replace Job Hunter's A–H scoring framework**. Provide a concise research-level rationale describing:

- relevance to industrial engineering, continuous improvement, process or operations engineering;
- suitability for a candidate entering the Australian engineering labour market, including transferable operational experience;
- feasible location and work arrangement from Tasmania;
- whether entry-level, graduate, trainee or internship access is realistic;
- explicit hard requirements and missing or uncertain information;
- why now may be a relevant moment to approach the organisation.

Geography is a gate: interstate positions should not be treated as viable merely because a website says “remote”. Confirm that working from Tasmania is accepted or mark it `location_unverified` for follow-up. Do not impose a requirement to work from Chile; that is a separate, longer-term objective.

## 8. Research brief: mandatory fields

For every recommended lead supply:

```yaml
company: ""
sector: ""
location: ""
work_arrangement: "hybrid | remote-from-Tasmania | onsite-Tasmania | unknown"
location_eligibility: "verified | unverified | incompatible"
signal_type: "fresh_hiring_post | expansion | investment | project | internship | proactive_employer"
signal_summary: ""
signal_date: "YYYY-MM-DD or unknown"
first_seen_at: "YYYY-MM-DD"
source_urls: []
evidence_status: "confirmed | inferred | unverified"
opportunity_type: "advertised_vacancy | early_hiring_signal | speculative_outreach"
role_family: ""
fit_rationale: ""
hard_requirements_or_unknowns: []
contact_name: ""
contact_title: ""
contact_source_url: ""
professional_email: ""  # blank unless publicly verified
email_status: "verified_public_business | not_verified"
alternative_contact_url: ""
recommended_action: "apply_formally | research_further | propose_outreach | discard"
urgency: "high | normal | low"
why_now: ""
personalisation_evidence: []
duplicate_check: "clear | existing_record | unresolved"
owner_for_next_step: "job-hunter | recruiter | project-manager"
```

Only populate fields with verified or clearly labelled inferred facts. Do not manufacture a fit percentage if the scoring owner has not calculated one.

## 9. Baserow integration and deduplication

Baserow is the **single source of truth** for leads, contacts, statuses, documents and follow-ups. Use the existing authorised Baserow schema and API; do not create a parallel spreadsheet, CRM, contact database or new Baserow tables without Project Manager approval.

Before suggesting a new record:

- match employer, role, location and source URL against vacancies and existing outreach leads;
- check whether the contact already exists, whether the candidate has applied, and whether outreach is pending/completed;
- update an existing record when this is an additional hiring signal about the same opportunity;
- preserve original sources, date history and ownership;
- flag unresolved duplicates rather than blindly inserting another record.

If a required schema field is missing, raise a specific schema-change request; do not improvise an unauthorised structural change.

## 10. Handoff contract between agents

**Research Agent → Job Hunter:** A genuine advertised vacancy found through a hiring post, with the official application URL and verified evidence. Job Hunter handles full A–H fit and its normal ranked pipeline.

**Research Agent → Recruiter Agent:** A validated employer/contact and personalised **research brief**, not a ready-to-send message. Include:

1. **Reason for contact:** public signal and why it matters now.
2. **Candidate-to-employer connection:** concrete, defensible transferable skills and relevant target role.
3. **Personalisation anchors:** 1–2 sourced facts about a project, operational challenge or company priority.
4. **Proposed ask:** inquiry about a relevant role, internship or short conversation, matched to the evidence.
5. **Contact route:** verified professional email or approved alternative.
6. **Restrictions/uncertainty:** official application process, missing contact details, location eligibility, evidence confidence.

**Recruiter Agent / Writer:** Own message composition, using the separately maintained **The user Writing Voice Skill**. For the short direct outreach variant, aim for approximately **3–5 short lines** of body text, using natural Australian English, concise personalisation, a clear purpose and one low-friction request. This is a design choice inspired by the Reddit case, not a verbatim email template from its author. Do not fabricate familiarity, achievements, job openings or referrals.

**Candidate approval:** All outbound emails, DMs and applications require explicit candidate review and approval. Research Agent must never send.

**Project Manager:** Own cross-agent prioritisation, weekly review, alerts, and follow-up rules. Preserve the established 10-day follow-up recommendation unless an explicit updated rule overrides it; the Recruiter Agent should not independently send repeat emails.

## 11. Output and prioritisation

For the weekly research handoff, provide:

- **Top 3–5 validated early outreach opportunities**, ranked by fit, evidence strength, freshness and Tasmania feasibility;
- a separate **emerging / exploratory** section for promising but unconfirmed signals;
- any **urgent fresh post** that may expire before the weekly cycle, sent through the established Project Manager notification mechanism;
- contacts requiring verification, formal-application requirements and duplicate/existing-application notes;
- a short description of what changed since the previous review.

If no opportunities meet the standard, report zero validated leads rather than padding the list. Do not claim a specific company is recruiting without evidence.

## 12. Quality gate — complete before handoff

- [ ] Company and source are authentic.
- [ ] Freshness and relevance are recorded accurately.
- [ ] Tasmania work eligibility is verified or explicitly marked uncertain.
- [ ] Hiring evidence is classified correctly (confirmed vs inferred vs speculative).
- [ ] Appropriate professional contact is connected to a cited public source.
- [ ] No guessed personal contact details or fabricated facts.
- [ ] Existing Baserow records checked; no duplicate generated.
- [ ] Research brief includes a defensible reason to contact **this organisation now**.
- [ ] The formal employer application route is respected.
- [ ] Owner of next action is explicit; no automatic outbound communication.

## 13. Measurement and iterative improvement

Start with this minimal workflow. Do not add new scraping services, contact-enrichment subscriptions, agent frameworks or automated email sending until validated need justifies them.

Track, using existing Baserow data where possible:

- validated leads discovered;
- leads with verified Tasmania work eligibility;
- leads accepted by Job Hunter or Recruiter;
- outreach approved and sent by the candidate;
- replies, conversations/interviews and subsequent outcomes;
- invalid signals, duplicates, contacts unavailable and time spent researching.

Review what actually generates useful conversations. Adjust thresholds and lead types based on observed outcomes, not the original Reddit author's claimed results.

## 14. Provenance and interpretation

**Original inspiration:** Reddit, `r/bangalorejob`, *I got 4 job offers with one simple method*, posted 11 November 2026: https://www.reddit.com/r/bangalorejob/comments/1xtc96l/i_got_4_job_offers_with_one_simple_method/

The post recommends noticing LinkedIn hiring announcements less than 24 hours old (and under 100 likes), emailing a relevant person directly in fewer than five lines, and following seed funding news. It reports four job offers but provides no independently verified controlled comparison or proof that these thresholds predict success. The author said a separate explanation of email wording would follow; **the skill must not attribute the example copy or detailed email structure to the original Reddit author**.

**Adaptations made for Hermes Career Buddy:** Tasmanian location gate, industrial-engineering targeting, Baserow single source of truth, cross-agent division of responsibility, official-application compliance, public professional-contact verification, manual outreach approval, and conservative evidence confidence.

## 15. Integration acceptance tests

1. A new Tasmanian employer hiring post appears with a public HR email: provide source, validated contact, proposed next owner and Baserow duplicate check; do not send.
2. A mining company announces plant expansion but no vacancies: classify as `early_hiring_signal` or `speculative_outreach`, not a confirmed position.
3. A role says remote but the employer only accepts NSW staff: mark incompatible for the present Tasmania job search.
4. An engineer's LinkedIn profile exists with no public email: offer the verified profile or employer contact page; leave email blank.
5. The same job appears on LinkedIn and the company careers site: reconcile into one Baserow opportunity with both sources.
6. The company requires applications via its careers portal: hand the vacancy to Job Hunter and propose any supplementary outreach only if appropriate.
7. The candidate has already contacted the company: surface Baserow status; do not recommend another introductory email.
8. No credible leads found: report zero and explain the search coverage rather than inventing prospects.

**Definition of done:** The agent can reliably produce sourced, deduplicated, Tasmania-compatible outreach research briefs and route each brief to the correct agent while retaining user control over every external communication.
