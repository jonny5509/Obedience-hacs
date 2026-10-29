# Obedience for Home Assistant

[![Downloads](https://img.shields.io/github/downloads/jonny5509/Obedience-hacs/total?label=downloads)](https://github.com/jonny5509/Obedience-hacs/releases) [![Version](https://img.shields.io/github/v/release/jonny5509/Obedience-hacs?display_name=tag&sort=semver)](https://github.com/jonny5509/Obedience-hacs/releases/latest) [![HACS Compatible](https://img.shields.io/badge/HACS-Compatible-41BDF5.svg)](https://hacs.xyz/)


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

## Use Obedience without Home Assistant Cloud

Home Assistant Cloud is not required if you provide your own publicly reachable HTTPS URL. One free option for Home Assistant OS or Supervised is a DuckDNS hostname with a Let's Encrypt certificate. The steps below expose Home Assistant directly on port 8123; only do this if you are comfortable making your Home Assistant instance reachable from the internet.

1. Create a DuckDNS hostname (for example, `my-home.duckdns.org`) and copy its token.
2. In Home Assistant, install and open the **Duck DNS** add-on. Configure it with your hostname and token, and enable its Let's Encrypt certificate options. The add-on configuration is generally similar to:

	 ```yaml
	 domains:
		 - my-home.duckdns.org
	 token: YOUR_DUCKDNS_TOKEN
	 aliases: []
	 lets_encrypt:
		 accept_terms: true
		 algo: secp384r1
		 certfile: fullchain.pem
		 keyfile: privkey.pem
	 seconds: 300
	 ```

	 Add-on options can vary by version. Use the configuration fields shown by the installed add-on, and keep your DuckDNS token private.
3. Configure Home Assistant to use the generated certificate by adding this to `configuration.yaml`:

	 ```yaml
	 http:
		 ssl_certificate: /ssl/fullchain.pem
		 ssl_key: /ssl/privkey.pem
	 ```

	 If you already have an `http:` section, add these options to it instead of creating a second section. Restart Home Assistant after the certificate is available.
4. Configure your router to forward **TCP port 8123** to Home Assistant. Router instructions differ; use a fixed/reserved local IP for Home Assistant. Do not expose ports you do not need.
5. From outside your home network, confirm that `https://my-home.duckdns.org:8123` opens and presents a valid certificate.
6. In Home Assistant, set the **External URL** under **Settings → System → Network** to `https://my-home.duckdns.org:8123`.
7. Add or reconfigure the Obedience integration. It will use this HTTPS URL for authorization and webhook callbacks instead of falling back to Home Assistant Cloud.

Use a strong Home Assistant password, enable multi-factor authentication, and keep Home Assistant and its add-ons updated. For Home Assistant Container/Core or a setup that already uses a reverse proxy, use a dynamic-DNS updater and configure HTTPS at the reverse proxy instead; set Home Assistant's External URL to the proxy's HTTPS address. Do not configure both direct Home Assistant SSL and proxy TLS unless your proxy setup specifically requires it.

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

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/jonny5509)
