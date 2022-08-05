from datetime import datetime
from typing import List, Dict

from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy

from rst.validate import prettify

from .models import Sheet
from .forms import NameForm


def _group_sheets(field, **kwargs) -> List[Dict]:
    keys = Sheet.objects.filter(**kwargs).values_list(field, flat=True).distinct()
    result = []
    for key in keys:
        query = {field:key}
        items = Sheet.objects.filter(**kwargs).filter(**query)
        result.append({'name':key, 'items':items})
    return result

def _user_permissions(user, sheet) -> Dict:
    return {
        'save': user == sheet.owner or user.is_superuser,
        'clone': user.is_authenticated
    }


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
            'permissions': _user_permissions(request.user, csd),
            'year': datetime.now().year,
        }
    )

def action_dispatcher(request, sheet_id):
    # No matter what we do after, we need to store the text from the form as the current content
    csd = get_object_or_404(Sheet, pk=sheet_id)
    csd.content = request.POST['sheet']

    if 'clone' in request.POST:
        if request.user.is_authenticated:
            # Create a copy with new data
            cloned = Sheet()
            cloned.content = csd.content
            cloned.saved = csd.content
            cloned.system = csd.system
            cloned.owner = request.user
            cloned.name = 'Copy of ' + csd.name
            cloned.is_shared = False
            cloned.is_template = False
            cloned.save()
            sheet_id = cloned.pk     # Show the new sheet when we redirect
        else:
            raise RuntimeError('must fix this')

    if 'save' in request.POST:
        # Save the content to saved
        csd.saved = csd.content
    if 'revert' in request.POST:
        # Copy the content from the saved data
        csd.content = csd.saved
    if 'validate' in request.POST:
        # Check that the definition is good and prettify it
        csd.content = prettify(csd.content)

    # Save the sheet and show it again!
    csd.save()
    url = reverse_lazy('sheet', kwargs={'sheet_id':sheet_id})

    return redirect(url)



def get_name(request):
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = NameForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            # process the data in form.cleaned_data as required
            # ...
            # redirect to a new URL:
            return HttpResponseRedirect('/thanks/')

    # if a GET (or any other method) we'll create a blank form
    else:
        form = NameForm()

    return render(request, 'name.html', {'form': form})