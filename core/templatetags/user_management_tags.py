from django import template

register = template.Library()

@register.filter
def filter_by_role(members, role):
    """Filter members by role"""
    return [member for member in members if member.role == role]

@register.filter
def filter_admin(roles):
    """Filter roles that are admin roles"""
    return [role for role in roles if role.is_admin]

@register.filter  
def length(value):
    """Get length of a list"""
    try:
        return len(value)
    except (TypeError, AttributeError):
        return 0

@register.filter
def pluralize_simple(value):
    """Simple pluralize filter"""
    try:
        return "s" if int(value) != 1 else ""
    except (ValueError, TypeError):
        return ""
