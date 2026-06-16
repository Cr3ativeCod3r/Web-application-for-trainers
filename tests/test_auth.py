import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

pytestmark = pytest.mark.django_db

def test_login_page_loads(client):
    url = reverse('accounts:login')
    response = client.get(url)
    assert response.status_code == 200
    assert 'accounts/login.html' in [t.name for t in response.templates]

def test_registration_page_loads(client):
    url = reverse('accounts:register')
    response = client.get(url)
    assert response.status_code == 200
    assert 'accounts/register.html' in [t.name for t in response.templates]

def test_user_login_success(client, test_user):
    url = reverse('accounts:login')
    data = {
        'username': 'test@example.com',
        'password': 'testpassword123'
    }
    response = client.post(url, data)
    # Upon successful login, should redirect to default login success url or next
    assert response.status_code == 302
    assert response.url != url
    
    # Check if user is authenticated
    assert '_auth_user_id' in client.session

def test_user_login_failure(client, test_user):
    url = reverse('accounts:login')
    data = {
        'username': 'test@example.com',
        'password': 'wrongpassword'
    }
    response = client.post(url, data)
    assert response.status_code == 200 # Form error, returns 200 with errors
    assert 'form' in response.context
    assert response.context['form'].errors

def test_inactive_user_cannot_login(client, inactive_user):
    url = reverse('accounts:login')
    data = {
        'username': 'inactive@example.com',
        'password': 'testpassword123'
    }
    response = client.post(url, data)
    assert response.status_code == 200
    assert 'form' in response.context
    assert response.context['form'].errors

def test_user_registration(client):
    url = reverse('accounts:register')
    data = {
        'email': 'newuser@example.com',
        'password': 'securepassword123'
    }
    response = client.post(url, data)
    
    # Assuming redirect on success
    assert response.status_code == 302
    assert response.url == reverse('accounts:registration_success')
    
    # Check if user was created
    user = User.objects.get(email='newuser@example.com')
    assert user is not None
    assert user.is_active is False # Defaults to inactive waiting for email confirmation

def test_logout(client, test_user):
    client.force_login(test_user)
    assert '_auth_user_id' in client.session
    
    url = reverse('accounts:logout')
    response = client.post(url) 
    if response.status_code == 405:
        response = client.get(url) # if get allowed
        
    assert response.status_code in [200, 302]
    assert '_auth_user_id' not in client.session
