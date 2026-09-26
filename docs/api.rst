Python API
==========

The modules below are documented directly from their NumPy-style docstrings.

Core event and action handling
------------------------------

.. automodule:: input_bridge.domain.event_normalizer
   :members:

.. automodule:: input_bridge.application.actions
   :members:

.. automodule:: input_bridge.domain.layers
   :members:

.. automodule:: input_bridge.application.layer_service
   :members:

.. automodule:: input_bridge.infrastructure.memory_layer_backend
   :members:

.. automodule:: input_bridge.ui.layer_editor
   :members:

Protocol helpers
----------------

.. automodule:: input_bridge.domain.protocol951
   :members:

Inspection and observation tools
--------------------------------

.. automodule:: input_bridge.infrastructure.inspect_macropad
   :members:

.. automodule:: input_bridge.infrastructure.inspect_protocol
   :members:

.. automodule:: input_bridge.infrastructure.observe_inputs
   :members:

.. automodule:: input_bridge.infrastructure.observe_raw_input
   :members:

Mappings and device state
-------------------------

.. automodule:: input_bridge.application.bindings
   :members:

.. automodule:: input_bridge.domain.neutral_mapping
   :members:

.. automodule:: input_bridge.infrastructure.read_device_state
   :members:

.. automodule:: input_bridge.infrastructure.read_key_layout
   :members:

Configuration writers
=====================

The writer modules are included for reference because they perform device
writes and should only be used with explicit approval and verified mappings.

.. automodule:: input_bridge.infrastructure.write_grid
   :members:

.. automodule:: input_bridge.infrastructure.write_knobs
   :members:

.. automodule:: input_bridge.infrastructure.write_single_key
   :members:

.. automodule:: input_bridge.infrastructure.poll_vendor_input
   :members:
