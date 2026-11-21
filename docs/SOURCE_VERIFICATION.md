# Source verification (JH-TV-02), 2026-11-16

Method (read-only, honest client identity `HermesCareerBuddy-check/1.0`, no login, no browser-identity spoofing):
1. Careers URL found with `agent-reach web search` (Exa).
2. `robots.txt` read and evaluated for `User-agent: *` and AI-crawler groups.
3. One real read of the listing page with `agent-reach web read` (Jina/Exa) and a count of job-like lines.
4. Terms of use: web search for the big portals' scraping clauses (sources at the end).
Raw evidence: `state/source-check/` (search.jsonl, check.jsonl, robots-*.txt, pages/*.md).

Limit found: the free Exa/Jina tier paused reads after about 30 calls in a few minutes ("UPSTREAM_BROKEN, retry
later"). Paced reads (20-60 s apart) worked. Three runs a day over about 12 sources fits; a paid key is not needed yet.

## A. Direct reading OK (robots allow, listings visible in the read)
| Source | Listing URL | robots | Read |
|---|---|---|---|
| TSS Careers (Tas Gov) | careers.jobs.tas.gov.au (PageUp) | allowed | ok (confirm /cw/en/listing on first run) |
| Glenorchy City Council | jobs.gcc.tas.gov.au/job-search/ | allowed, crawl-delay 20 s | ok, vacancies listed |
| Devonport City Council | devonport.tas.gov.au/.../employment-opportunities/ | allowed | ok |
| ~~Hydro Tasmania + Entura~~ | careers.pageuppeople.com/901/ht/en/listing/ | **withdrawn 2026-11-16 (RT-15)**: content is served from hydro-tasmania-careers.careerpages.rec-marketing.dc2.pageuppeople.com, robots `Disallow: /` for `*` | was ok |
| Bell Bay Aluminium | bellbayaluminium.com.au/careers (-> Rio Tinto Workday) | allowed | ok |
| Nyrstar Hobart | jobs.nyrstar.com/go/Hobart/8739002/ | allowed | ok (risk flag stays) |
| Huon Aquaculture | huonaqua.com.au/careers/current-jobs/ | allowed | ok |
| TasRail | tasrail.com.au/current-job-vacancies | allowed | ok |
| SAGE Automation | careers.gotosage.com/jobs | allowed | ok, 17 jobs (mostly mainland: 8579 filter applies) |
| Hazell Bros | careers.hazellbros.com.au/jobs/search | allowed | ok |

Check added after RT-15: read robots.txt of the host that actually serves the listing and the job links
(Hazell -> hazellbros.elmotalent.com.au: allows `/careers/*/job`, so it is a `detail_hosts` entry).

## B. Page reachable but listings load in a hidden widget (reader sees only the shell)
Kingborough (applynow.net.au portal), Central Coast, TasNetworks, TasPorts, Marinus Link (Employment Hero),
Clarence (TechnologyOne). -> `search_discovery` now; the external portal URL can be tested later one by one.

## C. Blocks automated clients (robots.txt returns 403 to an honest bot identity)
City of Hobart (listings also on councilcareers.com.au), City of Launceston, Burnie, TasWater, Searson Buck.
-> No direct reading. `search_discovery` or email alerts.

## D. Not allowed for automated reading
| Source | Evidence |
|---|---|
| SEEK job pages | robots.txt: `Disallow: */job/` for all bots (AI bots too); SEEK-group terms (JobStreet) ban robots and scraping. Category listing pages are allowed by robots, but terms are the stronger rule. |
| LinkedIn | robots.txt: "automated means ... strictly prohibited", `Disallow: /` for `*` |
| Indeed | robots disallows /jobs/AU/; third-party summaries of its terms report a scraping ban; reader failed |
| UTAS careers | robots.txt `Disallow: /` for `*` |
| Incat | robots blocks ClaudeBot, GPTBot, CCBot and other AI crawlers site-wide |
-> Use only search-engine discovery (results pages) and email alerts, never direct reading.

## E. Readable, terms not confirmed (decide before enabling)
Hays (Hobart office page), Randstad (32 Tasmania jobs), Prosple (24 engineering grad roles), GradConnection
(now "SEEK Grad": SEEK-group terms likely apply). Workforce Australia stays off (Digital ID).

## Recommendation
1. **Enable group A now** as `page_read` with the cadences in config/sources.yaml (paced reads, honour crawl-delay).
2. **Email job alerts as the main channel for SEEK, LinkedIn, TSS/PageUp, councils and Prosple** (allowed by every
   portal, pushed within minutes, best for the 24 h goal). Needs read-only Gmail access: proposal P-3.
3. **search_discovery (Exa) for B, C, D and E** until P-3 is live. Caveat: a search index can lag hours to days,
   so it is a safety net, not the 24 h channel.
4. Never: logged-in or automated LinkedIn, SEEK `/job/` pages, UTAS direct, Incat direct, identity spoofing.

## Sources (terms)
- SEEK robots: https://www.seek.com.au/robots.txt ; JobStreet (SEEK group) terms: https://my.jobstreet.com/terms
- LinkedIn robots: https://www.linkedin.com/robots.txt
- Indeed terms summary (third party): https://conductatlas.com/platform/indeed/indeed-terms-of-service/provision/CA-P-028619/prohibition-on-scraping-automated-access-and-bot-activity/
- Hays terms: https://www.hays.com.au/terms-conditions (no scraping clause seen in excerpt; not confirmed)
- PageUp job-alert emails: https://blog.pageuppeople.com/faqs
- Tasmanian Government web copyright guidance: https://www.communications.tas.gov.au/channels/websites/copyright_and_disclaimer_notices_web_publishing
