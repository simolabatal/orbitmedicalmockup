from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import permissions

from .models import ChatMessage


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def chatbot_api(request):
    message = request.data.get('message', '')
    language = request.data.get('language', 'fr')
    session_id = request.data.get('session_id', str(request.user.id))

    ChatMessage.objects.create(
        user=request.user, session_id=session_id,
        role='user', message=message, language=language,
    )

    response_text = None

    try:
        from django.conf import settings
        import urllib.request
        import json
        api_key = getattr(settings, 'GEMINI_API_KEY', None)
        if api_key and len(api_key) > 10:
            lang_names = {'fr': 'francais', 'ar': 'arabe', 'en': 'anglais'}
            lang_name = lang_names.get(language, 'francais')
            prompt_text = (
                f"Tu es un assistant agricole expert. L'utilisateur parle en {lang_name}. "
                f"Reponds de maniere concise et utile (max 300 caracteres). "
                f"Question: {message}"
            )
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
            payload = json.dumps({"contents": [{"parts": [{"text": prompt_text}]}]}).encode('utf-8')
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                candidates = data.get('candidates', [])
                if candidates:
                    response_text = candidates[0].get('content', {}).get('parts', [{}])[0].get('text', '')
    except Exception:
        pass

    if not response_text:
        Fallback_MSGS = {
            'fr': "Desole, l'assistant IA est temporairement indisponible. Reessayez plus tard.",
            'ar': "المساعد الذكي غير متوفر حاليا. حاول مرة أخرى لاحقا.",
            'en': "Sorry, the AI assistant is temporarily unavailable. Please try again later.",
        }
        response_text = Fallback_MSGS.get(language, Fallback_MSGS['fr'])

    ChatMessage.objects.create(
        user=request.user, session_id=session_id,
        role='bot', message=response_text[:500], language=language,
    )
    return Response({'response': response_text[:500]})
