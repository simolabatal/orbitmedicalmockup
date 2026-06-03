"""
Context processor — expose les rôles et groupes au templates.
Usage dans les templates:
  {% if user_roles.is_admin %}...{% endif %}
  {% if user_roles.is_finance %}...{% endif %}
  {% if user_roles.is_marketing %}...{% endif %}
  {% if user_roles.is_farmer %}...{% endif %}
  {% if user_roles.is_buyer %}...{% endif %}
"""
from types import SimpleNamespace


def roles(request):
    user = request.user
    groups = set()

    if user.is_authenticated:
        try:
            groups = set(user.groups.values_list('name', flat=True))
        except Exception:
            groups = set()

    roles = SimpleNamespace(
        is_admin='Admin' in groups or getattr(user, 'role', '') == 'admin',
        is_finance='Finance' in groups,
        is_marketing='Marketing' in groups or getattr(user, 'role', '') == 'marketer',
        is_farmer=getattr(user, 'role', '') == 'farmer',
        is_buyer=getattr(user, 'role', '') == 'buyer',
        is_authenticated=user.is_authenticated,
        groups=groups,
    )

    return {'user_roles': roles}
