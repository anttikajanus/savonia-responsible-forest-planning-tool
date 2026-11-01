# Use Windows as the supported development environment

Status: accepted  
Recorded: 2026-11-01

Windows is the only supported development environment for this personal
prototype because it is the environment used by the maintainer. Maintain and
verify development setup, local tooling, debugging, testing and packaging
instructions for Windows. The existing Windows CI jobs support this choice.

Supporting Linux and macOS development environments would add setup paths,
platform-specific instructions and verification work that the maintainer does
not use. Their development environments and the applicability of the development
guide on those platforms are outside the prototype's scope. They are not pending
verification tasks. A Python script that happens to work on another platform
does not establish support for the complete development environment there.

This decision concerns development tooling and documentation. It does not
change the plugin's QGIS installation range or establish that the plugin is
incompatible with another operating system. Runtime compatibility and desktop
acceptance remain separate from development-environment support.

The [development guide](../development.md) owns current setup and check commands;
the [verification register](../../open-questions.md#release-and-distribution-verification)
owns remaining runtime and release checks. Expanding development support requires
an explicit replacement decision, maintained setup instructions and verification
on the added platform.
