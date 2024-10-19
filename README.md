# YAML Path

A Python package and Sublime Text plugin which uses `ruamel.yaml` to parse YAML and JSON documents and lookup the "breadcrumb path" at a given position, which if used as a `yq`/`jq` query, should return the same item.

The Sublime Text plugin shows the path of the current selection/caret position in the status bar, so you can easily tell which part of the document you are in. There is also a command palette entry to copy the path to the clipboard. And to view the parse error in case the content is not valid.

It even works with multiple selections and inside YAML or JSON codefences embedded in Markdown documents.

## Status

Originally written for my own personal use, but happily accepting Pull Requests to fix any bugs or add more features.

Known limitations:
- currently only drills down to line level. This can be improved if it would be useful.
- doesn't handle JSONC very well - because it is using a YAML parser, `//` isn't a valid comment in YAML...
- currently no way to enable only for YAML files, and leave JSON to be handled by a separate plugin for example

## How it works

When a selection change event is fired by Sublime Text, YAMLPath checks to see if the selection start and end has the same scope. (It will if it is an empty selection of course!) If it is a JSON or YAML scope, it finds the surrounding context - either the whole document or the Markdown code fence for example, and checks the cache to see if it has an already parsed document for that region.
If it doesn't, it will use the ruamel.yaml Python package to parse it and get the locations of all the nodes. This is then cached until the "view" is closed or edited etc.
Then, it recursively looks through the parse tree for the node which comes immediately before the selection position. It knows not to recurse the 1st child node if the selection is after the 2nd child node position for example.
Based on that hierarchy/stack of breadcrumbs, it generates the "YAML path" and shows it in the status bar.
When the view is edited, it debounces the events, so that it only reparses the YAML after 200 ms has elapsed since the last edit, to keep the UI smooth.

## Testing

To run the unit tests:
```sh
python3 -m venv .venv
source .venv/bin/activate
pip3 install poetry
poetry install --no-root
poetry run python3 -m yaml_path.tests.test_yaml_path
```
