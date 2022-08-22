from datetime import datetime
from typing import List, Dict

from django.contrib import messages
from django.contrib.auth import login
from django.core.files.storage import default_storage
from django.http import HttpRequest, FileResponse, HttpResponse, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.safestring import mark_safe

from rst.validate import prettify, build_structure
from layout.build import make_pdf
from .forms import NewUserForm
from .models import Sheet



def _group_sheets(field, **kwargs) -> List[Dict]:
    keys = Sheet.objects.filter(**kwargs).values_list(field, flat=True).distinct()
    result = []
    for key in keys:
        query = {field: key}
        items = Sheet.objects.filter(**kwargs).filter(**query)
        result.append({'name': key, 'items': items})
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
        'shared': _group_sheets('system', is_shared=True, is_template=False),
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


def show_sheet(request, sheet_id, edit_content=None, pdf_file=None):
    csd = get_object_or_404(Sheet, pk=sheet_id)
    return render(
        request,
        'app_sheet/show_sheet.html',
        {
            'title': 'Sheet',
            'sheet': csd,
            'edit_content': edit_content or csd.content,
            'pdf_file': pdf_file,
            'permissions': _user_permissions(request.user, csd),
            'year': datetime.now().year,
        }
    )


def action_dispatcher(request, sheet_id):
    # No matter what we do after, we need to store the text from the form as the current content
    csd = get_object_or_404(Sheet, pk=sheet_id)
    edit_content = request.POST['sheet']
    pdf_file = None

    if 'clone' in request.POST:
        if request.user.is_authenticated:
            # Create a copy with new data
            cloned = Sheet()
            cloned.content = edit_content
            cloned.system = csd.system
            cloned.owner = request.user
            cloned.name = 'Copy of ' + csd.name
            cloned.is_shared = False
            cloned.is_template = False
            cloned.save()
            sheet_id = cloned.pk  # Show the new sheet when we redirect
        else:
            raise RuntimeError('must fix this')

    if 'save' in request.POST:
        # Save the content to saved
        csd.content = edit_content
        csd.save()
    if 'revert' in request.POST:
        # Copy the content from the saved data
        edit_content = csd.content
    if 'validate' in request.POST:
        # Check that the definition is good and prettify it
        edit_content = prettify(edit_content)
    if 'generate' in request.POST:
        # Generate PDF and store on disk
        sheet = build_structure(edit_content)
        pdf_file = make_pdf(sheet, csd.owner)

    return show_sheet(request, sheet_id, edit_content, pdf_file)


def show_file(request, file_name:str):
    name = request.user.username
    if file_name.startswith(name + '-'):
        pdf = default_storage.open('sheets/' + file_name, 'rb')
        return FileResponse(pdf)
    else:
        return HttpResponseForbidden('You cannot access sheets of other users')

def _extract_errors(html:str):
    items = html.split('<li>')
    assert len(items) %2 == 1
    for item in items[1::2]:
        idx = item.find('</li>')
        yield item[:idx].strip()

def register_request(request):
    if request.method == "POST":
        form = NewUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration . Welcome to ZeeSheet!")
            return redirect("home")

        reason = '<br>'.join(s.as_text() for s in form.errors.values())
        reason = reason.replace('* ', '<li>')
        reason = reason.replace('\n', '</li>')
        message = mark_safe("Unsuccessful registration:<br>" + reason + '</li>')
        messages.error(request, message)

    form = NewUserForm()
    return render(request=request, template_name="registration/register.html", context={"register_form": form})
