# Changelog

## 2.5.0

### Added
- Habit goal, remaining-to-goal, and progress sensors.
- A positive-state binary sensor for each habit.
- Reward cost sensors.
- Home Assistant `obedience_webhook` events containing the webhook's before/after payloads.
- Configurable polling intervals and webhook resource subscriptions.
- Habit increment service support for selecting a habit by entity ID, with optional response data.
- Relationship reward points, recent-history summaries, and bounded note attributes.
- Integration brand icon.

### Improved
- Webhook delivery deduplication with a bounded persistent cache.
- Immediate coordinator updates from valid webhook payloads.
- Entity cleanup when API objects are removed.
- Documentation and service descriptions.

### Testing
- Unit tests are included under `tests/`; run them with `python -m pytest -q`.
