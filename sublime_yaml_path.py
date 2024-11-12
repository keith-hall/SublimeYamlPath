import sublime
import sublime_plugin
import time
from functools import partial, wraps
from typing import Iterable, Optional, Union
from .yaml_path.yaml_path import parse_yaml_docs, yaml_path_to
from ruamel.yaml import YAMLError


VIEW_ID_YAML_MAP = {}


def debounced(delay_in_ms, sync=False):
    """Delay calls to event hooks until they weren't triggered for n ms.

    Performs view-specific tracking and is best suited for the
    `on_modified` and `on_selection_modified` methods
    and their `_async` variants.
    The `view` is taken from the first argument for `EventListener`s
    and from the instance for `ViewEventListener`s.

    Calls are only made when the `view` is still "valid" according to ST's API,
    so it's not necessary to check it in the wrapped function.
    """

    # We assume that locking is not necessary because each function will be called
    # from either the ui or the async thread only.
    set_timeout = sublime.set_timeout if sync else sublime.set_timeout_async

    def decorator(func):
        to_call_times = {}

        def _debounced_callback(view, callback):
            vid = view.id()
            threshold = to_call_times.get(vid)
            if not threshold:
                return
            if not view.is_valid():
                del to_call_times[vid]
                return
            diff = threshold - time.time() * 1000
            if diff > 0:
                set_timeout(partial(_debounced_callback, view, callback), diff)
            else:
                del to_call_times[vid]
                callback()

        @wraps(func)
        def wrapper(self, *args, **kwargs):
            view = self.view if hasattr(self, 'view') else args[0]
            if not view.is_valid():
                return
            vid = view.id()
            busy = vid in to_call_times
            to_call_times[vid] = time.time() * 1000 + delay_in_ms
            if busy:
                return
            callback = partial(func, self, *args, **kwargs)
            set_timeout(partial(_debounced_callback, view, callback), delay_in_ms)

        return wrapper

    return decorator


class StatusBarYamlPath(sublime_plugin.EventListener):
    STATUS_BAR_KEY = "YamlPath"

    def update_path(self, view: sublime.View) -> None:
        yaml_paths = list(get_yaml_paths_for_view_selections(view))
        if len(yaml_paths):
            view.set_status(self.STATUS_BAR_KEY, "YAML Path: " + ", ".join(yaml_paths))
        else:
            view.erase_status(self.STATUS_BAR_KEY)

    @debounced(200)
    def on_selection_modified_async(self, view: sublime.View) -> None:
        self.update_path(view)

    def on_close_async(self, view: sublime.View) -> None:
        try:
            del VIEW_ID_YAML_MAP[view.id()]
        except KeyError:
            pass
        view.erase_status(self.STATUS_BAR_KEY)

    @debounced(700)
    def on_modified_async(self, view: sublime.View) -> None:
        if view.id() in VIEW_ID_YAML_MAP:
            # not closed
            del VIEW_ID_YAML_MAP[view.id()]
            self.update_path(view)


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
        else:
            continue
        if yaml_region:
            yield (yaml_region, sel_region)


def get_yaml_paths_for_view_selections(view: sublime.View) -> Iterable[str]:
    for yaml_region, sel_region in get_yaml_regions_containing_selections(view):
        # TODO: think of a better way to handle it than a region hash
        #       - region hash changes every character typed...
        #       - but it's i.e. still the 2nd yaml region in a Markdown file... use indexing instead? or cache from the begin only and not the end
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
            mark = yaml_docs.problem_mark
            yield f'-- YAML PARSE ERROR -- line {mark.line}: {yaml_docs.problem}'
            continue
        else:
            path = yaml_path_to(yaml_docs, end_rowcol[0] - offset_line, end_rowcol[1])

        if path:
            yield path


def get_region_hash(view: sublime.View, yaml_region: sublime.Region) -> tuple:
    if view.id() not in VIEW_ID_YAML_MAP:
        VIEW_ID_YAML_MAP[view.id()] = {}
    
    if yaml_region == sublime.Region(0, view.size()):
        return (-1, -1) # entire file. Otherwise size changes on each character typed which ruins the region cache

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
            mark = err.problem_mark
            pos = self.view.text_point(mark.line, mark.column)
            self.view.sel().clear()
            self.view.sel().add(pos)
            self.view.show(pos)
            self.view.show_popup(
                '<pre>' + sublime.html.escape(str(err)) + '</pre>',
                pos #sel_region.b
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
