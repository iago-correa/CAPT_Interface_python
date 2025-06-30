from django.shortcuts import render, redirect, reverse
from django.views.decorators.csrf import csrf_exempt
from urllib.parse import urlencode
from login.models import Session

@csrf_exempt
def evaluate(request):
    
    session_id = request.session.get('session_id')
    
    if not session_id:
        error_message = 'Please sign in.'
        query_params = urlencode({'error': error_message})
        return redirect(f"{reverse('login:evaluation_login')}?{query_params}")

    try:
        session_obj = Session.objects.get(id=session_id)
        rater = session_obj.rater
    except Session.DoesNotExist:
        request.session.flush()
        error_message = 'The session is not active anymore, plase sign in again.'
        query_params = urlencode({'error': error_message})
        return redirect(f"{reverse('login:evaluation_login')}?{query_params}")
    
    if request.method == 'GET':
        
        return render(request, 'evaluate/evaluate.html', {
            'csrf_token_value': request.META.get('CSRF_COOKIE') 
        })