---
id: "legal-ethical-access"
title: "Legal and Ethical Data Access"
status: "Active"
created: "2026-05-13"
last_reviewed: "2026-05-13"
review_frequency: "Annual"
conflicts_with: []
tags:
  - ethics
  - legal
  - access
  - privacy
---

## Tenet: legal-ethical-access

**Title**: Legal and Ethical Data Access

**Description**: The Access phase must include explicit consideration of the legal and ethical basis for using each data source. This covers intellectual property rights (database copyright, license agreements), individual privacy rights (GDPR, CCPA, and equivalent frameworks), data provenance (where did this data come from, who collected it, and how), and ethical use (consent, potential harms to individuals or groups). Access code and documentation must record these considerations, not treat them as implicit or assumed. Data that cannot be accessed legally or ethically must not be used.

**Quote**: *"Getting the data is not just a technical problem — it is a legal and ethical one too."*

**Examples**:
- Including a comment in access.py recording the license under which a dataset is used
- Documenting in the access layer that a dataset was collected with informed consent and noting the consent scope
- Checking whether an API's terms of service permit the intended use before writing the access code
- Recording data provenance (source URL, access date, version) so the analysis can be reproduced and audited
- Flagging in the access layer when data contains personally identifiable information and what protections apply

**Counter-examples**:
- Writing access code that scrapes a website without checking the terms of service
- Using a dataset without documenting its license or the legal basis for access
- Combining datasets without checking whether the composite use violates any individual license
- Treating provenance as unimportant because "the data is already available"
- Ignoring GDPR obligations because the data was obtained from a public source

**Conflicts**:
- Legal and ethical review can slow down exploratory analysis
- Resolution: A brief, explicit note in the access layer is low cost and prevents serious downstream problems; it also serves as documentation for future analysts
- In some research contexts, datasets are shared internally and licensing is assumed to be clear
- Resolution: Even internally shared data benefits from explicit provenance and consent documentation

**Version**: 1.0 (2026-05-13)
