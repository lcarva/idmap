# idmap

A local **identity-correlation** store: it maps identifiers from arbitrary
namespaces (services) to a single canonical person. Start from any identifier
and link more later — no service is special, and adding a new one is never a
schema change.

It knows nothing about LDAP, GitHub, or any specific service. It's a `set`/`get`
utility over an [identity graph](https://en.wikipedia.org/wiki/Identity_resolution),
backed by a single SQLite file. No network calls.

## Install

Single file, standard library only (needs Python 3.10+):

```sh
cp idmap ~/.local/bin/idmap    # anywhere on $PATH
chmod +x ~/.local/bin/idmap
```

The database is created on first use at `$IDMAP_DB`, or
`${XDG_DATA_HOME:-~/.local/share}/idmap/idmap.db`. Override per-invocation with
`--db PATH`.

## Concepts

- An **identifier** is `namespace:handle`, e.g. `github:alice`, `ldap:asmith`,
  `quay:alice-q`. The namespace is lowercased; the handle is kept verbatim.
- A **person** (entity) is a cluster of identifiers that all refer to the same
  human. You never create a person explicitly — it appears the first time you
  name an identifier, and clusters **merge** automatically when you link two
  that already exist.
- A person may hold **multiple handles in one namespace** (alt accounts,
  renamed users), so `get --ns` can return more than one line.

## Usage

```sh
# Assert that these identifiers name the same person (creates or merges).
idmap set github:alice ldap:asmith

# Attach more later, starting from any known identifier.
idmap set ldap:asmith quay:alice-q gitlab:alice-gl

# Resolve: all identifiers for the person, or just one namespace's handle(s).
idmap get ldap:asmith                 # github:alice, gitlab:alice-gl, ...
idmap get ldap:asmith --ns github     # alice
idmap get quay:alice-q --ns gitlab    # alice-gl

# Inspect.
idmap ls                              # every person and their identifiers
idmap ls --ns github                  # every github:* handle on record

# Labels and corrections.
idmap name github:alice "Alice Smith"
idmap unlink quay:alice-q             # split it off into its own person
idmap rm gitlab:alice-gl             # forget an identifier
```

`get` prints nothing and exits non-zero when the identifier (or requested
namespace) isn't known — convenient for shell callers.

## Schema

```sql
CREATE TABLE entity (
  id   INTEGER PRIMARY KEY,
  name TEXT
);
CREATE TABLE identifier (
  namespace TEXT NOT NULL,
  handle    TEXT NOT NULL,
  entity_id INTEGER NOT NULL REFERENCES entity(id) ON DELETE CASCADE,
  PRIMARY KEY (namespace, handle)
);
```

## Using it from other tools

Any script can treat LDAP/GitHub/etc. as ordinary namespaces. For example,
resolving a Red Hat LDAP uid to a GitHub id becomes one offline call:

```sh
resolve_github_id() {
  idmap get "ldap:$1" --ns github   # empty output + non-zero exit if unmapped
}
```

Populate the store however you like (LDAP discovery, manual overrides, a CSV
import); querying afterwards needs no network access.
