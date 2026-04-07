from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me_view(request):
    user = request.user
    return Response({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'is_staff': user.is_staff,
    })


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/token/', TokenObtainPairView.as_view()),
    path('api/auth/token/refresh/', TokenRefreshView.as_view()),
    path('api/auth/me/', me_view),
    path('api/accounts/', include('apps.accounts.urls')),
    path('api/cpc/', include('apps.cpc.urls')),
    path('api/sales/', include('apps.sales.urls')),
    path('api/todos/', include('apps.todos.urls')),
    path('api/messaging/', include('apps.messaging.urls')),
    path('api/emails/', include('apps.emails.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
