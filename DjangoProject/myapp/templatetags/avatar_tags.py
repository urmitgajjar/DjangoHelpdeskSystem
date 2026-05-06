from django import template
from django.core.exceptions import ObjectDoesNotExist


register = template.Library()


@register.filter
def avatar_url(user):
    if not user:
        return ''
    try:
        profile = user.userprofile
    except ObjectDoesNotExist:
        return ''
    image = getattr(profile, 'Profile_Image', None)
    if not image:
        return ''
    try:
        if not image.name:
            return ''
        if not image.storage.exists(image.name):
            return ''
        return image.url
    except Exception:
        return ''


@register.filter
def avatar_initial(user):
    if not user:
        return ''

    first_name = (getattr(user, 'first_name', '') or '').strip()
    if first_name:
        return first_name[0].upper()

    full_name = (getattr(user, 'get_full_name', lambda: '')() or '').strip()
    if full_name:
        first_part = full_name.split()[0] if full_name.split() else full_name
        if first_part:
            return first_part[0].upper()

    username = (getattr(user, 'username', '') or '').strip()
    if username:
        return username[0].upper()

    return ''
