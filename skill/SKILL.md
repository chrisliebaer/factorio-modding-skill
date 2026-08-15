---
name: factorio-modding
description: >
  Agent optimized documentation variant of official Factorio modding documentation.
  Supports multiple versions, or just `stable`.
  Use when implementing, debugging, explaining or otherwise interacting with Factorio mods.
---

# Factorio modding
Run from this skill directory to fetch the documentation before working on a Factorio mod.

```console
uvx --from ./{{WHEEL_FILENAME}} factorio-docs --version stable
```

Use `experimental` or an explicit Factorio version when the task requires it.
The command generates `ref/stable/`, `ref/experimental/`, or `ref/<version>/` for the selected release and returns the resulting full path to you.
Generation may take between 20 and 40 minutes.

* `auxiliary/`: Guides for mod structure, lifecycle, storage, migrations, libraries, noise expressions, and other topics that span the modding API. (see `index-auxiliary.md`)
* `classes/`: Lua objects whose methods and attributes let scripts inspect and change a running game. (see `classes.md`)
* `concepts/`: Structured values, identifiers, filters, and specifications passed to or returned by the runtime API. (see `concepts.md`)
* `events.md`: Events that scripts register for to react to game lifecycle, world changes, players, and other activity.
* `prototypes/`: Schemas for the entities, items, recipes, technologies, and other definitions that mods add or change while data is loaded. (see `prototypes.md`)
* `types/`: Reusable structures, unions, identifiers, and value formats used by prototype properties. (see `types.md`)
* `runtime/`: The API used by control scripts to handle events and inspect or change the active game through classes, globals, functions, and shared concepts. (see `runtime/index.md`)
* `prototype/`: The API used by data scripts to define and modify the prototypes from which Factorio builds game content. (see `prototype/index.md`)

Shared constants are in `defines.md`.

## Troubleshooting
* Command has a `--refetch` option, this forces full regeneration, so be careful with it.
* Skill supports only a limited range of Factorio versions and is expected to grow support as there is demand.
