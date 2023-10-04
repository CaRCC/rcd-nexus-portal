import re

class NavNode(object):
    def __init__(self, label="root", link=None, current=False, children=None):
        self.label = label
        self.link = link
        if children == None:
            self.children = []
        else:
            self.children = list(children)
        self.current = current

    def __iter__(self):
        yield from self.children

    def __str__(self):
        return self.label

    def as_html(self):
        classes = "current" if self.current else ""
        if self.link != None:
            return f'<a class="{classes}" href="{self.link}">{self.label}</a>'
        else:
            return f'<span class="{classes}">{self.label}</span>'

    def set_current(self, label_regex):
        """
        Nodes matching the label regex will be highlighted. Others will lose highlighting.
        """
        regex = re.compile(label_regex)

        def _set_current(node):
            node.current = bool(regex.match(node.label))
            for child in node:
                _set_current(child)
        
        _set_current(self)