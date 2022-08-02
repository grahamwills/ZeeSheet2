from datetime import datetime
from typing import List, Dict

from django.http import HttpRequest
from django.shortcuts import render, get_object_or_404

from .models import Sheet

def _group_sheets(field, **kwargs) -> List[Dict]:
    keys = Sheet.objects.filter(**kwargs).values_list(field, flat=True).distinct()
    print('keys =', keys)
    result = []
    for key in keys:
        query = {field:key}
        items = Sheet.objects.filter(**kwargs).filter(**query)
        result.append({'name':key, 'items':items})
    print('result =', result)
    return result


def home(request):
    """Renders the home page."""
    user = request.user
    if not user.is_authenticated:
        user = None
    content = {
        'title': 'Home Page',
        'year': datetime.now().year,
        'mine': _group_sheets('system', owner=user),
        'templates': _group_sheets('system', is_template=True, is_shared=True),
        'shared': _group_sheets('system', is_shared=True),
    }

    return render(
        request,
        'app_sheet/index.html',
        content
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


def show_sheet(request, sheet_id):
    csd = get_object_or_404(Sheet, pk=sheet_id)
    return render(
        request,
        'app_sheet/show_sheet.html',
        {
            'title': 'Sheet',
            'sheet': csd,
            'year': datetime.now().year,
        }
    )
