from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from .serializers import UserSerializer
from .models import User
from rest_framework_simplejwt.exceptions import TokenError


class RegisterAPIView(APIView):
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate tokens upon registration
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': serializer.data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        })

class LoginAPIView(APIView):
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        user = User.objects.filter(email=email).first()

        if user is None:
            raise AuthenticationFailed('User not found')
            
        if not user.check_password(password):
            raise AuthenticationFailed('Invalid password')

        # Generate tokens using SimpleJWT
        refresh = RefreshToken.for_user(user)
        
        response = Response()
        
        # Store the refresh token in an HTTP-only cookie
        response.set_cookie(
            key='refresh_token',
            value=str(refresh),
            httponly=True,
            samesite='Lax',
            secure=True  # Set to True if using HTTPS
        )
        
        # Send the access token in the response
        response.data = {
            'access': str(refresh.access_token)
        }

        return response

class UserView(APIView):
    def get(self, request):
        # Get the Authorization header
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            raise AuthenticationFailed("Invalid token format. Use 'Bearer <token>'")
        
        token = auth_header.split(' ')[1]
        
        try:
            # Use SimpleJWT's token backend to verify the token
            from rest_framework_simplejwt.tokens import AccessToken
            access_token = AccessToken(token)
            user_id = access_token['user_id']
            
            user = User.objects.filter(id=user_id).first()
            if not user:
                raise AuthenticationFailed("User not found")
                
            serializer = UserSerializer(user)
            return Response(serializer.data)
            
        except Exception as e:
            raise AuthenticationFailed(str(e))

class LogoutView(APIView):
    def post(self, request):
        response = Response()
        response.delete_cookie('refresh_token')
        response.data = {
            'message': 'Successfully logged out'
        }
        return response

class TokenRefreshAPIView(APIView):
    def post(self, request):
        # Try to get refresh token from cookie first
        refresh_token = request.COOKIES.get('refresh_token')
        
        # If not in cookie, check request body
        if not refresh_token:
            refresh_token = request.data.get('refresh')
            
        if not refresh_token:
            raise AuthenticationFailed('Refresh token is required')

        try:
            refresh = RefreshToken(refresh_token)
            return Response({
                'access': str(refresh.access_token)
            })
        except Exception as e:
            raise AuthenticationFailed('Invalid refresh token')
        

class TokenValidationView(APIView):
    def post(self, request):
        # Get token from various possible sources
        token = None
        auth_header = request.headers.get('Authorization')
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        else:
            token = request.data.get('token')
            
        if not token:
            return Response({
                'is_valid': False,
                'error': 'No token provided'
            }, status=400)

        try:
            # Try to parse and validate the token
            access_token = AccessToken(token)
            
            # Get additional token information
            user_id = access_token['user_id']
            user = User.objects.filter(id=user_id).first()
            
            return Response({
                'is_valid': True,
                'token_info': {
                    'user_id': user_id,
                    'user_email': user.email if user else None,
                    'expires_at': access_token['exp'],
                }
            })
            
        except TokenError as e:
            return Response({
                'is_valid': False,
                'error': str(e)
            }, status=401)
            
        except Exception as e:
            return Response({
                'is_valid': False,
                'error': 'Invalid token format'
            }, status=400)