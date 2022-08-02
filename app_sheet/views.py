from datetime import datetime

from django.http import HttpResponse, HttpRequest
from django.shortcuts import render, get_object_or_404

from .models import Sheet


def home(request):
    """Renders the home page."""
    assert isinstance(request, HttpRequest)
    return render(
        request,
        'app_sheet/index.html',
        {
            'title': 'Home Page',
            'year': datetime.now().year,
        }
    )


def contact(request):
    """Renders the contact page."""
    assert isinstance(request, HttpRequest)
    return render(
        request,
        'app_sheet/contact.html',
        {
            'title': 'Contact',
            'message': 'ZeeSheet Contact Page',
            'year': datetime.now().year,
        }
    )


def about(request):
    """Renders the about page."""
    assert isinstance(request, HttpRequest)
    return render(
        request,
        'app_sheet/about.html',
        {
            'title': 'About',
            'message': 'About ZeeSheet',
            'year': datetime.now().year,
        }
    )


def sheet_edit(request, sheet_id):
    csd = get_object_or_404(Sheet, pk=sheet_id)
    print(csd)
    print(csd.pk)
    print(csd.content)
    return render(
        request,
        'app_sheet/sheetedit.html',
        {
            'title': 'Sheet',
            'sheet': csd,
            'year': datetime.now().year,
        }
    )


def markdown_view(request):
    return HttpResponse("This is where the markdown component will go")
