from django import forms

class LogInStudent(forms.Form):
    student_id = forms.CharField(
        label="学生番号",
        max_length=10,
        widget=forms.TextInput(attrs={'class': 'form-control'}) 
    )
    