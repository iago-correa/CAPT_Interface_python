from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def demo(request):
    
    return render(request, 'kengaku/demo.html')