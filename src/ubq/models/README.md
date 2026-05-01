# ubq models

The models component provides normalized data structures used by providers and services.

## Design

- Models are immutable dataclasses with `frozen=True` and `slots=True`.
- All fields must have set types
  - optional entries can include `| None` or be an empty list

## Usage

Import the model from `ubq.models` and provide data on creation:

```python
from ubq.models import BugRecord

bug = BugRecord(
	provider_name="launchpad",
	id="12345",
	title="Example bug",
)
```
