from django import forms

class MultiFileInput(forms.FileInput):
    def __init__(self, attrs=None):
        super().__init__(attrs)
        self.attrs = {'multiple': True} if attrs is None else {**attrs, 'multiple': True}

    def value_from_datadict(self, data, files, name):
        if hasattr(files, 'getlist'):
            return files.getlist(name)
        return files.get(name)

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultiFileInput())  # Use custom widget
        super().__init__(*args, **kwargs)

    def clean(self, value, initial=None):
        if not value:
            return []
        if isinstance(value, (list, tuple)):
            return value
        return [value]