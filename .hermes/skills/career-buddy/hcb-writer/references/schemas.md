# Engine input schemas (targets.yaml, content.json)

Taken from files that passed every Engine check (fit, verify, ATS, keywords) on 2026-11-14.
Field VALUES that are facts (name, contact, titles, orgs, dates, education, certifications) are copied
literally from `facts-digest.md`; never retype them from memory.

## targets.yaml (Pasada 1 input for `bin/hcb engine select`)
```yaml
application: "<Employer>, <Role> (<Location>)"
capabilities:            # ad requirements -> capability tags (vocabulary below), weight 3 central, 2 duty, 1 support
  process-improvement: 3
  excel: 3
prefer:                  # force an OUT unit in, with reason (also used to break EMPATE)
  - ecyt_excel_business_report   # reason
exclude:                 # keep a unit out, with reason
  - ecyt_uml_with_programmer     # reason
max_per_role: {origin: 4, australia: 2, concurrent: 0}   # change only with a written reason
bullet_budget: 12        # optional; change only with a reason
keywords:                # 15-25 rows, literal ad words; checked by keyword_check.py
  - keyword: "continuous improvement"
    weight: 3
    status: cv           # cv | letter | demonstrated | gap | excluded
    match: ["continuous improvement"]      # literal forms that count
    evidence: [catercare_documentation]
    synonym_of: "<literal wording in the cited fact>"   # REQUIRED if the keyword is not in the fact
    kind: tool           # only for tools: never covered by synonym
  - keyword: "Lean"
    weight: 1
    status: gap
    reason: "No verified Lean practice; standardised work only."
# Free-text planning fields are allowed and useful for the Recruiter:
sales_thesis: "..."
professional_title_branch: credential-led | capability-led
professional_title_reason: "..."
transferable_map: {cater_care: "...", panorama: "..."}
```

### Capability tag vocabulary (from `select_evidence.py --tags`, 2026-11-14)
documentation reporting data-management costing excel logistics automation process-improvement
cost-analysis leadership process-mapping process-design stakeholder-support budget-monitoring
margin-analysis pricing stakeholder-communication data-analysis commercial-judgement database
requirements-specification accuracy knowledge-transfer standardised-work financial-modelling
time-saving financial-tracking cost-reduction decision-ownership root-cause supply-chain
market-intelligence governance program-coordination business-intelligence stakeholder-translation
systems-analysis system-administration supplier-management invoicing training data-quality onboarding
procedure-control resilience site-work bpmn decision-analysis public-value option-appraisal
feasibility-analysis user-research discipline build-vs-buy vendor-evaluation data-access solution-gaps
process-analysis business-case vendor-management infrastructure-cost monitoring project-delivery
status-reporting recruitment team-building interviewing people-management agile scrum stand-ups
team-communication project-management-practices team-coordination delegation process-documentation
role-design initiative uml inventory customer-validation revenue-growth adaptability digitalisation
systems-implementation sales-analysis data-driven-decisions cash-flow year-on-year-analysis
self-directed-learning systems-integration error-reduction verification reconciliation cash-handling
daily-records compliance cost-structure traceability risk-reduction continuous-improvement
stakeholder-buyin safety-compliance whs regulated-environment self-management regulatory-compliance
compliance-analysis policy-analysis environmental stakeholder-analysis sustainability dcf capm
project-evaluation sensitivity-analysis risk-analysis weighted-scoring layout-design material-flow
industrial-engineering safety-by-design capacity-planning mass-balance quantitative-analysis
cost-engineering capital-costing budget-modelling quality-assurance sampling-plan quality-control
waste-management babok business-analysis innovation prototyping multidisciplinary-teamwork
business-modelling mvp market-validation go-to-market-testing selection-under-competition coordination
large-group-management performance-under-pressure precision technical-training academic-performance
competitive-selection warehousing working-under-pressure rapid-adaptation systems-thinking ai-tooling advisory
(The facts digest lists each evidence unit's tags: prefer tags that real units carry.)

## content.json (Pasada 2 output; fit.py renders md/html/docx/pdf from it)
```json
{
  "application": "<same as targets.yaml>",
  "generated": "14 November 2026",
  "title_branch": "credential-led | capability-led",
  "name": "JUAN MUNOZ",
  "identity_line": "Industrial Engineer",
  "capability_nouns": "Noun One | Noun Two | Noun Three",
  "contact_line_1": "<location_line> (willing to relocate to <city>) | <phone> | <email>",
  "contact_line_2": "<working_rights or working_rights_display>  [| driver licence display if relevant]",
  "professional_summary": "<= 55 words; **keyword** highlights only for status cv",
  "skills": [{"label": "Reporting", "terms": "Excel | Power BI | Progress reports"}],
  "experience": [
    {"title": "<title_on_documents>", "org": "<employer_display>", "dates": "<display_dates>",
     "context": "optional italic line, never self-diminishing",
     "page_break_before": false,
     "concurrent": [{"label": "Concurrent, part time", "title": "...", "org": "...", "bullets": []}],
     "bullets": [
       {"text": "15-25 words, result first.", "evidence": ["<evidence ids from selection.json>"]},
       {"headline": "Build versus buy", "text": "rest of the bullet...", "evidence": ["ecyt_keepa_buildvsbuy"]}
     ]}
  ],
  "education": ["<from facts-digest Credentials, display form>"],
  "certifications": ["<only those relevant to the role, max 2 lines>"],
  "letter": {
    "date": "14 November 2026",
    "addressee": ["Recruitment Team", "<Employer>"],
    "salutation": "Dear Recruitment Team,",
    "paragraphs": [
      {"text": "Thesis paragraph..."},
      {"text": "Role understanding..."},
      {"heading": "<criterion theme from the ad>", "text": "Explicit claim + proof..."},
      {"text": "Gap once + closing evidence (max two sentences)..."},
      {"text": "Personal anchor + thanks + availability."}
    ],
    "signoff": "Kind regards,",
    "signature": "The user"
  },
  "statement": {"date": "...", "title": ["Selection Criteria Statement", "<role>, <team>, <employer>"],
                "criteria": [{"heading": "<literal criterion>", "text": "220-300 words, STAR order",
                              "star": {"situation": "<excerpt of text>", "task": "<excerpt>",
                                       "action": "<excerpt>", "result": "<excerpt>"}},
                             {"heading": "Highly regarded", "block": "highly_regarded", "text": "short"}]}
}
```
`statement` only when the portal asks. Experience order is imposed by the Engine (`order.js`), but
write it Chile first anyway. Extra keys (e.g. `test_only`, `version_label`) are ignored by the renderer.
