## Governance Control Plane v1

### Positioning

The governance control plane is a lightweight local management surface for the
configuration assets that drive the current governance engine.

It is not a complex backend and it is not a database-backed configuration center.
Its job is to make the most important governance assets:

- visible
- editable
- validatable
- saveable
- publishable

within the current single-user local MVP.

### Managed Assets

Current version manages these asset groups:

1. knowledge packs
   - abbreviation dictionary
   - root-word dictionary
   - standard fields library
2. workflow profiles
3. intent patterns
4. tool registry
5. quality rule recommendation configs
   - quality rule templates
   - quality rule policies

### Why Draft and Published Status Matter

Even in a local MVP, configuration changes should not be treated as invisible edits.
The control plane keeps a lightweight status per asset so the user can distinguish:

- `draft`
  - valid content exists, but it is not explicitly marked as published
- `published`
  - current file content is considered the active published baseline
- `invalid`
  - the latest edited content failed validation or current file content no longer passes checks

### Basic Flow

The expected configuration lifecycle is:

1. select a managed asset
2. inspect current content
3. edit locally
4. validate changes
5. save changes
6. publish when ready

### Save, Validate, Publish Behavior

- save creates a backup before writing when the edited content passes validation
- validation updates status metadata and stores the latest validation timestamp
- publish re-validates the asset and only updates metadata status when validation passes

### Backups and Snapshots

- `backups/` stores overwrite protection copies before saves
- `snapshots/` is reserved for manual exported snapshots or future compare flows

### Current Boundary

Current control plane scope is intentionally limited:

- local single-user only
- file-level configuration management only
- YAML / JSON / CSV assets only
- no approval workflow
- no multi-user editing
- no database-backed versioning
- no external admin API

### Future Direction

Later versions may add:

- multi-user approval workflow
- version diff and rollback views
- database-backed config registry
- external admin API
