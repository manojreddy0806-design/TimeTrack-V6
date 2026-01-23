/**
 * Store Service
 * 
 * Root-level service for all store operations.
 * Uses the centralized apiClient for all API calls.
 * 
 * All methods return promises that resolve to data or reject with normalized errors.
 */

// Import apiClient (assumes apiClient.js is loaded before this)
// Don't throw error immediately - allow graceful degradation
if (typeof apiClient === 'undefined') {
  console.warn('apiClient not loaded. StoreService will not work until apiClient.js is loaded.');
}

class StoreService {
  /**
   * List stores for the current tenant
   * 
   * @param {string|null} managerUsername - Optional manager username to filter stores
   * @returns {Promise<Array>} Array of store objects
   */
  async listStores(managerUsername = null) {
    if (typeof apiClient === 'undefined') {
      throw new Error('apiClient not loaded. Please ensure apiClient.js is loaded before StoreService.');
    }
    try {
      const params = {};
      if (managerUsername) {
        params.manager_username = managerUsername;
      }
      return await apiClient.get('/stores/', params);
    } catch (error) {
      // Re-throw with context
      error.context = 'Failed to load stores';
      throw error;
    }
  }

  /**
   * Create a new store
   * 
   * @param {Object} storeData - Store data
   * @param {string} storeData.name - Store name (required)
   * @param {string} storeData.username - Store username (required)
   * @param {string} storeData.password - Store password (required)
   * @param {number} storeData.total_boxes - Total boxes (required)
   * @param {string} [storeData.opening_time] - Opening time (HH:MM format)
   * @param {string} [storeData.closing_time] - Closing time (HH:MM format)
   * @param {string} [storeData.timezone] - Store timezone (e.g., 'America/New_York')
   * @returns {Promise<Object>} Created store object
   */
  async createStore(storeData) {
    if (typeof apiClient === 'undefined') {
      throw new Error('apiClient not loaded. Please ensure apiClient.js is loaded before StoreService.');
    }
    try {
      // Validate required fields
      if (!storeData.name) {
        throw {
          error: 'Store name is required',
          error_code: 'VALIDATION_ERROR',
          status_code: 400
        };
      }
      if (!storeData.username) {
        throw {
          error: 'Username is required',
          error_code: 'VALIDATION_ERROR',
          status_code: 400
        };
      }
      if (!storeData.password) {
        throw {
          error: 'Password is required',
          error_code: 'VALIDATION_ERROR',
          status_code: 400
        };
      }
      if (storeData.total_boxes === undefined || storeData.total_boxes === null) {
        throw {
          error: 'Total boxes is required',
          error_code: 'VALIDATION_ERROR',
          status_code: 400
        };
      }

      // Prepare payload
      const payload = {
        name: storeData.name.trim(),
        username: storeData.username.trim(),
        password: storeData.password,
        total_boxes: parseInt(storeData.total_boxes, 10),
        opening_time: storeData.opening_time || null,
        closing_time: storeData.closing_time || null,
        timezone: storeData.timezone || null
      };

      // Validate total_boxes
      if (isNaN(payload.total_boxes) || payload.total_boxes < 1) {
        throw {
          error: 'Total boxes must be a positive integer',
          error_code: 'VALIDATION_ERROR',
          status_code: 400
        };
      }

      return await apiClient.post('/stores/', payload);
    } catch (error) {
      // Re-throw with context
      error.context = 'Failed to create store';
      throw error;
    }
  }

  /**
   * Update an existing store
   * 
   * @param {Object} storeData - Store update data
   * @returns {Promise<Object>} Updated store object
   */
  async updateStore(storeData) {
    try {
      if (!storeData.name) {
        throw {
          error: 'Store name is required',
          error_code: 'VALIDATION_ERROR',
          status_code: 400
        };
      }

      return await apiClient.put('/stores/', storeData);
    } catch (error) {
      error.context = 'Failed to update store';
      throw error;
    }
  }

  /**
   * Delete a store
   * 
   * @param {string} storeName - Store name to delete
   * @returns {Promise<Object>} Success response
   */
  async deleteStore(storeName) {
    try {
      if (!storeName) {
        throw {
          error: 'Store name is required',
          error_code: 'VALIDATION_ERROR',
          status_code: 400
        };
      }

      return await apiClient.delete('/stores/', { name: storeName });
    } catch (error) {
      error.context = 'Failed to delete store';
      throw error;
    }
  }

  /**
   * Get a single store by name
   * 
   * @param {string} storeName - Store name
   * @returns {Promise<Object>} Store object
   */
  async getStore(storeName) {
    try {
      if (!storeName) {
        throw {
          error: 'Store name is required',
          error_code: 'VALIDATION_ERROR',
          status_code: 400
        };
      }

      const stores = await this.listStores();
      const store = stores.find(s => s.name === storeName);
      
      if (!store) {
        throw {
          error: `Store "${storeName}" not found`,
          error_code: 'NOT_FOUND',
          status_code: 404
        };
      }

      return store;
    } catch (error) {
      if (error.error_code) {
        throw error;
      }
      error.context = 'Failed to get store';
      throw error;
    }
  }
}

// Export singleton instance
const storeService = new StoreService();

// Export class for testing
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { StoreService, storeService };
}
