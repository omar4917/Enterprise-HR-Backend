from django import template

from attendance.utils.moderator_labels import get_label

register = template.Library()


@register.simple_tag
def label(key, default=None):
    return get_label(key, default)
