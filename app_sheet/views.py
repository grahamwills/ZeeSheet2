from datetime import datetime
from typing import List, Dict

from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse_lazy

from rst.validate import prettify

from .models import Sheet

def _group_sheets(field, **kwargs) -> List[Dict]:
    keys = Sheet.objects.filter(**kwargs).values_list(field, flat=True).distinct()
    result = []
    for key in keys:
        query = {field:key}
        items = Sheet.objects.filter(**kwargs).filter(**query)
        result.append({'name':key, 'items':items})
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



def show_sheet(request, sheet_id, content:str=None):
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

def action_dispatcher(request, sheet_id):
    # No matter what we do after, we need to store the text from the form as the current content
    csd = get_object_or_404(Sheet, pk=sheet_id)
    csd.content = request.POST['sheet']

    if 'save' in request.POST:
        # Save the content to saved
        csd.saved = csd.content
    if 'revert' in request.POST:
        # Copy the content from the saved data
        csd.content = csd.saved
    if 'validate' in request.POST:
        # Check that the definition si good and rpettify it
        csd.content = prettify(csd.content)

    # Save the sheet and show it again!
    csd.save()
    url = reverse_lazy('sheet', kwargs={'sheet_id':sheet_id})
    return HttpResponseRedirect(url)

