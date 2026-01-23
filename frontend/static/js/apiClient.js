/**
 * Root-level API Client
 * 
 * Provides a centralized API client with:
 * - Automatic baseURL from environment config
 * - Automatic Authorization header attachment
 * - Consistent headers (Content-Type: application/json)
 * - Error normalization (401, 403, 404, 5xx)
 * - Request ID tracking
 */

// Get API base URL from environment or default
function getApiBaseUrl() {
  // Check for environment-specific config
  if (window.API_BASE_URL) {
    return window.API_BASE_URL;
  }
  // Default to /api
  return '/api';
}

// Generate a unique request ID for tracking
function generateRequestId() {
  return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

// Normalize API errors into consistent format
function normalizeError(error, statusCode, requestId) {
  const normalized = {
    error: 'An error occurred',
    error_code: 'UNKNOWN_ERROR',
    status_code: statusCode || 500,
    request_id: requestId
  };

  // Try to parse error message
  let errorMessage = error;
  if (typeof error === 'object' && error !== null) {
    if (error.error) {
      errorMessage = error.error;
    } else if (error.message) {
      errorMessage = error.message;
    } else {
      errorMessage = JSON.stringify(error);
    }
  }

  normalized.error = errorMessage;

  // Map status codes to error codes
  if (statusCode === 401) {
    normalized.error_code = 'UNAUTHORIZED';
    if (!normalized.error || normalized.error === 'An error occurred') {
      normalized.error = 'Authentication required. Please login.';
    }
  } else if (statusCode === 403) {
    normalized.error_code = 'FORBIDDEN';
    if (!normalized.error || normalized.error === 'An error occurred') {
      normalized.error = 'Insufficient permissions';
    }
  } else if (statusCode === 404) {
    normalized.error_code = 'NOT_FOUND';
    if (!normalized.error || normalized.error === 'An error occurred') {
      normalized.error = 'Resource not found';
    }
  } else if (statusCode === 400) {
    normalized.error_code = 'BAD_REQUEST';
  } else if (statusCode === 422) {
    normalized.error_code = 'VALIDATION_ERROR';
  } else if (statusCode >= 500) {
    normalized.error_code = 'SERVER_ERROR';
    if (!normalized.error || normalized.error === 'An error occurred') {
      normalized.error = 'Server error. Please try again later.';
    }
  }

  // Preserve error_code from backend if present
  if (error && typeof error === 'object' && error.error_code) {
    normalized.error_code = error.error_code;
  }

  // Preserve metadata from backend if present
  if (error && typeof error === 'object' && error.metadata) {
    normalized.metadata = error.metadata;
  }

  return normalized;
}

// Load session from localStorage
function loadSession() {
  try {
    const sessionStr = localStorage.getItem('session');
    if (!sessionStr) return null;
    return JSON.parse(sessionStr);
  } catch (e) {
    console.error('Error loading session:', e);
    return null;
  }
}

/**
 * Root-level API Client
 */
class ApiClient {
  constructor(baseUrl = null) {
    this.baseUrl = baseUrl || getApiBaseUrl();
  }

  /**
   * Get default headers with authentication
   */
  getHeaders() {
    const headers = {
      'Content-Type': 'application/json'
    };

    const session = loadSession();
    if (session?.token) {
      headers['Authorization'] = `Bearer ${session.token}`;
    }

    return headers;
  }

  /**
   * Make a GET request
   */
  async get(path, params = {}) {
    const requestId = generateRequestId();
    const url = new URL(this.baseUrl + path, window.location.origin);
    
    // Add query parameters
    Object.keys(params).forEach(key => {
      if (params[key] !== null && params[key] !== undefined) {
        url.searchParams.append(key, params[key]);
      }
    });

    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: this.getHeaders()
      });

      const responseText = await response.text();
      let data;

      try {
        data = responseText ? JSON.parse(responseText) : null;
      } catch (e) {
        // Not JSON, use text
        data = responseText;
      }

      if (!response.ok) {
        const error = normalizeError(data, response.status, requestId);
        throw error;
      }

      return data;
    } catch (error) {
      // If already normalized, rethrow
      if (error.error_code) {
        throw error;
      }
      // Otherwise normalize
      throw normalizeError(error, error.status || 500, requestId);
    }
  }

  /**
   * Make a POST request
   */
  async post(path, data = {}) {
    const requestId = generateRequestId();

    try {
      const response = await fetch(this.baseUrl + path, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify(data)
      });

      const responseText = await response.text();
      let responseData;

      // Handle empty response
      if (!responseText || responseText.trim() === '') {
        if (response.ok) {
          return { success: true, status: response.status, request_id: requestId };
        }
        responseData = { error: 'Empty response from server' };
      } else {
        try {
          responseData = JSON.parse(responseText);
        } catch (e) {
          responseData = { error: responseText };
        }
      }

      if (!response.ok) {
        const error = normalizeError(responseData, response.status, requestId);
        throw error;
      }

      return responseData;
    } catch (error) {
      // If already normalized, rethrow
      if (error.error_code) {
        throw error;
      }
      // Otherwise normalize
      throw normalizeError(error, error.status || 500, requestId);
    }
  }

  /**
   * Make a PUT request
   */
  async put(path, data = {}) {
    const requestId = generateRequestId();

    try {
      const response = await fetch(this.baseUrl + path, {
        method: 'PUT',
        headers: this.getHeaders(),
        body: JSON.stringify(data)
      });

      const responseText = await response.text();
      let responseData;

      if (!responseText || responseText.trim() === '') {
        if (response.ok) {
          return { success: true, status: response.status, request_id: requestId };
        }
        responseData = { error: 'Empty response from server' };
      } else {
        try {
          responseData = JSON.parse(responseText);
        } catch (e) {
          responseData = { error: responseText };
        }
      }

      if (!response.ok) {
        const error = normalizeError(responseData, response.status, requestId);
        throw error;
      }

      return responseData;
    } catch (error) {
      if (error.error_code) {
        throw error;
      }
      throw normalizeError(error, error.status || 500, requestId);
    }
  }

  /**
   * Make a DELETE request
   */
  async delete(path, data = {}) {
    const requestId = generateRequestId();

    try {
      const options = {
        method: 'DELETE',
        headers: this.getHeaders()
      };

      // Include body if data provided
      if (data && Object.keys(data).length > 0) {
        options.body = JSON.stringify(data);
      }

      const response = await fetch(this.baseUrl + path, options);

      const responseText = await response.text();
      let responseData;

      if (!responseText || responseText.trim() === '') {
        if (response.ok) {
          return { success: true, status: response.status, request_id: requestId };
        }
        responseData = { error: 'Empty response from server' };
      } else {
        try {
          responseData = JSON.parse(responseText);
        } catch (e) {
          responseData = { error: responseText };
        }
      }

      if (!response.ok) {
        const error = normalizeError(responseData, response.status, requestId);
        throw error;
      }

      return responseData;
    } catch (error) {
      if (error.error_code) {
        throw error;
      }
      throw normalizeError(error, error.status || 500, requestId);
    }
  }
}

// Export singleton instance
const apiClient = new ApiClient();

// Export class for custom instances
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { ApiClient, apiClient };
}
