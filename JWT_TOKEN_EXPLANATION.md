# Understanding JWT Token Authentication

This document explains how JWT token authentication works, particularly focusing on access and refresh tokens, with implementation examples in both basic API calls and Flutter.

## Basic Concept

When you log in, you receive two tokens:
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

## How It Works

1. **Normal API Access**: Use access token in Authorization header
```bash
curl http://localhost:8000/api/patients/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

2. **When Access Token Expires**: You'll get an error
```json
{
    "detail": "Token is invalid or expired",
    "code": "token_not_valid"
}
```

3. **Getting New Access Token**: Use refresh token
```bash
curl -X POST http://localhost:8000/api/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh":"YOUR_REFRESH_TOKEN"}'
```

Response:
```json
{
    "access": "NEW_ACCESS_TOKEN_HERE..."
}
```

## Frontend Implementation Examples

### Basic JavaScript Example
```javascript
async function apiCall(url) {
    try {
        // Try API call with access token
        const response = await fetch(url, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
            }
        });

        if (response.status === 401) { // Token expired
            // Use refresh token to get new access token
            const refreshResponse = await fetch('/api/token/refresh/', {
                method: 'POST',
                body: JSON.stringify({
                    refresh: localStorage.getItem('refreshToken')
                })
            });

            const newTokens = await refreshResponse.json();
            localStorage.setItem('accessToken', newTokens.access);

            // Retry original API call
            return fetch(url, {
                headers: {
                    'Authorization': `Bearer ${newTokens.access}`
                }
            });
        }

        return response;
    } catch (error) {
        window.location.href = '/login';
    }
}
```

### Flutter Implementation

#### 1. Auth Service
```dart
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage';

class AuthService {
  final storage = const FlutterSecureStorage();
  final String baseUrl = 'http://your-api-url/api';

  // Login and store tokens
  Future<bool> login(String username, String password) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/login/'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'username': username,
          'password': password,
        }),
      );

      if (response.statusCode == 200) {
        final tokens = jsonDecode(response.body);
        await storage.write(key: 'access_token', value: tokens['access']);
        await storage.write(key: 'refresh_token', value: tokens['refresh']);
        return true;
      }
      return false;
    } catch (e) {
      print('Login error: $e');
      return false;
    }
  }

  Future<String?> getAccessToken() async {
    return await storage.read(key: 'access_token');
  }

  Future<bool> refreshToken() async {
    try {
      final refreshToken = await storage.read(key: 'refresh_token');
      if (refreshToken == null) return false;

      final response = await http.post(
        Uri.parse('$baseUrl/token/refresh/'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'refresh': refreshToken}),
      );

      if (response.statusCode == 200) {
        final newTokens = jsonDecode(response.body);
        await storage.write(key: 'access_token', value: newTokens['access']);
        return true;
      }
      return false;
    } catch (e) {
      print('Refresh token error: $e');
      return false;
    }
  }

  Future<void> logout() async {
    await storage.delete(key: 'access_token');
    await storage.delete(key: 'refresh_token');
  }
}
```

#### 2. API Service
```dart
class ApiService {
  final AuthService _authService = AuthService();
  final String baseUrl = 'http://your-api-url/api';

  Future<dynamic> get(String endpoint) async {
    try {
      final response = await _makeRequest(() async {
        final token = await _authService.getAccessToken();
        return await http.get(
          Uri.parse('$baseUrl/$endpoint'),
          headers: {
            'Authorization': 'Bearer $token',
            'Content-Type': 'application/json',
          },
        );
      });
      
      return jsonDecode(response.body);
    } catch (e) {
      print('API error: $e');
      rethrow;
    }
  }

  Future<http.Response> _makeRequest(Future<http.Response> Function() request) async {
    final response = await request();
    
    if (response.statusCode == 401) {
      final refreshed = await _authService.refreshToken();
      if (refreshed) {
        return await request();
      } else {
        throw Exception('Session expired');
      }
    }
    
    return response;
  }
}
```

#### 3. Example Usage in Flutter Screen
```dart
class PatientsScreen extends StatefulWidget {
  @override
  _PatientsScreenState createState() => _PatientsScreenState();
}

class _PatientsScreenState extends State<PatientsScreen> {
  final ApiService _apiService = ApiService();
  List<dynamic> patients = [];
  bool isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadPatients();
  }

  Future<void> _loadPatients() async {
    try {
      final data = await _apiService.get('patients/');
      setState(() {
        patients = data;
        isLoading = false;
      });
    } catch (e) {
      print('Error loading patients: $e');
      setState(() => isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Patients')),
      body: isLoading
          ? Center(child: CircularProgressIndicator())
          : ListView.builder(
              itemCount: patients.length,
              itemBuilder: (context, index) {
                final patient = patients[index];
                return ListTile(
                  title: Text(patient['full_name']),
                  subtitle: Text('Age: ${patient['age']}'),
                  onTap: () {
                    // Navigate to patient details
                  },
                );
              },
            ),
    );
  }
}
```

## Required Flutter Dependencies
Add these to your `pubspec.yaml`:
```yaml
dependencies:
  flutter:
    sdk: flutter
  http: ^1.1.0
  flutter_secure_storage: ^9.0.0
```

## Simplified Version (For Internal Use)

For internal applications with long-lived tokens, you can use this simpler version that just redirects to login when the token expires:

```dart
class ApiService {
  final AuthService _authService = AuthService();
  final String baseUrl = 'http://your-api-url/api';

  Future<dynamic> get(String endpoint) async {
    try {
      final token = await _authService.getAccessToken();
      final response = await http.get(
        Uri.parse('$baseUrl/$endpoint'),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json',
        },
      );
      
      if (response.statusCode == 401) {
        // Token expired, navigate to login
        Navigator.of(navigatorKey.currentContext!).pushReplacementNamed('/login');
        throw Exception('Session expired');
      }
      
      return jsonDecode(response.body);
    } catch (e) {
      print('API error: $e');
      rethrow;
    }
  }
}
```

This simplified version is more appropriate for internal applications where:
1. Tokens have long expiration times (30-90 days)
2. Security requirements are less stringent
3. User experience prioritizes simplicity over continuous session maintenance