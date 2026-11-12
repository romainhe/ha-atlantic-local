# CLAUDE.md

Home Assistant custom integration (`custom_components/atlantic_local/`) driving an Atlantic connected heater over its Wi-Fi module's local web server. Same layout and tooling as `ha-prix-carburants`: `scripts/setup` / `scripts/develop`, pytest with `pytest-homeassistant-custom-component`, ruff, hassfest + HACS + tests in CI.

## Protocol

See README "Protocole". The traps:

- One command per HTTP request: the module only answers the first item of a batch. `AtlanticLocalApi` serialises requests behind a lock.
- Writes must use the typed key the id reads back with (`VIS` for temperatures). The generic `value` key from the module's own maintenance page is rejected with `ERROR 4`.
- Local ids are unrelated to Cozytouch / Magellan cloud capability ids (cloud 40 = setpoint, local 4118).
- `GET /passthrough/reboot` reboots the module: never call it. Do not touch `/passthrough/ota_*` or `/passthrough/zigbee` POSTs.

## Mapping new ids

Ids were found by scanning reads (`CMD 1`) and diffing snapshots while changing the heater by hand. The heater lives in blocks 4000–4199. Mode ids are not mapped yet. `scripts/map_ids.py` (read-only) diffs the heater blocks between manual changes; protocol in `docs/mapping-modes.md`. Once known, set `PRESET_MAP` / `POWER_MAP` (`ModeMap`) in `const.py`: the climate entity derives its presets, HVAC off and turn on/off from them, and writes with the map's typed key. Any new preset name needs a translation under `entity.climate.heater.state_attributes.preset_mode`.

## Tests

`tests/fake_module.py` emulates `/passthrough/cmd` (reads, typed writes, `ERROR 4` on wrong key). Integration tests patch `async_get_clientsession` to return it.
