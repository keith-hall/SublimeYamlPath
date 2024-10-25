import sublime
import sublime_plugin
from .yaml_dumper.readable_yaml_dumper import configure_yaml_for_dumping, YAML
from io import StringIO
from typing import Any

yaml = YAML()
configure_yaml_for_dumping(yaml)


class ConvertJsonToYamlCommand(sublime_plugin.TextCommand):
    def run(self, edit: sublime.Edit):
        # if any selection is empty, use the whole document
        if not all(sel for sel in self.view.sel()):
            # TODO: if the document looks like JSONL, automatically select all, then split selection into lines
            # - gives most flexibility, that user can always select what they want to convert
            whole_doc = sublime.Region(0, self.view.size())
            convert_region_to_yaml(self.view, edit, whole_doc)
            self.view.assign_syntax('Packages/YAML/YAML.sublime-syntax')
        else:
            convert_selections_to_yaml(self.view, edit)


def convert_selections_to_yaml(view: sublime.View, edit: sublime.Edit) -> None:
    # convert each selection in reverse order
    prev_region_begin = -1
    for sel_region in reversed(view.sel()):
        if sel_region.end() == prev_region_begin - 1:
            # insert YAML document separator
            view.insert(edit, sel_region.end(), '\n---')
        convert_region_to_yaml(view, edit, sel_region)
        prev_region_begin = sel_region.begin()


def convert_region_to_yaml(view: sublime.View, edit: sublime.Edit, region: sublime.Region) -> None:
    try:
        data = sublime.decode_value(view.substr(region))
    except ValueError as e:
        view.window().status_message('Unable to parse JSON: ' + str(e))
        return
    
    new_contents = convert_to_yaml(data)
    view.replace(edit, region, new_contents)


def convert_to_yaml(data: Any) -> str:
    buffer = StringIO()
    yaml.dump(data, buffer)
    return buffer.getvalue()


