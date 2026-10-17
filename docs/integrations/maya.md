# Maya integration

Maya integration is not included in the current Input Bridge application.

Input Bridge is designed so a future Maya connector can consume resolved host
actions without moving Maya-specific logic into the device protocol, layer
service, or core runtime. Until that connector exists, users should treat Maya
profiles and action IDs as planning or external-connector documentation only.

Any future Maya integration should document its supported Maya versions,
installation location, connector entry point, action mappings, and manual
verification steps separately from the core Input Bridge installation.
