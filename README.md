# Obedience for Home Assistant

A Home Assistant custom integration for the Obedience public API.

## Features

- Uses the official Obedience API.
- **Polling only:** Home Assistant makes outbound HTTPS requests to Obedience.
- No Nabu Casa subscription, port forwarding, tunnel, webhook or inbound Home Assistant connection is required.
- Imports all accessible habits, rewards, punishments and relationships.
- Exposes each object as a Home Assistant sensor with its API data as attributes.
- Provides increase/decrease buttons for habits that the Obedience API allows Home Assistant to change.

## Installation

Install this repository through HACS as a custom repository, or copy the `custom_components/obedience` folder into Home Assistant.

Go to **Settings → Devices & services → Add integration → Obedience**.

Because Obedience requires a fully qualified HTTPS redirect URL, the integration uses a static authorization helper hosted by GitHub Pages. It only displays the values returned by Obedience so you can copy them into Home Assistant.

### GitHub Pages setup

Enable GitHub Pages for this repository:

**Settings → Pages → Deploy from a branch → main → /docs**

The authorization helper URL is:

https://jonny5509.github.io/Obedience-hacs/authorize.html

After authorization, copy the returned extension ID, secret and user ID into Home Assistant.

## Security

The extension secret is an Obedience API credential. Keep it private and do not share the authorization URL or secret.

After setup, Home Assistant only makes outbound requests to the Obedience API. Webhooks are not configured.

The Obedience API is currently documented as beta and may change.
