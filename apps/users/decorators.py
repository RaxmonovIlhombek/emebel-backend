from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if request.user.role not in roles:
                messages.error(request, "Bu sahifaga kirish huquqingiz yo'q!")
                if request.user.role == 'client':
                    return redirect('client_cabinet')
                return redirect('dashboard')
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


def staff_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.role == 'client':
            messages.error(request, "Bu sahifaga kirish huquqingiz yo'q!")
            return redirect('client_cabinet')
        return view_func(request, *args, **kwargs)
    return _wrapped


def client_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.role != 'client':
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped


def admin_required(view_func):
    return role_required('admin')(view_func)