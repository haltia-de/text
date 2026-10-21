# text

Notepad («Блокнот») for the Haltia desktop
(https://github.com/haltia-de/haltia). It opens a new note or a recent
file, and a file handed over by Files. «Сохранить» writes UTF-8. A new
note asks for a name and is saved in the Documents directory
(`documents()` in `haltia-text`). Unsaved changes ask before you leave.
Only UTF-8 text, at most 2 MB. The application id is
`io.github.haltia_de.Text`.

## Layout

- `haltia-text` — the program, one Python 3 / GTK 3 script.
- `data/io.github.haltia_de.Text.desktop` — launcher (`X-Haltia-Home`).
- `data/io.github.haltia_de.Text.svg` — icon.
- `data/io.github.haltia_de.Text.metainfo.xml` — AppStream data and releases.
- `data/io.github.trudenboy.Text.desktop` — hidden launcher of the old id.
  `install.sh` also links `b8k-text` to `haltia-text`. Both stay until 3.0.
  At startup the old `b8k-text` data directory is migrated.
- `install.sh` — installs the script, both launchers, the icon and metainfo.
- `packaging/alpine/APKBUILD` — Alpine package `haltia-text` (`noarch`).
- `NEWS.md` — release notes, Russian and English.
- `.github/workflows/release.yml` — runs when a `vX.Y.Z` tag is pushed.
- `README.md` — the human summary, in Russian. License GPL-2.0 (`LICENSE`).

## Run and install

Requires Python 3, PyGObject (GTK 3) and haltia-kit
(https://github.com/haltia-de/kit). From the checkout:

```sh
python3 ./haltia-text
python3 ./haltia-text FILE
```

Install here, under `/usr/local`:

```sh
sh install.sh
```

`sh install.sh [ROOT] [PREFIX]` installs under that root and prefix.
PREFIX defaults to `/usr/local`. Alpine calls `sh ./install.sh "$pkgdir" /usr`.

## Release

Write the notes in `NEWS.md`. Tag `vX.Y.Z`. The same number, without `v`,
is `pkgver` and the metainfo `<release>` (version and text). Pushing the
tag runs `.github/workflows/release.yml`, which calls haltia-de/ci
`apk.yml@v1` (`arch: noarch`) to build the signed Alpine package and add
it to the GitHub release. A release needs the user's approval before
the tag is created or the release is published.

## Conventions

Follow https://github.com/haltia-de/haltia/blob/main/docs/conventions.md
for SemVer, tags, commits, languages and paths. ADR 0002 and ADR 0005
are in haltia-de/haltia.
