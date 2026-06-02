import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lfellah_server.settings')
django.setup()
from django.contrib.auth import authenticate

for email, pwd in [
    ('mohamed@lfellah.ma', 'simo123'),
    ('fellah@test.ma', 'Fellah@1234'),
    ('marketing@lfellah.ma', 'Market@1234'),
    ('acheteur@test.ma', 'Acheteur@1234'),
]:
    u = authenticate(request=None, username=email, password=pwd)
    print(f"auth({email}) = {u} role={u.role if u else 'N/A'}")