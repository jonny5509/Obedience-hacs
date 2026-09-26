# Obedience for Home Assistant

A Home Assistant custom integration for the Obedience public API.

## Features

- Connect your Obedience account through the official authorization flow.
- Import all accessible habits, rewards, punishments and relationships.
- Expose each object as a Home Assistant sensor with its API data as attributes.
- Provide increase/decrease buttons for habits that the Obedience API allows Home Assistant to change.
- Register an Obedience webhook automatically for near-real-time refreshes.
- Verify Obedience webhook signatures with the public RSA key.

## Installation

Install this repository through HACS as a custom repository, or copy custom_components/obedience into your Home Assistant configuration.

Home Assistant must have an HTTPS external URL configured because Obedience requires a fully-qualified HTTPS redirect URL for authorization.

Then go to Settings → Devices & services → Add integration → Obedience and authorize Home Assistant in Obedience.

## API scope

The integration uses the documented Obedience extension API to read habits, rewards, punishments and relationships and to increment/decrement habits. It does not store your Obedience password; authorization returns an extension ID and per-user secret which Home Assistant stores in the config entry.

The Obedience API is currently documented as beta and may change.
