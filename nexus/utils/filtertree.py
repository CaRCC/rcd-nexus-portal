from enum import Enum

# THIS IS OBSOLETE - verify and remove this file

class ChoiceType(Enum):
    CHECKBOX = 1
    RADIO = 2
    RANGE = 3

class FilterCategory(object):
    def __init__(self, label="root", paramName=None, eltype=ChoiceType.CHECKBOX, collapsed=False, children=None):
        self.label = label
        self.paramName = paramName
        self.eltype = eltype
        self.collapsed = collapsed
        if children == None:
            self.children = []
        else:
            self.children = list(children)

    def addChild(self, child):
        self.children.append(child)

    def __iter__(self):
        yield from self.children

    def __str__(self):
        return self.label

    def as_html(self):
        htmlbase = f'<span class="filterlabel">{self.label}</span>'
        if self.eltype != ChoiceType.CHECKBOX:
            return htmlbase
        else:
            return f'{htmlbase} <span id="{self.label}.all" class="setall">*</span><span id="{self.label}.none" class="clearall">0</span>'

class FilterChoice(object):
    def __init__(self, label, valueName, checked=True, eltype=ChoiceType.CHECKBOX, radioGroup=None, htmlid=None):
        self.label = label
        self.valueName = valueName
        self.checked = checked
        self.eltype = eltype
        self.radioGroup = radioGroup
        if htmlid is None:
            self.htmlid = valueName+"_"+str(eltype)
        else:
            self.htmlid = htmlid

    def __str__(self):
        return self.label

    def as_html(self):
        inputClass = "longLabel" if len(self.label) > 18 else ""
        if self.eltype == ChoiceType.CHECKBOX:
            type = "checkbox"
            checked = "checked" if self.checked else ""
            return f'<input class="{inputClass}" type="{type}" name="{self.valueName}" id="{self.htmlid}" {checked} /> <label for="{self.htmlid}">{self.label}</label>'
        elif self.eltype == ChoiceType.RADIO:
            type = "radio"
            checked = "checked" if self.checked else ""
            return f'<input class="{inputClass}" type="{type}" name="{self.radioGroup}" value="{self.valueName}" id="{self.htmlid}" {checked} /> <label for="{self.htmlid}">{self.label}</label>'
        else:
            return f'<input class="{inputClass}" type="text" name="{self.valueName}_L" size=3 id="{self.htmlid}_L"/><span> to </span><input type="text" name="{self.valueName}_L" size=3 id="{self.htmlid}_L"/><span> $M</span>'
