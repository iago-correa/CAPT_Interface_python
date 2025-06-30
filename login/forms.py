from django import forms

class LogInStudent(forms.Form):
    student_id = forms.CharField(
        label="学生番号",
        max_length=10,
        widget=forms.TextInput(attrs={'class': 'form-control'}) 
    )

class LogInRater(forms.Form):
    rater_id = forms.CharField(
        label="ID",
        max_length=10,
        widget=forms.TextInput(attrs={'class': 'form-control'}) 
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput, 
        max_length=20
    )