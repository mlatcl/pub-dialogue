---
id: "2026-05-12_cip000d-update-init-py"
title: "Update pub_dialogue/__init__.py to expose access/assess/address submodules"
status: "Proposed"
priority: "Medium"
created: "2026-05-12"
last_updated: "2026-05-12"
category: "features"
related_cips: ["000D"]
owner: ""
dependencies: [
  "2026-05-12_cip000d-create-access-py",
  "2026-05-12_cip000d-create-assess-py",
  "2026-05-12_cip000d-create-address-py"
]
tags:
- backlog
- cip000d
- access-assess-address
---

# Task: Update pub_dialogue/__init__.py to expose access/assess/address submodules

## Description

Update `pub_dialogue/__init__.py` so that `import pub_dialogue` makes the
three new submodules available as `pub_dialogue.access`, `pub_dialogue.assess`,
and `pub_dialogue.address`.

## Acceptance Criteria

- [ ] `import pub_dialogue; pub_dialogue.access` is accessible after import
- [ ] `import pub_dialogue; pub_dialogue.assess` is accessible after import
- [ ] `import pub_dialogue; pub_dialogue.address` is accessible after import
- [ ] `from pub_dialogue import access` works
- [ ] `from pub_dialogue import assess` works
- [ ] `from pub_dialogue import address` works
- [ ] Existing imports (`from pub_dialogue import LLMClient`, `from pub_dialogue.utils import ...`) still work

## Implementation Notes

This is typically accomplished by adding `from pub_dialogue import access, assess, address`
or ensuring the submodule imports are present in `__init__.py`. Check the
existing `__init__.py` content before editing.

## Related

- CIP: 000D

## Progress Updates

### 2026-05-12

Task created.
