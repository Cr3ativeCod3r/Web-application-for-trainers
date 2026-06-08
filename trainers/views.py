from django.shortcuts import render

def home_search_view(request):
    """
    Mockup view for the home search page.
    """
    return render(request, 'trainers/home_search.html')
