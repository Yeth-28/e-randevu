from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    if not isinstance(dictionary, dict):
        return None
    return dictionary.get(key)


@register.filter
def default_if_none(value, default):
    return value if value is not None else default


@register.filter
def split(value, sep):
    if not value:
        return []
    return str(value).split(sep)