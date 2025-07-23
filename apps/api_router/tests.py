from django.test import TestCase, Client
from django.urls import reverse
import json


class HealthCheckTestCase(TestCase):
    def setUp(self):
        self.client = Client()
    
    def test_ping_endpoint(self):
        """Test that ping endpoint returns 200 OK"""
        response = self.client.get('/api/v1/ping')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['status'], 'ok')
        self.assertIn('timestamp', data)
    
    def test_health_check_endpoint(self):
        """Test that health check endpoint works"""
        response = self.client.get('/api/v1/health')
        
        # Should be 200 or 503 depending on service availability
        self.assertIn(response.status_code, [200, 503])
        
        data = response.json()
        self.assertIn('status', data)
        self.assertIn('timestamp', data)
        self.assertIn('services', data)
        
        # Check that we're testing database and redis
        services = data['services']
        self.assertIn('database', services)
        self.assertIn('redis', services)