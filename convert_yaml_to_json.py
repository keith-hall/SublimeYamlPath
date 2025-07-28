import sublime
import sublime_plugin


class ConvertYamlToJsonCommand(sublime_plugin.TextCommand):
    def run(self, edit: sublime.Edit):
        # if any selection is empty, use the whole document
        if not all(sel for sel in self.view.sel()):
            # TODO: split by YAML doc separator?
            # - gives most flexibility, that user can always select what they want to convert
            whole_doc = sublime.Region(0, self.view.size())
            convert_region_to_json(self.view, edit, whole_doc)
            self.view.assign_syntax('Packages/JSON/JSON.sublime-syntax')
        else:
            convert_selections_to_json(self.view, edit)


def convert_selections_to_json(view: sublime.View, edit: sublime.Edit) -> None:
    # convert each selection in reverse order
    prev_region_begin = -1
    for sel_region in reversed(view.sel()):
        if sel_region.end() == prev_region_begin - 1:
            # insert YAML document separator
            view.insert(edit, sel_region.end(), '\n---')
        convert_region_to_json(view, edit, sel_region)
        prev_region_begin = sel_region.begin()


def convert_region_to_json(view: sublime.View, edit: sublime.Edit, region: sublime.Region) -> None:
    try:
        data = yaml.load(view.substr(region))
    except Exception as e:
        view.window().status_message('Unable to parse YAML: ' + str(e))
        return
    
    new_contents = sublime.encode_value(data, pretty=True)
    view.replace(edit, region, new_contents)
