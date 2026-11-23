DOMAIN = "obedience"
NAME = "Obedience"
API_BASE = "https://app.obedienceapp.com/extensions"
CONF_EXTENSION_ID = "extension_id"
CONF_SECRET = "secret"
CONF_UID = "uid"
CONF_POLL_INTERVAL = "poll_interval"
CONF_WEBHOOK_HABITS = "webhook_habits"
CONF_WEBHOOK_REWARDS = "webhook_rewards"
CONF_WEBHOOK_PUNISHMENTS = "webhook_punishments"
CONF_WEBHOOK_RELATIONSHIPS = "webhook_relationships"
DEFAULT_WEBHOOK_SUBSCRIPTIONS = {
    CONF_WEBHOOK_HABITS: True,
    CONF_WEBHOOK_REWARDS: True,
    CONF_WEBHOOK_PUNISHMENTS: True,
    CONF_WEBHOOK_RELATIONSHIPS: True,
}
PLATFORMS = ["sensor", "button", "binary_sensor"]
