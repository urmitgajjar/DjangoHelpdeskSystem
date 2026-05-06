from django.contrib import messages
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse


def csrf_failure(request, reason=""):
    login_path = reverse("login")
    if request.path == login_path:
        messages.error(
            request,
            "Your login form expired in another tab. Please try signing in again.",
        )
        return redirect("login")

    return HttpResponseForbidden("CSRF verification failed. Please refresh and try again.")
