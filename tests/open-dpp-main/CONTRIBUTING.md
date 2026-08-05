# Contributing to open-dpp

The schema is only useful if it reflects reality. If something is wrong, missing, or unclear, contributions are welcome.

## Two ways to contribute

### Not technical? Use GitHub Discussions

If you have a question, a challenge with how a milestone or field is classified, or a disagreement with scope - open a discussion at [github.com/rhys-the-davies/open-dpp/discussions](https://github.com/rhys-the-davies/open-dpp/discussions). 

Each 'card' on the schema page has a 'discuss' button that will take you to the same place. 

You don't need to know anything about JSON or version control. Just describe what you think is wrong or missing and why. This is also the right place for implementation questions - if you're a compliance team trying to understand how a field should be populated in practice, that context is genuinely valuable too.

### Technical? Open a pull request

Changes to `milestones.json` or `schemas/textile/schema.json` should come in as pull requests. See the relevant sections below for what each type of PR needs to include.

---

## Legislation tracker contributions

There are four types of contribution to the tracker, in rough order of priority.

### 1. Verify an existing milestone

The most valuable thing you can do. Each milestone has a primary source link. We always welcome people to check that link, confirm the date and description are accurate, and let us know if we've missed something or if anything has changed.

This is a 15-minute task for anyone who knows where to look in EU regulatory texts.

### 2. Correct an error

Something is factually wrong - a date is off, a description misrepresents the legislation, a source link is broken. Open an issue describing the error and cite the correct source. If you're comfortable with GitHub and sure of your contribution submit a pull request directly. Discussions are always welcome. 

### 3. Add a missing milestone

A relevant regulatory development isn't covered. Propose it as an issue first so we can agree it belongs before you write it up - not everything adjacent to DPPs needs to be in here.

### 4. Suggest or research a new track

A whole regulatory track we're not covering. Currently out of scope but worth tracking: EU Textile Labelling Regulation revision (expected August 2026), REACH intersection with DPP data fields, member state transposition differences. 

Open a discussion issue to propose.

---

### How to verify a milestone

1. Find a milestone marked as needing verification — check [open issues](https://github.com/rhys-the-davies/open-dpp/issues?q=is%3Aopen+label%3Averification-needed) or look for milestones without a `last_verified` date in `data/milestones.json`
2. Follow the primary source link in the milestone
3. Check that the date, description, and status are accurate against the source text
4. If correct: update `last_verified` to today's date and add your GitHub username to `verified_by`
5. If incorrect: correct the data and note what changed in your PR description
6. Submit a pull request

---

### How to add or correct a milestone - for technical readers

Each milestone in `milestones.json` follows this structure:

```json
{
  "id": "e4",
  "date": "2026-01-01",
  "title": "First delegated act consultations — textiles and steel (expected)",
  "status": "expected",
  "desc": "Description with inline citations using [N] notation referencing the refs array.",
  "sources": [
    {
      "label": "Have Your Say portal",
      "url": "https://ec.europa.eu/info/law/better-regulation/have-your-say/initiatives_en"
    }
  ],
  "note": "Optional note for context, caveats, or monitoring guidance.",
  "last_verified": null,
  "verified_by": null
}
```

**Status values:**
- `done` — formally adopted, published in Official Journal
- `active` — currently in effect / obligation is live
- `pending` — scheduled with a confirmed date in the legislation
- `expected` — anticipated based on stated Commission plans, not yet confirmed

A date marked as `expected` should always have a note explaining the basis for the estimate and flagging uncertainty.

**Adding a new reference:** Add to the `refs` array in `milestones.json` and assign the next sequential ID. All refs must include `id`, `title`, `detail`, `type`, and `url`. Type must be one of: `official`, `technical`, `analysis`, `consultation`.

---

## Schema contributions

### What can be changed

- **Fields can be added** — with a clear regulatory basis and all properties completed
- **Fields can be updated** — corrections to descriptions, references, or classification
- **Fields can be removed or narrowed** — only with a clear regulatory justification; the schema should only shrink if the regulation requires it

### For each new field, include

| Property | Required | Notes |
|---|---|---|
| `field_id` | Yes | Follow the existing numbering within the relevant section. `3.1` means section 3, first field. |
| `field_name` | Yes | snake_case, descriptive |
| `section` | Yes | Use an existing section or propose a new one in the PR description |
| `mandate_status` | Yes | M1, M2, M3, or M4 — see README for definitions |
| `required` | Yes | true or false under current ESPR text |
| `access_tier` | Yes | public, authorities, legitimate_interest, or delegated_act_will_specify |
| `data_behaviour` | Yes | static or dynamic |
| `type` | Yes | string, number, boolean, object, or array |
| `description` | Yes | Plain language, including who is responsible for the data |
| `regulatory_basis` | Yes | Specific articles or annex references — no vague regulation names |

PRs that add fields without completing all properties will not be merged.

### Schema versioning

The schema uses semantic versioning (`major.minor.patch`):

- **Patch** — corrections to descriptions or references, no change to the field set
- **Minor** — new fields, or reclassification of existing fields
- **Major** — structural changes, or significant reclassification following adoption of a delegated act

Update the `version` field in `x-meta` in `schema.json` with your PR. If you're unsure which increment applies, note it in the PR and we'll confirm.

---
## How to use all this locally
For now and hopefully for a while it's just a few html pages: 

```bash
git clone https://github.com/rhys-the-davies/open-dpp.git
cd open-dpp
open index.html
```
The schema viewer fetches `schema.json` at runtime, so it needs a local server:
```bash
python3 -m http.server 8000
# then open http://localhost:8000/schemas/textile/schema.html
```

---

## Citation standards

Every factual claim must link to a primary source. This is non-negotiable. The sources used so far all come from official EU sources. If you have a primary source that is not already listed feel free to propose it but be open to discuss its validity unless it's immediately obvious. 
---

## Submitting a pull request

1. Fork the repository
2. Create a branch: `git checkout -b verify/milestone-e4` or `fix/textile-schema-field-2-3`
3. Make your changes to `milestones.json` or `schemas/textile/schema.json`
4. In your PR description, cite the source you used to verify or correct the data
5. Submit against `main`

PRs that change factual data without citing a primary source will not be merged.

---

## Scope

The tracker covers four EU regulatory tracks related to Digital Product Passports: ESPR Framework, Battery Passport, Textile & Apparel DPP, and CRMA Permanent Magnet Passport.

The schema currently covers textiles under Regulation (EU) 2024/1781 (ESPR). A `schemas/batteries/` directory is reserved for a future implementation based on the EU Battery Regulation (Reg. (EU) 2023/1542) — contributions and discussion on that are welcome ahead of formal work starting.

If you want to propose coverage of another product group or regulatory track, open a discussion first.

---

## Questions

Open a [GitHub Discussion](https://github.com/rhys-the-davies/open-dpp/discussions) 
