# Open DPP
A shared, open field schema for EU Digital Product Passports (DPPs) - starting with textiles.
The EU's Ecodesign for Sustainable Products Regulation (ESPR) requires textile products sold in the EU to carry a digital product passport by a date to be confirmed in a forthcoming delegated act. 
That passport needs to contain specific data about materials, supply chain, repairability, chemicals, and a lot more. 
What it doesn't yet have is a standard technical structure for how that data should be organised.
This schema is an attempt to build that structure in the open, so that compliance teams, brands, and developers are working from the same foundation rather than inventing their own or waiting in decision paralysis for the EC. 
## What's in this repo
This repo contains three things:
A legislation tracker that we can keep up to date with primary sources about the progress of the DPP regulations. 
A proposed field schema for textile DPP data.
Discussions about the above. 
If this proves useful we can add more for the other types of products that will be included. Batteries is a likely next case so `schemas/batteries/` directory is reserved for a future implementation which has a more mature DPP framework
## How the schema is organised
Each field in `schema.json` describes one piece of data that belongs in a textile DPP. Every field carries the same set of properties:

| Property | What it means |
|---|---|
| `field_id` | A reference number. `3.1` means section 3, first field. |
| `field_name` | The field's technical identifier, for use in implementation |
| `section` | Which group of fields this belongs to |
| `mandate_status` | Where the legal requirement comes from - see below |
| `required` | Whether this field is mandatory right now under current ESPR text |
| `access_tier` | Who is allowed to see this data — see below |
| `responsible_for` | Who is responsible for inputting the data along the way |
| `type` | The data format: text, number, true/false, structured object, or list |
| `description` | A plain-language explanation of the field, including who is responsible for it |
| `regulatory_basis` | The specific regulation articles this field comes from |
The [schema.html](schemas/textile/schema.html) page renders all of this in a more human-readable format.
## Mandate status
Not all fields are required today. The regulation works in layers.
| Code | Meaning |
|---|---|
| **M1** | Required now. The obligation exists directly in ESPR (Reg. (EU) 2024/1781). |
| **M2** | Required in principle, details pending. The field category is established in Annex III, but the textile delegated act will confirm the exact requirements. |
| **M3** | Required by a different regulation. The field is relevant to EU compliance, but the primary legal basis is outside ESPR — for example, the EU Deforestation Regulation or the Corporate Sustainability Due Diligence Directive. |
| **M4** | Not currently required. Included because it is standard industry practice or likely to appear in a future delegated act. |
When the textile delegated act is adopted, M2 fields will be updated to reflect confirmed requirements.
---
## Access tier
Not all data in a DPP is visible to everyone. ESPR defines different access levels depending on who is asking.
| Value | Who can see this |
|---|---|
| `public` | Anyone. Accessible via the QR code on the product, no login required. |
| `authorities` | Market surveillance authorities and the European Commission only. |
| `legitimate_interest` | Anyone with a verified legitimate interest — supply chain partners, recyclers, repair operators, researchers. |
| `delegated_act_will_specify` | Not yet defined. The textile delegated act will confirm. |
---
## Responsible for
The schema defines the data structure. Who actually creates, updates, or provides each piece of data is a separate question - and a more complicated one.
That's covered in the responsibility matrix (`dpp_responsibility_matrix_v0_4.xlsx`), which maps every field to the actors responsible for it. Keeping this separate from the schema means the governance can evolve without changing the technical structure.
The regulation recognises eight actors involved in a textile DPP:
- **Manufacturer** — the brand or entity placing the product on the EU market under their name, even if they don't physically make it
- **Importer** — the EU-based entity bringing non-EU products into the market; treated as manufacturer in some circumstances
- **Authorised representative** — an EU-based entity acting formally on behalf of a non-EU manufacturer
- **Supply chain actors** — mills, spinners, dye houses, chemical suppliers; their data obligations activate when the delegated act invokes Art. 38
- **Professional repairer / independent operator** — repair shops, refurbishers, recyclers, waste managers; have rights to update certain fields post-sale
- **Dealer / retailer** — responsible for making the DPP accessible to customers, but has no data creation rights
- **EU responsible person** — required where a non-EU manufacturer has no EU importer
- **DPP service provider** — platforms that store and serve DPP data (like AWARE); a distinct actor type with specific obligations under Art. 10(4) and Art. 11
---
## Contributing
Want to add or notice somethign is wrong? Head over to the [contributing instructions]([url](https://github.com/rhys-the-davies/open-dpp?tab=contributing-ov-file)) to learn how to contribute direclty.
---
## Versioning
The schema uses semantic versioning (`major.minor.patch`):
- **Patch** — corrections to descriptions or references, no change to the field set
- **Minor** — new fields, or reclassification of existing fields
- **Major** — structural changes, or significant reclassification following adoption of the textile delegated act
The current version is `0.4.0`. The schema is in draft - breaking changes are possible before `1.0.0`. Version 1.0.0 will be tagged when the textile delegated act is adopted or the schema has been validated against a live implementation.
---
## Regulatory references
| Instrument | Relevance |
|---|---|
| Reg. (EU) 2024/1781 (ESPR) | Primary instrument. DPP obligations across Art. 7, 9, 10, 11, 12, 27–31, 38 and Annex III. |
| Reg. (EU) 2023/1542 (Battery Regulation) | Structural reference for schema design, particularly Annex XIII and DIN DKE Spec 99100. |
| Reg. (EU) 1007/2011 | EU textile fibre nomenclature, used in the `fibre_composition` field. |
| Reg. (EC) 1907/2006 (REACH) | Chemical substance obligations underpinning the substances fields. |
| Reg. (EU) 2023/1115 (EUDR) | Raw material origin traceability for deforestation-linked commodities. |
| Reg. (EU) 2024/1760 (CSDDD) | Social compliance due diligence basis. |
| Reg. (EU) 2024/3015 (Forced Labour Regulation) | Facility-level disclosure obligations from 2027. |
| Reg. (EU) 2019/1020 (Market Surveillance) | EU responsible person obligations. |
| Union Customs Code Art. 60 | Rules of origin for `country_of_manufacture`. |

—
## Licence
Released under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Free to use, adapt and redistribute with attribution.
