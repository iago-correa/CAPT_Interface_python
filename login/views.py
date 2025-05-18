from django.shortcuts import render
from django.http import HttpResponse

def login_view(request):
    # return HttpResponse("Login view")
    return render(request, 'login/login.html')

def logout_view(request):
    return HttpResponse("Logout view")
    #return render(request, 'login/logout.html')

def sessions_view(request, student_id):
    return HttpResponse("%s" % student_id)
    #return render(request, 'login/session.html')