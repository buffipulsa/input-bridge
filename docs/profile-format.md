# Profile format

Input Bridge profiles are portable JSON documents. They contain host-side
layer and binding data, optional user-authored scripts, and references to
application-specific connectors such as the future Maya bridge.

The current schema version is `1`.

```json
{
  "schema_version": 1,
  "name": "Maya Modeling",
  "layers": [],
  "bindings": [
    {
      "control": "R1C1",
      "action_id": "maya.parent_constraint_from_selection",
      "executor": "maya",
      "layer_path": ["Maya", "Modeling"],
      "trigger": "press",
      "script_id": null
    }
  ],
  "scripts": [],
  "connectors": [
    {
      "connector_id": "maya",
      "name": "Maya bridge",
      "entry_point": "connectors/maya/bridge.py",
      "version": null
    }
  ]
}
```

Profiles contain references and source text, not machine-specific paths or
credentials. Import must validate the schema and show included executable
content before anything is enabled or run. Loading a profile never executes
its scripts.

Host scripts and application connectors are intentionally separate. A host
script can run as an Input Bridge action, while a Maya action is sent to code
running inside Maya and is represented by an action ID in the profile.
