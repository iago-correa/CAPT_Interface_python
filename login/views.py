from django.shortcuts import render, redirect, reverse
from django.http import HttpResponse
from django.utils import timezone
from .utils import get_current_period
from .models import Student, Session
from .forms import LogInStudent
import datetime
    
def try_log_in(request, student_id):

    try:
        student = Student.objects.get(student_id=student_id)
        request.session['student_id'] = student.student_id

        student = Student.objects.get(student_id = request.session['student_id'])
        student_session = Session(student=student)
        student_session.save()
        request.session['session_id'] = student_session.id
    except Student.DoesNotExist:
        login_form = LogInStudent(request.POST)
        return render(request, 'login/login.html', {'login_form': login_form, 'error': '学生番号が見つかりませんでした。'})


def login(request):
    if request.method == "POST":

        period = get_current_period()

        if period == 1:
            student_id = request.POST.get('student_id')
            try_log_in(request, student_id)
            return redirect('practice:practice')
        elif period == -1:
            login_form = LogInStudent(request.POST)
            message = '現在は実験期間外のため、ログインできません。実験期間中に再度アクセスしてください。'
            return render(request, 'login/login.html', {'login_form': login_form, 'error': message})
        else:
            student_id = request.POST.get('student_id')
            try_log_in(request, student_id)
            return redirect('record:record', t=period)
        
    else:
        if request.session.get('student_id'):
            
            period = get_current_period()

            if period == 1:
                return redirect('practice:practice')
            elif period == -1:
                request.error = '現在は実験期間外のため、ログインできません。実験期間中に再度アクセスしてください。'
                logout(request)
            else:
                return redirect('record:record', t=period)

        else:
            login_form = LogInStudent()
            success_message = request.GET.get('success', '')
            error_message = request.GET.get('error', '')
            return render(request, 'login/login.html', {'login_form': login_form, 'success': success_message, 'error': error_message})

def logout(request):

    session_id = request.session.get('session_id')
    if session_id:
        session = Session.objects.get(id = session_id)
        session.end_time = timezone.now()
        session.save()

    message = request.GET.get('message', '')
    error = request.GET.get('error', '')
    
    request.session.flush()
    
    if message:
        return redirect('/?success=' + message)
    elif error:
        return redirect('/?error=' + error)
    else:
        return redirect('login:login')

def session(request):
    
    if request.session.get('student_id'):
        return render(request, 'login/session.html', {})
    else:
        message = '学生番号でサインしてください。'
        return redirect('/?error=' + message)
