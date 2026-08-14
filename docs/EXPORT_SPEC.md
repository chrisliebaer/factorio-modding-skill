# Factorio JSON Markdown export specification

This specification defines the approved export of Factorio's machine-readable runtime and prototype API documentation to Markdown.

## Output layout

The temporary output tree has four official documentation areas:

```text
output/
├── settings/
├── auxiliary/
├── prototype/
└── runtime/
```

The runtime export and prototype export each have an `index.md` metadata document. Each index contains that export's `application`, `application_version`, `api_version`, and `stage`. Metadata indexes are not API categories.

Each official top-level JSON category is rendered as one Markdown file. No categories are invented.

The runtime categories are:

* Classes
* Events
* Concepts
* Global objects
* Global functions

The prototype categories are:

* Prototypes
* Types

Definitions are generated as a shared `defines.md` document through a third independent production build step. The defines build is not owned by either the runtime build or the prototype build.

The shared defines build consumes both exports' define collections and applies these rules:

* Reject duplicate names within either source.
* Match definitions by their official name.
* Require the complete typed define subtrees of a shared name to be exactly equal.
* Merge a definition that occurs in only one export into the shared output.
* Preserve both sources' relative JSON order.
* Fail when shared definitions occur in incompatible relative orders.
* Use a deterministic stable merge for exclusive definitions with no cross-source ordering relationship. Runtime precedes prototype only when the sources provide no ordering constraint.

Within every category, definitions remain in JSON array order. The `order` property does not replace JSON array order. No alphabetical sorting or finer grouping is introduced unless a rule explicitly says otherwise.

## Output goals

The Markdown is compact, lossless, human-readable, regex-searchable, and intended for agents.

All semantically relevant JSON information is retained. Character reduction comes from formatting and grammar, not summarization, abbreviation of prose, or omitted information. Menus, navigation, HTML anchors, non-working presentation links, and decorative formatting are not retained.

Canonical declarations start with an anchored, short declaration prefix. Identifiers, signatures, types, and literals use backticks where established by the formats below. A callable declaration follows this form:

```md
## fn `function_name` `(start:int, end:int, word:string)`
```

This permits searches anchored on `^## fn`, searches for a canonical backticked identifier, and searches for a signature independently of its description.

Entity declarations use the official entity kind:

```md
## class `LuaThing`
## event `on_thing_changed`
## concept `ThingSpecification`
## prototype `ThingPrototype` `"thing"`
## type `Thing`
## define `direction`
```

Nested declarations use the same short anchored grammar:

```md
### fn `find` `(start:Position, end:Position) -> LuaEntity[]`
### attr `enabled` `boolean` read/write
### prop `energy_usage` `Energy`
```

Short descriptions follow the declaration on the same line after ` - `:

```md
### attr `enabled` `boolean` read/write - Whether the entity is currently enabled.
### prop `energy_usage` `Energy` required - Energy consumed while operating.
```

Descriptions with additional paragraphs, lists, examples, or code continue below the declaration without rewriting or information loss:

```md
### prop `filters` `PrototypeFilter[]` optional - Filters the candidate prototypes.

Additional constraints or Markdown lists continue below the declaration without being compressed or rewritten.
```

## Callables and members

Argument names, types, order, and optionality are encoded once in a callable signature. Argument detail lines contain only argument-specific documentation and do not repeat a type already present in the signature:

```md
## fn `find` `(start:Position, end:Position) -> LuaEntity[]` - Finds matching entities.
* arg `start` - Beginning of the search area.
* arg `end` - End of the search area.
* return - Matching entities.
```

An argument with no documentation or metadata beyond its signature has no argument detail line.

Multiple return values use a tuple signature. Return detail lines use one-based ordinals when unnamed return values need to be distinguished:

```md
### fn `measure` `(value:string, ...:LocalisedString) -> (number, string?)`
* return `1` - Measured width.
* return `2` - Optional diagnostic.
```

Variadic arguments remain in the signature using `...`.

An attribute with different read and write types uses `<-`:

```md
### attr `value` `LuaItemStack <- ItemStackDefinition` - Current item value.
```

Operators use `op` and retain their actual operator semantics:

```md
### op `index` `(key:string) -> LuaEntity`
### op `length` `() -> uint`
### op `call` `(value:string) -> boolean`
```

Raised events use one line per raised-event record:

```md
* raises `<event>` `<timeframe>` [optional] - <description>
```

The `optional` marker is omitted when false.

Event filters use:

```md
* filter `<FilterType>`
```

Subclass restrictions use an alphabetically sorted list regardless of JSON order:

```md
* subclasses: `<A>`, `<B>`
```

## Metadata

Entity and member metadata is emitted on one line:

```md
* meta: item1, item2, item3
```

Metadata items are sorted alphabetically. Metadata includes applicable information such as abstract status, deprecation, parent, prototype discriminator, visibility, instance limit, aliases, overrides, inline status, and optionality when it is not already encoded in a declaration signature.

For example:

```md
## prototype `AccumulatorPrototype` `"accumulator"` < `EntityWithOwnerPrototype`
* meta: abstract, deprecated, limit=`255`, Space Age
```

Defaults belong directly on the field or property signature using assignment syntax. The assignment combines with the existing optional and type syntax:

```md
a?:float=1
```

The shorthand is `a?=1`. The same pattern applies wherever the same or a similar observed field, property, or parameter declaration carries a default.

Ordinary signatures use single-backtick code spans. When a signature contains backticks, the complete signature uses a double-backtick CommonMark delimiter and preserves the embedded default Markdown unchanged:

````md
## type `LightDefinition` ``{...,color?:Color=`{r=1, g=1, b=1}`,...}``
````

Field-scoped metadata uses the same metadata notation and rendering as all other metadata, nested beneath its owning field detail line:

```md
* field `filename` - ...
  * meta: override
```

Nested metadata items remain alphabetically sorted.

## Table arguments and variants

A callable that takes one table renders the complete table as its signature. Optional fields use `?` after the field name.

An optional whole argument table places `?` after the closing brace:

```md
{raise_destroy?:bool}?
```

Field-level optionality remains inside the braces. A required table has no trailing `?`.

Every method with `variant_parameter_groups` must have `takes_table=true` and `table_optional=false`. The generator fails explicitly otherwise. Focused tests construct typed methods that violate each condition.

Literal-discriminator table variants use `when` and `add`:

```md
### fn `set_gui_arrow` `{margin:u32,type:GuiArrowType}`
* when `type="entity"` add `{entity:LuaEntity}`
* when `type="position"` add `{position:MapPosition}`
* when `type="crafting_queue"` add `{crafting_queueindex:u32}`
* when `type="item_stack"` add `{inventory_index:defines.inventory,item_stack_index:u32,source:"player"|"target"|"player-quickbar"}`
```

`GuiArrowType` is the field's type. Values such as `"entity"` are values of that type, and the added fields are passed in the same table.

Non-discriminator mutually exclusive table shapes retain the official hierarchy. No synthetic dotted identifiers are introduced:

```md
* one of - These attributes provide different methods of specifying the unit's spawn location:
  * `body-nodes` `{body_nodes:MapPosition[]}`
    * arg `body_nodes` - The body nodes that define the shape of the body. [...]
  * `position-and-direction` `{position:MapPosition,direction?:defines.direction,extended?:bool}`
    * arg `position` - The head position.
    * arg `direction` - The initial orientation of the head. [...]
    * arg `extended` - If `true`, [...]
```

The same argument-detail rendering abstraction handles normal and grouped runtime parameters.

Contextual groups whose fields depend on an entity's prototype type do not imply a passed discriminator field or a complete-table alternative. They use:

```md
* by entity type - <variant_parameter_description>
  * `<group>` add `{...}`
    * arg `<argument>` - <description>
```

The group and argument identifiers are the official JSON names.

When `variant_parameter_description` is present but `variant_parameter_groups` is absent, the description is preserved as a standalone detail line:

```md
* variants - Other attributes may be specified depending on `filter`:
```

Groups remain required whenever the documentation describes actual additions.

## Types

Every type name passes through one central explicit type rewriter wherever it is reasonably detectable as an isolated identifier in a structured field. This includes recursive type expressions, class names, concept names, prototype-type names, parents, subclass restrictions, event filter type names, and other modeled type declarations and references. The initial alias is:

```text
boolean -> bool
```

Unmapped official names remain unchanged. Method, attribute, property, and argument names; prototype discriminator values; literals; prose descriptions; examples; lists; and Markdown link text and targets are not rewritten.

The full generated-document sanity test injects a conspicuous alias for a common type, renders the complete relevant API documentation, and proves that every structured occurrence is renamed. Original occurrences are permitted only in explicitly unstructured content such as prose and untouched Markdown links.

Arrays, dictionaries, tuples, unions, literals, and full inline tables retain their complete structural signatures. Large inline structures are not collapsed merely for human readability:

```md
## concept `SearchOptions` `{position:MapPosition,radius:double,force?:ForceIdentification}`
* field `position` - Search center.
* field `radius` - Maximum distance.
* field `force` - Optional force restriction.
```

Described union and literal alternatives remain in the type signature. Each non-empty alternative description additionally receives an option line:

```md
## concept `AsteroidChunkID` `LuaAsteroidChunkPrototype|string`
* option `LuaAsteroidChunkPrototype` - The asteroid chunk prototype.
* option `string` - The prototype name.
```

```md
## concept `ComparatorString` `"="|">"|"<"|...`
* option `"="` - Equal to.
* option `">"` - Greater than.
```

An option line is omitted when that alternative has no description.

Runtime-specific type constructors remain explicitly visible with their official semantics:

```text
function(...)
LuaLazyLoadedValue<T>
LuaCustomTable<K,V>
LuaStruct{...}
builtin
```

Function types list only their parameter types and do not invent return types. `LuaLazyLoadedValue<T>` retains the lazily loaded payload type. `LuaCustomTable<K,V>` remains distinct from an ordinary dictionary. A `LuaStruct{...}` retains all nested attributes and their agreed read/write, optionality, and documentation notation.

## Prototype custom properties

Arbitrary key/value prototype properties use `custom` rather than pretending to have a fixed property name:

```md
### custom `{string:MapGenPreset}` - Presets are defined as uniquely named `MapGenPreset` properties of the prototype. Zero or more named presets can be specified within the prototype.
```

Their lists, examples, and images use the shared documentation rendering below the declaration.

## Defines

Recursive defines retain their hierarchy through nested headings:

```md
## define `direction`
### value `north` - Northward direction.
### define `diagonal`
#### value `northeast` - Northeast direction.
```

## Documentation content

Markdown prose, paragraphs, lists, examples, and fenced code are retained without summarization. Lists, examples, and images attached to an entity or member follow that declaration using the same shared renderer.

Factorio custom internal Markdown links are preserved exactly as they appear in the JSON, including their label and target. They are not rewritten, stripped, normalized, validated as browser URLs, or converted to backticked text. They intentionally remain non-browser-clickable while conveying navigation intent to agents. For example:

```md
[grid tiles](prototype:AgriculturalTowerPrototype::growth_grid_tile_size)
```

External HTTP and HTTPS Markdown links also remain unchanged.

Images retain normal Markdown image syntax and their captions. Image paths are corrected relative to the generated document and a configured static directory. Every referenced image file must exist; generation fails otherwise.

## Fail-fast requirements

The generator fails rather than omitting or guessing information when it encounters:

* An unknown API stage, modeled field, type-expression variant, structural variant, or rendering state.
* A method with variant parameter groups that does not take one required table.
* An image whose resolved source file does not exist.
* Duplicate define names within either export.
* Different complete typed subtrees for a shared define name.
* Incompatible relative ordering of shared definitions.
* Input that cannot be represented by an approved lossless format.
