# Obedience for Home Assistant

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/jonny5509/Obedience-hacs)
[![HACS](https://img.shields.io/badge/HACS-Custom%20Integration-41BDF5.svg)](https://hacs.xyz/)

A Home Assistant custom integration for the **Obedience public API**.

The integration connects your Obedience account to Home Assistant, exposes supported Obedience data as native Home Assistant entities, and uses webhooks for near-real-time updates.

## ✨ Features

- 🔐 Official Obedience authorization flow
- 📥 Import accessible habits, rewards, punishments, and relationships
- 📊 Expose supported API objects as Home Assistant sensors
- 🎛️ Increase/decrease habits through Home Assistant when supported by the API
- ⚡ Automatically register an Obedience webhook for near-real-time refreshes
- 🛡️ Verify webhook signatures using Obedience's public RSA key
- 🔑 Store the extension ID and per-user secret in the Home Assistant config entry rather than your Obedience password

## 📋 Requirements

- Home Assistant with support for custom integrations
- An Obedience account
- An HTTPS external URL configured in Home Assistant
- Network access to the Obedience API

> **Important:** Obedience requires a fully qualified **HTTPS** redirect URL for authorization. Make sure Home Assistant's external URL is configured correctly before starting setup.

## 🚀 Installation

### HACS

Install the repository through HACS as a custom repository if it is not already listed.

Repository:

`https://github.com/jonny5509/Obedience-hacs`

Then:

1. Open **HACS → Integrations**.
2. Install **Obedience**.
3. Restart Home Assistant.
4. Open **Settings → Devices & services**.
5. Select **Add Integration**.
6. Search for **Obedience**.
7. Follow the authorization flow.

### Manual installation

1. Download or clone this repository.
2. Copy `custom_components/obedience` into your Home Assistant `config/custom_components/` directory.
3. Restart Home Assistant.
4. Open **Settings → Devices & services → Add Integration**.
5. Search for **Obedience**.
6. Complete the authorization flow.

## 🔐 Authentication & security

The integration uses the documented Obedience extension API.

It does **not** store your Obedience password. The authorization flow returns an extension ID and per-user secret, which Home Assistant stores in the integration's config entry.

Keep Home Assistant and its backups secure, and do not publish integration credentials or secrets in issue reports, screenshots, or logs.

## 📊 Home Assistant entities

The integration imports supported Obedience data and exposes each accessible object as a Home Assistant sensor, with API data available through entity attributes.

Supported object types include:

- Habits
- Rewards
- Punishments
- Relationships

For habits where the API permits changes, Home Assistant can expose increase/decrease controls.

## ⚡ Webhooks

The integration registers an Obedience webhook automatically and uses it for near-real-time refreshes.

Incoming webhook signatures are verified using Obedience's public RSA key before webhook data is accepted.

## 🌐 API compatibility

The integration uses the documented Obedience extension API.

> **API status:** The Obedience API is currently documented as **beta** and may change. API changes can therefore require corresponding integration updates.

## 🧰 Troubleshooting

### Authorization fails

Verify that:

- Home Assistant has a valid HTTPS external URL.
- The external URL is reachable as required by your Home Assistant deployment.
- Your Obedience account authorization is valid.
- Home Assistant can reach the Obedience API.

### The integration cannot refresh

Check the Home Assistant logs for errors from `custom_components.obedience` and verify API availability.

### Webhook updates are not arriving

Confirm that Home Assistant is reachable through the configured HTTPS external URL and that the integration completed webhook registration successfully.

## 👩‍💻 Development

The integration source code is located in:

`custom_components/obedience/`

When developing changes, test:

- Config Flow authorization
- Entity creation and attribute data
- Habit increase/decrease actions
- Webhook registration
- Webhook signature verification
- API error handling

## 🔄 Updating

For HACS installations:

1. Update **Obedience** from HACS.
2. Restart Home Assistant.
3. Check the logs if the integration does not reconnect or refresh correctly.

## 🔗 Links

- [Repository](https://github.com/jonny5509/Obedience-hacs)
- [Issues](https://github.com/jonny5509/Obedience-hacs/issues)

## 📄 License

See the repository for the current project license.
