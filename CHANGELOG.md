# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Changed
- Moved top controls into the fixed navbar:
	- Meraki API key input/save controls
	- Organisation selector
	- Floor selector
- Kept Organisation and Floor selectors visible even when no data is loaded by showing disabled placeholder options.
- Removed the `Fetch APs` button from the Heatmap card header.
- Updated Heatmap controls layout so the RSSI cutoff slider is inline next to the `2.4Ghz` and `5Ghz` buttons.
- Reduced the RSSI cutoff slider width for a more compact control row.

### Access Points
- Updated Access Points table columns:
	- Renamed `Ch` to `5Ghz Ch`
	- Renamed `Tx (dBm)` to `5Ghz Tx (dBm)`
	- Added `2.4Ghz Ch`
	- Added `2.4Ghz Tx (dBm)`
	- Removed `Lat` and `Long`
- Updated AP payload generation to include per-band fields from wireless status:
	- `channel5`, `txPower5`
	- `channel24`, `txPower24`
