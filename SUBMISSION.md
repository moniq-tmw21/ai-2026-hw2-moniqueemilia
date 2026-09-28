# HW2 submission

**Name:** Monique-Emilia-Tumewu  
**Student ID:** 26078852  
**Group:** AI-Eng-8  
**Repository:** https://github.com/moniq-tmw21/ai-2026-hw2-moniqueemilia

## AI tool disclosure

State which AI tools you used and for what. Expected and fine; undisclosed use
is not. If you used a model to help you draft a prompt, say which prompt.

>I used ChatGPT to help me understand the assignment requirements, draft and refine prompts, debug the Python programs, and check whether my implementations followed the README instructions. In Sublab Easy, ChatGPT helped draft the role prompts and program structure. In Sublab Medium, ChatGPT helped draft the conversation-memory and compression prompts, JSON validation logic, token tracking, and failure handling. In Sublab Hard, ChatGPT helped draft the extraction and scoring prompts, extraction schema, validation logic, and Python weighted-score calculation. I reviewed and tested the generated code in my local environment.

---

## Sublab Easy — one task, four roles

### Decisions per role

**Run status:** The experiment could not produce model responses because every API request returned `429 insufficient_quota` (`credit_balance_exhausted`). Therefore, the results below are marked as unavailable rather than filled with fabricated model outputs.

One row per enquiry. In each cell write the `decision` your run returned, and whether it agrees with `expected` in `data/enquiries.json`:

| Enquiry | policy_officer | front_desk | auditor | bilingual_clerk |
|---|---|---|---|---|
| E-01 | N/A | N/A | N/A | N/A |
| E-02 | N/A | N/A | N/A | N/A |
| E-03 | N/A | N/A | N/A | N/A |
| E-04 | N/A | N/A | N/A | N/A |
| E-05 | N/A | N/A | N/A | N/A |
| E-06 | N/A | N/A | N/A | N/A |
| E-07 | N/A | N/A | N/A | N/A |
| E-08 | N/A | N/A | N/A | N/A |
| E-09 | N/A | N/A | N/A | N/A |
| E-10 | N/A | N/A | N/A | N/A |
| **agrees with `expected`** | N/A | N/A | N/A | N/A |
| **parsed** | N/A | N/A | N/A | N/A |
| **schema-valid** | N/A | N/A | N/A | N/A |

The agreement, parsing, and schema-validity rates could not be measured because no model response was returned.

### Which field moved, on which enquiry, under which role

| Field | Enquiries that moved | Role(s) that moved it |
|---|---|---|
| `found` | N/A | N/A |
| `decision` | N/A | N/A |
| `amount` | N/A | N/A |
| `missing_documents` | N/A | N/A |

No valid field-movement comparison could be made because the API calls produced no model responses. The program printed no detected movements because `None` responses were skipped; this is not evidence that the fields were stable across roles.

### Raw replies

Paste the full reply for **one enquiry where a role changed the decision** away from the policy officer's:

```text
N/A — no model reply was produced because the API request returned 429 insufficient_quota (credit_balance_exhausted).

```
Paste the full reply for **E-07 (the Kazakh enquiry)** from the bilingual clerk, so the `reason` language is visible:

```text
N/A — no model reply was produced because the API request returned 429 insufficient_quota (credit_balance_exhausted).
```

### Written answers

**1. Which fields are role-sensitive and which are not?** Point at rows in your
tables.

> I could not determine which fields were role-sensitive from the actual run because the API returned no model responses. Therefore, the `found`, `decision`, `amount`, and `missing_documents` rows are all marked N/A in my comparison table. The experiment would normally compare these fields across the four roles while keeping the enquiry and underlying records unchanged.

**2. Which enquiries are most sensitive to the role, and why those?** Say what
E-03, E-04, E-07 and E-10 are each testing.

> The actual role sensitivity could not be measured because the API calls failed. However, these enquiries are designed to test different pressure points in the role prompts. E-03 tests whether the model follows the official record instead of accepting an applicant's claim. E-04 tests how the role handles an applicant who does not satisfy the policy requirements. E-07 tests bilingual handling and whether the bilingual clerk can respond appropriately while preserving the same structured decision logic. E-10 tests whether changing the role causes the model to apply discretion differently instead of consistently following the supplied policy and records.

**3. Where does discretion belong — the role paragraph, or code that reads
`decision` afterwards?** Say what a downstream program can and cannot tell
about which role produced a record.

> The role paragraph can guide the model's tone, priorities, and behavior, but important decision rules should not depend only on prompt wording. A downstream program that only reads the `decision` field can see the final value, but it cannot reliably know why that decision was produced or which role influenced it unless role information is stored separately. If a decision has important consequences, the program should validate it against explicit policy rules and trusted record data instead of assuming that the role prompt enforced the rules correctly.

**4. Is a role a boundary?** Say in Week 2 terms what the role paragraph is
made of, and what you would put in code — not in the prompt — if a wrong
`decision` were expensive.

> A role is not a security or correctness boundary. The role paragraph is part of the model's prompt context and instructions, so it can influence the output but cannot guarantee that the model will always follow a rule. If a wrong `decision` were expensive, I would put the important checks in deterministic code: validate the JSON schema, verify the applicant against the official records, apply the eligibility rules in code, reject invalid or inconsistent outputs, and log the result for review. The prompt can guide the model, but the final enforcement should be outside the model.


---

## Sublab Medium — memory you choose

**Run status:** The API returned `429 insufficient_quota` (`credit_balance_exhausted`) for every model request. The program still recorded local token estimates for the attempted calls, but compression, assistant replies, and probe answers could not be produced. Therefore, the token values below should not be interpreted as the result of a successful compression experiment.

### Tokens per call

| Call | A — never compressed | B — compressed at the `compress` turn |
|---|---|---|
| 1 | 845 | 845 |
| 2 | 862 | 862 |
| 3 | 877 | 877 |
| 4 | 892 | 892 |
| 5 | 908 | 908 |
| 6 | 927 | 927 |
| 7 | 949 | 949 |
| 8 | 973 | 973 |
| 9 | 994 | 994 |
| 10 | 1010 | 1010 |
| 11 | 1019 | 1019 |
| 12 | N/A | N/A |
| **peak** | 1019 | 1019 |
| **total for the run** | 10256 | 10256 |

Call 12 is marked N/A because `data/chat_script.json` contains 11 applicant messages plus the `<compress>` command. The `<compress>` marker is a command rather than an applicant message. In run B, compression was attempted at that marker but failed because of the API quota error, so the original history was preserved. The token values shown are local estimates from the failed run, not successful API prompt-usage measurements.

### Probes after the conversation

| Probe | Tests | A retrieved? | A answer | B retrieved? | B answer |
|---|---|---|---|---|---|
| Q-1 identity | turn 1 | N/A | No model response | N/A | No model response |
| Q-2 missing document | turn 5 | N/A | No model response | N/A | No model response |
| Q-3 band and amount | turns 3–4 | N/A | No model response | N/A | No model response |
| Q-4 the constraint | turn 6 | N/A | No model response | N/A | No model response |
| Q-5 the open question | turn 7 | N/A | No model response | N/A | No model response |
| **retrieved** | | N/A | | N/A | |

The probes could not be evaluated because their API requests also failed with `429 insufficient_quota`.

### The state my compression produced

```json
N/A
```

No compressed state was produced. The compression API request failed, and the program preserved the existing conversation history instead of silently replacing it.

### Written answers

**1. What did compression buy?** Peak tokens both ways, probes retrieved both
ways, and — if a probe was lost — which one and which turn it came from.

> Compression could not be evaluated in this run because the compression request failed. The local token estimates had the same peak of 1019 tokens and the same total of 10256 in both runs because run B preserved the original history after the failed compression attempt. None of the five probes could be evaluated because their API calls also failed. Therefore, I cannot claim that compression reduced the context or preserved or lost any particular probe.

**2. Why must the state be structured rather than a paragraph?** You could have
asked for "a summary". Say what changes when the summary is an object with
named fields.

> A structured state makes the important parts of memory explicit. In my program, the state has named fields such as `applicant_id`, `topic`, `facts`, `decisions`, `constraints`, `open_questions`, and `language`. This makes the state machine-readable and allows it to be checked against a JSON schema. A free-form paragraph may contain the same information, but it is harder for code to verify whether a required fact is present, missing, or stored in the correct category.

**3. What is missing from your state that you would add?** Name what you would
add and what you would drop to pay for it.

> I would add a `source_turns` field that records which conversation turn supports each important fact. This would make it easier to trace compressed information back to the original conversation and check whether the state changed a fact during compression. To pay for the additional tokens, I would shorten repetitive wording in the `facts` field and avoid storing information that is already represented clearly in another field.

**4. When is compression the wrong choice?** Name a conversation where it would
lose something that cannot be recovered, and say whether your program would
notice.

> Compression is a poor choice when exact wording matters, for example a conversation containing a legal statement, an exact quotation, or detailed instructions whose wording must be preserved. A summary can keep the general meaning while losing a small but important detail. My program validates the structure of the compressed state, so it can notice a missing required field or an invalid type, but schema validation alone cannot detect every semantic detail that was omitted or changed. The original conversation would be needed to recover information that was discarded.


---

## Sublab Hard — stories in, CVs out, the best candidate by code

**Run status:** The program found all six candidate stories, but every extraction request failed because the API returned `429 insufficient_quota` (`credit_balance_exhausted`). Therefore, no candidate extraction, model score, weighted total, or prose winner was produced.

### Part 1 — extraction

| Story | Parsed? | Valid? | Fields that came back `null` | Traps hit |
|---|---|---|---|---|
| story-01 | N/A | N/A | N/A | N/A |
| story-02 | N/A | N/A | N/A | N/A |
| story-03 | N/A | N/A | N/A | N/A |
| story-04 | N/A | N/A | N/A | N/A |
| story-05 | N/A | N/A | N/A | N/A |
| story-06 | N/A | N/A | N/A | N/A |

The four traps, for reference: no GPA stated · a GPA on another scale · a paper
that is not published · a story that contradicts itself.

The traps are present in the supplied stories, but the table records the actual program run. Since no extraction response was returned, I did not mark any trap as successfully detected by the model.

Paste the extraction for **story-06**, the one that contradicts itself:

```json
N/A
```

No extraction was produced for story-06 because the API request failed. The extraction prompt was designed to keep a contradicted field as `null` and record the contradiction in `ambiguities`, rather than choosing or averaging conflicting values.

### Part 2 — scores and the winner

| Candidate | academic (0–5) | research (0–5) | experience (0–5) | weighted total (code) |
|---|---|---|---|---|
| story-01 | N/A | N/A | N/A | N/A |
| story-02 | N/A | N/A | N/A | N/A |
| story-03 | N/A | N/A | N/A | N/A |
| story-04 | N/A | N/A | N/A | N/A |
| story-05 | N/A | N/A | N/A | N/A |
| story-06 | N/A | N/A | N/A | N/A |

**Winner, computed by my code:** N/A — no candidates were successfully extracted and scored.

**The model's prose answer, asked separately ("who should win?"):**

> N/A — the scoring stage could not be completed because the extraction requests failed, so no valid candidate results were available for the separate prose-winner call.

### Part 3 — written answers

**1. Which rule did you have to add, and what broke without it?** Name the
story that forced it.

> I added an explicit contradiction rule: when a story gives conflicting values for the same field, the extractor must not choose, average, or guess between them. The affected field should be `null`, and the conflict should be recorded in `ambiguities`. Story-06 forced this rule because it gives conflicting GPA and graduation information. Without the rule, the model could arbitrarily select one value and make the extracted CV look more certain than the source story actually is.

**2. Where did the model guess, and where did your code have to decide?** One
example of each, from your run.

> I could not observe an actual model guess in this run because all extraction API requests failed. However, the prompt specifically prevents likely guessing cases such as story-02, where no numerical GPA is stated and the model must not invent one. My code, rather than the model, is responsible for computing the final weighted total from the returned criterion scores using the rubric formula: `0.5 * academic + 0.3 * research + 0.2 * experience`. This keeps the final arithmetic deterministic.

**3. Did your prose ranking and your computed ranking agree?** Say which one
you trust and why — and if they agreed, what you would need to see before
trusting the prose one alone.

> I could not compare the prose ranking with the computed ranking because the failed API requests prevented the scoring and prose-winner stages from producing results. If both were available, I would rely on the code-computed weighted totals for the final ranking because the calculation follows the rubric weights explicitly and deterministically. Before trusting a prose answer alone, I would need to verify that it used the same extracted facts, criterion scores, weights, and ranking rule without silently changing any of them.

**4. The rubric has no anchor for a contradicted field.** The stories say 3.2
and then 3.5; the rubric defines a 0 and a 5 and nothing in between for this
case. Say what you did and what the rule should be.

> I treated the contradicted GPA as unknown instead of choosing 3.2, choosing 3.5, or averaging them. The extraction rule sets the affected value to `null` and records the contradiction in `ambiguities`. A better rubric should explicitly define how contradicted evidence affects scoring. For example, it could require the academic score to remain unresolved until the contradiction is verified from a trusted source. This is safer than allowing the model to invent a resolution.

**5. How close were your top two candidates?** If they were within 0.05, say
what you would tell the committee and what you would change in the extraction
to make that call defensible.

> I could not calculate the distance between the top two candidates because no valid scores or weighted totals were produced in this run. If two candidates were within 0.05, I would tell the committee that the difference is too small to treat as a robust distinction without reviewing the underlying evidence. I would strengthen the extraction by preserving evidence for each scored field, including the exact source text and ambiguity information, so the committee could verify the facts behind the scores before making the final decision.

---

## Reflection (optional, one short paragraph)

Having now written a role prompt, compressed a conversation, and ranked six
extractions — what will you do differently the next time you build something
that has to get reliable structured output out of a model?

> The main thing I learned from this homework is that prompts alone are not enough for reliable structured output. Next time, I would define the output schema and validation rules before writing the prompt, keep important calculations and policy checks in deterministic code, and preserve evidence for important extracted facts. I would also design failure handling from the beginning so that an API error, invalid JSON, or failed compression does not silently produce incorrect results.
