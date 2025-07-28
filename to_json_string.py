import sublime
import sublime_plugin


class ToJsonStringCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        sel = self.view.sel()[0] or sublime.Region(0, self.view.size())
        input_string = self.view.substr(sel)
        output_string = sublime.encode_value(input_string)
        self.view.replace(edit, sel, output_string)
