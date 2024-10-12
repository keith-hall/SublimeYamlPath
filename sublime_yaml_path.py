import sublime
import sublime_plugin
from typing import Iterable, Optional, Union
from .yaml_path.yaml_path import parse_yaml_docs, yaml_path_to
from ruamel.yaml import YAMLError


VIEW_ID_YAML_MAP = {}


class StatusBarYamlPath(sublime_plugin.EventListener):
    STATUS_BAR_KEY = "YamlPath"

    def update_path(self, view: sublime.View) -> None:
        yaml_paths = list(get_yaml_paths_for_view_selections(view))
        if len(yaml_paths):
            view.set_status(self.STATUS_BAR_KEY, "YAML Path: " + ", ".join(yaml_paths))
        else:
            view.erase_status(self.STATUS_BAR_KEY)

    on_selection_modified_async = update_path

    def on_close_async(self, view: sublime.View) -> None:
        if view.id() in VIEW_ID_YAML_MAP:
            del VIEW_ID_YAML_MAP[view.id()]

    def on_modified_async(self, view: sublime.View) -> None:
        if view.id() in VIEW_ID_YAML_MAP:
            del VIEW_ID_YAML_MAP[view.id()]


def get_yaml_regions_containing_selections(view: sublime.View) -> Iterable[sublime.Region]:
    change_count_at_beginning = view.change_count()

    for sel_region in view.sel():
        if view.change_count() != change_count_at_beginning:
            # Buffer was changed, we abort our mission.
            return
        start = sel_region.begin()
        end = sel_region.end()
        if start != end and view.scope_name(start) != view.scope_name(end): # selection is okay as long as all inside string etc. as opposed to across tokens
            break
        if not view.match_selector(start, 'source.yaml, source.json'):
            break

        for yaml_region in view.find_by_selector('source.yaml, source.json'):
            if yaml_region.begin() < start and yaml_region.end() > start:
                break

        if yaml_region:
            yield (yaml_region, sel_region)


def get_yaml_paths_for_view_selections(view: sublime.View) -> Iterable[str]:
    for yaml_region, sel_region in get_yaml_regions_containing_selections(view):
        region_hash = get_region_hash(view, yaml_region)
        if region_hash not in VIEW_ID_YAML_MAP[view.id()]:
            text = view.substr(yaml_region)
            # get line and column of sub-yaml...
            start_rowcol = view.rowcol(yaml_region.begin())
            
            VIEW_ID_YAML_MAP[view.id()][region_hash] = (
                parse_yaml_docs(text),
                start_rowcol[0],
            )
        
        end = sel_region.end()
        end_rowcol = view.rowcol(end)
        yaml_docs, offset_line = VIEW_ID_YAML_MAP[view.id()][region_hash]
        if isinstance(yaml_docs, YAMLError):
            # TODO: see if can surface location of error
            yield '-- YAML PARSE ERROR --'
            continue
        else:
            path = yaml_path_to(yaml_docs, end_rowcol[0] - offset_line, end_rowcol[1])

        if path:
            yield path


def get_region_hash(view: sublime.View, yaml_region: sublime.Region) -> tuple:
    if view.id() not in VIEW_ID_YAML_MAP:
        VIEW_ID_YAML_MAP[view.id()] = {}
    
    return (yaml_region.a, yaml_region.b)


class CopyYamlPathCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        yaml_paths = list(get_yaml_paths_for_view_selections(self.view))
        if len(yaml_paths):
            sublime.set_clipboard(", ".join(yaml_paths))

    def is_enabled(self):
        return next(get_yaml_regions_containing_selections(self.view), None) is not None and \
               get_parse_error(self.view)[0] is None


class ShowYamlParseErrorCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        err, _, sel_region = get_parse_error(self.view)
        if err:
            self.view.show_popup(
                '<pre>' + sublime.html.escape(repr(err)) + '</pre>',
                sel_region.b
            )

    def is_enabled(self) -> bool:
        return get_parse_error(self.view)[0] is not None


def get_parse_error(view: sublime.View) -> Optional[YAMLError]:
    for yaml_region, sel_region in get_yaml_regions_containing_selections(view):
        region_hash = get_region_hash(view, yaml_region)
        yaml_docs, _ = VIEW_ID_YAML_MAP[view.id()].get(region_hash, (None, None))
        if isinstance(yaml_docs, YAMLError):
            return (yaml_docs, yaml_region, sel_region)
    return (None, None, None)
