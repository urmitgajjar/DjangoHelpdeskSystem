from django import template


register = template.Library()


@register.filter
def split(value, delimiter=" "):
    return str(value or "").split(delimiter)


@register.filter
def replace(value, args):
    text = str(value or "")
    if args is None:
        return text

    parts = str(args).split(",", 1)
    old = parts[0]
    new = parts[1] if len(parts) > 1 else ""
    return text.replace(old, new)
