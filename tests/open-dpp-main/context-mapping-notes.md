# Context mapping notes

This file records every IRI mapping decision made when adding JSON-LD context to the open-dpp textile schema (v0.5.0).

Three namespaces are used:

- schema: https://schema.org/
- gs1: https://www.gs1.org/voc/
- dpp: https://open-dpp.eu/vocab#

The dpp: namespace is provisional. It does not yet resolve to a published vocabulary document. It is used for two categories of term: (1) DPP-specific concepts with no equivalent in schema.org or GS1, and (2) textiles-specific or regulatory concepts where no stable external IRI has been identified.

Fields marked "mapping under review" carry `iri_review: true` in schema.json and display a note in the schema documentation.

---

## Namespace decisions

### Why schema.org over GS1 for most terms

schema.org terms are stable, widely implemented, and well-understood by linked data consumers. GS1 terms are preferred where the GS1 source is more precise - specifically `hasBatchLotNumber` and `gln`, which have no direct schema.org equivalent.

### Why not UNTP vocabulary

UNTP (UN Transparency Protocol) defines relevant concepts including `EmissionsPerformance` and supply chain classes. However, the UNTP vocabulary IRIs currently use the subdomain `https://test.uncefact.org`, which is a test environment and not a stable namespace for production use. Until UNTP vocabulary IRIs are confirmed at `https://vocabulary.uncefact.org/` (the stable base), UNTP terms are not used. Carbon footprint and supply chain properties are flagged as mapping under review for this reason.

### Why not EU Reg 1007/2011 terms for fibre types

Regulation (EU) 1007/2011 defines the authoritative list of textile fibre names (Annex I), but it exists only as a legal text - there is no machine-readable ontology or IRI namespace associated with it. `dpp:fibreType` is therefore interim.

---

## Field-by-field mapping log

### 1.1 product_identifier

| property | iri | status |
|---|---|---|
| id | @id | stable |
| product_name | schema:name | stable |
| product_type | dpp:productType | mapping under review |
| batch_number | gs1:hasBatchLotNumber | stable |
| serial_number | schema:serialNumber | mapping under review |
| model_number | schema:model | stable |
| dpp_level | dpp:dppLevel | stable |

Notes:
- `id` maps to the JSON-LD `@id` keyword because the value IS the node identifier (a GS1 Digital Link URI). This is the most semantically precise mapping possible.
- `serial_number` is flagged because `gs1:hasSerialNumber` is a competing candidate. `schema:serialNumber` is chosen as the primary mapping for wider compatibility, but gs1:hasSerialNumber is the more precise term in a GS1 context. Decision pending.
- `product_type` has no clean external equivalent. `schema:category` exists but applies to commercial product categories, not textile product type classification. Flagged.

### 1.2 user_manuals_and_safety_information

| property | iri | status |
|---|---|---|
| care_instructions | dpp:careInstructions | stable |
| repair_instructions_url | schema:url | mapping under review |
| end_of_life_instructions | dpp:endOfLifeInstructions | stable |
| language_codes | schema:inLanguage | stable |
| accessible_until | dpp:accessibleUntil | mapping under review |

Notes:
- `repair_instructions_url` uses `schema:url` as a generic fallback. A more specific term describing a URL pointing to repair documentation would be preferable. The same generic mapping applies to all other URL-type fields in this schema (see below).
- `accessible_until` has no clean external equivalent. `schema:expires` exists but is defined for Offers and other commerce objects, not for accessibility guarantees on information resources. Flagged.

### 2.1 operator_identifiers

| property | iri | status |
|---|---|---|
| operator_role | dpp:operatorRole | stable |
| operator_name | schema:name | stable |
| unique_operator_identifier | gs1:gln | stable |
| postal_address | schema:address | stable |
| electronic_contact | schema:email | mapping under review |
| eori_number | dpp:eoriNumber | stable |

Notes:
- `unique_operator_identifier` maps to `gs1:gln` because the field description specifies GS1 GLN as the interim standard. If a different identifier system is used, this mapping becomes less accurate.
- `electronic_contact` is flagged because the value may be a URL (web contact form) rather than an email address. `schema:email` is not the right term for a URL value. A union term covering both would be more accurate; none exists in schema.org. Flagged.

### 2.2 manufacturer_contact_details

| property | iri | status |
|---|---|---|
| name | schema:name | stable |
| postal_address | schema:address | stable |
| electronic_contact | schema:email | mapping under review |
| complaints_channel_url | schema:url | mapping under review |

Notes:
- Same electronic_contact flag as 2.1.
- `complaints_channel_url` uses `schema:url` as a generic fallback. No specific term for a complaints/feedback channel exists in schema.org.

### 3.1 fibre_composition

| property | iri | status |
|---|---|---|
| fibre_type | dpp:fibreType | mapping under review |
| percentage | dpp:percentage | mapping under review |
| component | dpp:component | stable |
| is_recycled | dpp:isRecycled | stable |

Notes:
- `fibre_type` is flagged because EU Reg 1007/2011 Annex I fibre names have no machine-readable ontology. No external vocabulary maps this concept.
- `percentage` is flagged because a generic weight-percentage term does not exist in schema.org or GS1. The concept is simple but context-dependent (weight percentage of a fibre within a product component). A qualified measurement would require a more complex mapping than a flat @context supports.

### 3.2 recycled_content

| property | iri | status |
|---|---|---|
| material | schema:material | stable |
| recycled_percentage | dpp:recycledPercentage | mapping under review |
| recycled_source | dpp:recycledSource | mapping under review |
| verification_standard | dpp:verificationStandard | stable |
| certificate_id | schema:identifier | stable |

Notes:
- `recycled_percentage` is flagged for the same reason as `percentage` above.
- `recycled_source` (post_consumer / post_industrial / mixed / unknown) reflects a GRS/ISO 14021 concept. Global Recycled Standard and ISO 14021 define this distinction, but neither publishes a dereferenceable IRI namespace for these terms. Flagged.

### 3.3 raw_material_origin

| property | iri | status |
|---|---|---|
| material | schema:material | stable |
| country_of_origin | schema:countryOfOrigin | stable |
| region | schema:addressRegion | stable |
| farm_or_source_id | dpp:farmOrSourceId | stable |

Notes:
- All mappings are straightforward. `farm_or_source_id` has no external equivalent and uses the dpp: namespace without review flag - it is a DPP-specific field that would only gain a stable external IRI if and when an agricultural traceability vocabulary is adopted at EU level.

### 4.1 supply_chain

| property | iri | status |
|---|---|---|
| stage | dpp:stage | mapping under review |
| facility_name | schema:name | stable |
| unique_facility_identifier | gs1:gln | stable |
| country | schema:addressCountry | stable |
| address | schema:address | stable |
| tier | dpp:tier | stable |

Notes:
- `stage` is flagged because production stage classification (spinning, dyeing, cut-make-trim, etc.) is a textiles supply chain concept with no published ontology. UNTP defines supply chain concepts but uses an unstable namespace. Flagged pending UNTP stabilisation.
- `unique_facility_identifier` maps to `gs1:gln` following the same logic as `unique_operator_identifier`.

### 5.1 carbon_footprint

| property | iri | status |
|---|---|---|
| total_kgco2e | dpp:totalKgCO2e | mapping under review |
| calculation_methodology | dpp:calculationMethodology | mapping under review |
| scope_boundary | dpp:scopeBoundary | mapping under review |
| reference_year | dpp:referenceYear | stable |

Notes:
- All three flagged properties have UNTP equivalents (`EmissionsPerformance`, related methodology and boundary terms) but UNTP IRIs currently use `https://test.uncefact.org`. Once stable IRIs are published at `https://vocabulary.uncefact.org/`, these should be remapped.
- `total_kgco2e` is specifically the carbon footprint value expressed in kg CO2 equivalent - a well-defined concept in GHG accounting (ISO 14067, GHG Protocol) but with no stable Linked Data IRI in either standard.

### 5.2 water_use

| property | iri | status |
|---|---|---|
| total_litres | dpp:totalLitres | mapping under review |
| calculation_methodology | dpp:calculationMethodology | mapping under review |
| scope_boundary | dpp:scopeBoundary | mapping under review |

Notes:
- Same flags as carbon_footprint. ISO 14046 defines water footprint methodology but publishes no Linked Data vocabulary.

### 6.1 substances_of_concern

| property | iri | status |
|---|---|---|
| substance_name | schema:name | stable |
| other_names | schema:alternateName | stable |
| cas_number | dpp:casNumber | mapping under review |
| ec_number | dpp:ecNumber | mapping under review |
| location_in_product | dpp:locationInProduct | stable |
| concentration_ppm | dpp:concentrationPpm | mapping under review |
| espr_category | dpp:esprCategory | stable |
| safe_use_instructions | dpp:safeUseInstructions | stable |
| end_of_life_handling | dpp:endOfLifeHandling | stable |

Notes:
- `cas_number` and `ec_number` are flagged because ECHA publishes no Linked Data namespace. CAS numbers are maintained by the American Chemical Society (Chemical Abstracts Service) which also does not publish a Linked Data namespace. The identifiers are strings within these fields, not IRIs.
- `concentration_ppm` is flagged because no standard property exists for substance concentration expressed in parts per million in a product context. QUDT (Quantities, Units, Dimensions and Types) has related concepts but adds significant complexity.

### 6.2 restricted_substances_compliance

| property | iri | status |
|---|---|---|
| reach_compliant | dpp:reachCompliant | stable |
| rsl_standard | dpp:rslStandard | stable |
| test_report_reference | dpp:testReportReference | stable |
| tested_by | schema:agent | stable |
| test_date | dpp:testDate | stable |

Notes:
- `tested_by` maps to `schema:agent` as the entity performing an action. `schema:Organization` would be more specific but `agent` is more flexible (the tester may be identified by name rather than as a structured object).
- `test_date` uses `dpp:testDate` rather than `schema:dateCreated` because the date refers to when testing was conducted, not when the record was created. These are semantically distinct.

### 7.1 durability

| property | iri | status |
|---|---|---|
| pilling_resistance | dpp:pillingResistance | mapping under review |
| colourfastness_washing | dpp:colourfastnessWashing | mapping under review |
| colourfastness_rubbing | dpp:colourfastnessRubbing | mapping under review |
| test_method | schema:measurementTechnique | stable |
| expected_lifetime_washes | dpp:expectedLifetimeWashes | stable |

Notes:
- The three durability test objects are flagged because textile testing standards (ISO 12945, ISO 105) do not publish Linked Data vocabularies. The concepts are well-defined in standards documents but not as dereferenceable IRIs.
- Sub-properties `score`, `dry_score`, `wet_score`, and `test_cycles` have no IRI assigned. They are too granular to map meaningfully without a domain-specific textile testing ontology.
- `test_method` maps to `schema:measurementTechnique`, which is defined as "a technique or technology used in a MeasuredValue's measuredProperty". This fits test method references.

### 7.2 repairability

| property | iri | status |
|---|---|---|
| repairability_score | dpp:repairabilityScore | mapping under review |
| spare_parts_available | dpp:sparePartsAvailable | stable |
| spare_parts_url | schema:url | mapping under review |
| repair_instructions_url | schema:url | mapping under review |
| repair_network_url | schema:url | mapping under review |
| last_updated | schema:dateModified | stable |
| updated_by | schema:agent | stable |

Notes:
- `repairability_score` is flagged because the ESPR textile delegated act has not yet defined the scoring methodology. The IRI should be updated once the delegated act specifies the scale and calculation method.
- Three URL fields map to `schema:url` as a generic fallback. More specific terms (pointing specifically to spare parts, repair instructions, or repair networks) do not exist in schema.org. These would benefit from more specific dpp: terms once the vocabulary is published.

### 7.3 end_of_life

| property | iri | status |
|---|---|---|
| recyclability_rate | dpp:recyclabilityRate | mapping under review |
| disassembly_instructions | dpp:disassemblyInstructions | stable |
| take_back_scheme_url | schema:url | mapping under review |
| waste_sorting_code | dpp:wasteSortingCode | mapping under review |
| contains_non_recyclable_components | dpp:containsNonRecyclableComponents | stable |
| non_recyclable_components_description | schema:description | stable |
| last_updated | schema:dateModified | stable |
| updated_by | schema:agent | stable |

Notes:
- `recyclability_rate` is flagged because no standard definition of recyclability rate exists at EU level. The ESPR delegated act may define a calculation methodology, at which point the IRI should be updated.
- `waste_sorting_code` is flagged because waste classification codes vary by jurisdiction (e.g. European Waste Catalogue codes, national sorting systems). No single standard Linked Data namespace covers this.
- `take_back_scheme_url` uses `schema:url` for the same reason as other URL fields.

### 8.1 certifications

| property | iri | status |
|---|---|---|
| standard_name | schema:name | stable |
| certificate_id | schema:identifier | stable |
| issued_by | schema:issuer | stable |
| valid_from | schema:validFrom | stable |
| valid_until | schema:validThrough | stable |
| scope | dpp:scope | mapping under review |
| certificate_url | schema:url | mapping under review |

Notes:
- `scope` (product / facility / transaction) is flagged because `schema:about` does not fit the concept of a certification scope. No more specific term exists. This is a DPP-specific classification.
- `issued_by` maps to `schema:issuer`, which is defined for credentials and financial instruments. It fits the concept of a certifying body issuing a certificate.
- `valid_from` / `valid_until` use `schema:validFrom` / `schema:validThrough`. `validThrough` (not `validUntil`) is the correct schema.org term - it is the date after which the offer or certificate is no longer valid.

### 9.1 lifecycle_status

| property | iri | status |
|---|---|---|
| status | dpp:status | stable |
| status_date | dpp:statusDate | stable |
| intervention_description | schema:description | stable |
| updated_by | schema:agent | stable |
| previous_dpp_reference | dpp:previousDppReference | stable |

Notes:
- `status` and `status_date` use dpp: terms because the lifecycle status vocabulary (new / repaired / refurbished / etc.) is ESPR-specific and the dates associated with it are not the same as a generic `dateModified`. Keeping these in the dpp: namespace avoids conflating lifecycle events with document modification timestamps.
- `previous_dpp_reference` has no external equivalent - it is a DPP chaining mechanism specific to the ESPR framework.

### 10.1 dpp_metadata

| property | iri | status |
|---|---|---|
| schema_version | dpp:schemaVersion | mapping under review |
| dpp_created_date | schema:dateCreated | stable |
| dpp_last_updated | schema:dateModified | stable |
| responsible_economic_operator | dpp:responsibleEconomicOperator | stable |
| language | schema:inLanguage | stable |
| registry_unique_registration_identifier | dpp:registryUniqueRegistrationIdentifier | stable |

Notes:
- `schema_version` is flagged because `schema:version` exists in schema.org (defined for CreativeWork) and could apply here. However, this is the version of the DPP schema specification, not the version of the DPP document itself. The distinction matters. Flagged pending a decision on whether `schema:version` is a close enough fit.
- `registry_unique_registration_identifier` uses a dpp: term because the EU DPP registry (Art. 13) does not yet exist as an operational system with its own vocabulary.

---

## Competing vocabulary summary

The following properties have a competing IRI from a second vocabulary:

| property | chosen iri | competing iri | reason for choice |
|---|---|---|---|
| serial_number | schema:serialNumber | gs1:hasSerialNumber | schema.org chosen for wider compatibility; gs1 is more precise in a GS1 context |
| unique_operator_identifier | gs1:gln | schema:identifier | gs1:gln is more specific (this field explicitly uses GLN as the interim standard) |
| unique_facility_identifier | gs1:gln | schema:identifier | same as above |
| electronic_contact | schema:email | schema:contactPoint | email is simpler; contactPoint would require a structured ContactPoint object |

---

## URL-type fields using schema:url

Eight properties map to `schema:url` as a generic fallback. All are flagged as mapping under review. They are:

- `repair_instructions_url` (fields 1.2 and 7.2)
- `complaints_channel_url` (field 2.2)
- `spare_parts_url` (field 7.2)
- `repair_network_url` (field 7.2)
- `take_back_scheme_url` (field 7.3)
- `scope` - not a URL field, separate issue (see 8.1 notes)
- `certificate_url` (field 8.1)

Each of these would benefit from a more specific term describing the purpose of the URL. If and when the dpp: namespace is published as a formal vocabulary, dedicated terms for each URL type should be defined.
