# ubq services

The services component provides methods for connecting to providers externally.


## Existing services

## Direct Python access via QueryService

The QueryService provides functions for logging into a service, then using it to gather or send model data.

### Example

```python
from ubq.models import AuthScope
from ubq.services import QueryService

service = QueryService()
service.login(provider_name="launchpad", scope=AuthScope.READ_ONLY)

bug = service.get_bug(bug_id="12345", provider_name="launchpad")
```
