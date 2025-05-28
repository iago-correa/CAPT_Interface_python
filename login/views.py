from django.shortcuts import render, redirect, reverse
from django.http import HttpResponse
from django.utils import timezone
from .models import Student, Session
from .forms import LogInStudent

def login(request):
    if request.method == "POST":
        
        login_form = LogInStudent(request.POST)
        student_id = request.POST.get('student_id')

        try:
            student = Student.objects.get(student_id=student_id)
            request.session['student_id'] = student.student_id

            student = Student.objects.get(student_id = request.session['student_id'])
            student_session = Session(student=student)
            student_session.save()
            request.session['session_id'] = student_session.id

            # return redirect('practice:practice')
            return redirect('login:session')
        except Student.DoesNotExist:
            return render(request, 'login/login.html', {'login_form': login_form, 'error': '学生番号が見つかりませんでした。'})
        
    else:
        if request.session.get('student_id'):
            return redirect('login:session')
        else:
            login_form = LogInStudent()
            success_message = request.GET.get('success', '')
            error_message = request.GET.get('error', '')
            return render(request, 'login/login.html', {'login_form': login_form, 'success': success_message, 'error': error_message})

def logout(request):
    session = Session.objects.get(id = request.session['session_id'])
    session.end_time = timezone.now()
    session.save()

    message = request.GET.get('message', '')
    
    request.session.flush()
    
    return redirect('/?success=' + message)

def session(request):
    
    if request.session.get('student_id'):
        return render(request, 'login/session.html', {})
    else:
        message = '学生番号でサインしてください。'
        return redirect('/?error=' + message)
