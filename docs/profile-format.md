# Profile format

Input Bridge profiles are portable JSON documents. They contain host-side
layer and binding data, relative references to user-authored scripts, and
references to application-specific connectors. Embedded script source remains
supported only for legacy profile compatibility.

The current schema version is `1`.

```json
{
  "schema_version": 1,
  "name": "Example",
  "layers": [
    {"name": "Global", "locked": true, "children": []},
    {"name": "Example", "locked": false, "children": []}
  ],
  "bindings": [
    {
      "control": "R1C1",
      "action_id": "run_script",
      "layer_path": ["Example"],
      "trigger": "press",
      "script_id": "template_controls",
      "command_name": "Show example message"
    },
    {
      "control": "R1C2",
      "action_id": "run_script",
      "layer_path": ["Example"],
      "trigger": "press",
      "script_id": "template_controls",
      "command_name": "Run example command"
    }
  ],
  "scripts": [
    {
      "script_id": "template_controls",
      "name": "Template controls",
      "path": "template/controls.py"
    }
  ],
  "connectors": []
}
```

Profiles contain relative script references and legacy embedded source text,
not machine-specific absolute paths or credentials. A script entry can use
``path`` to reference a Python file relative to the user-selected codebase,
for example ``template/controls.py``. ``command_name`` is an optional
human-readable name shown in the editor for a specific button binding; it does
not change the underlying action. Import must validate the schema and show
referenced executable content before anything is enabled or run. Loading a
profile never executes its scripts.

Host scripts and application connectors are intentionally separate. A host
script can run as an Input Bridge action, while an application connector can
send an action ID to code running in another application.
