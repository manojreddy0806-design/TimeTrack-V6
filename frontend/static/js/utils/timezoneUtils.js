/**
 * Timezone utilities for consistent ET (America/New_York) handling in frontend.
 * 
 * All times displayed to users should be in ET.
 * Backend returns UTC timestamps (stored as naive UTC in database).
 * This module converts UTC to ET for display.
 */

/**
 * Get current time in ET (America/New_York)
 * @returns {Date} Current time in ET
 */
function nowET() {
    const now = new Date();
    // Convert to ET
    return new Date(now.toLocaleString('en-US', { timeZone: 'America/New_York' }));
}

/**
 * Convert UTC timestamp string to ET Date object
 * Handles both ISO strings with 'Z' suffix and naive UTC strings
 * @param {string} utcTimestamp - UTC timestamp string (ISO format or naive)
 * @returns {Date} Date object representing the time in ET
 */
function utcToET(utcTimestamp) {
    if (!utcTimestamp) return null;
    
    // If it's already a Date object, use it
    if (utcTimestamp instanceof Date) {
        // Convert to ET
        const etString = utcTimestamp.toLocaleString('en-US', { timeZone: 'America/New_York' });
        return new Date(etString);
    }
    
    // Parse the timestamp string
    let date;
    if (typeof utcTimestamp === 'string') {
        // If it doesn't end with 'Z', assume it's naive UTC and add 'Z'
        const normalizedTimestamp = utcTimestamp.endsWith('Z') || utcTimestamp.includes('+') || utcTimestamp.includes('-') 
            ? utcTimestamp 
            : utcTimestamp + 'Z';
        
        date = new Date(normalizedTimestamp);
    } else {
        date = new Date(utcTimestamp);
    }
    
    // Convert UTC to ET by formatting in ET timezone and parsing back
    // This handles DST automatically
    const etString = date.toLocaleString('en-US', { timeZone: 'America/New_York' });
    return new Date(etString);
}

/**
 * Format time in ET for display
 * @param {string|Date} utcTimestamp - UTC timestamp
 * @param {Object} options - Formatting options (same as toLocaleTimeString)
 * @returns {string} Formatted time string in ET
 */
function formatTimeET(utcTimestamp, options = {}) {
    const etDate = utcToET(utcTimestamp);
    if (!etDate || isNaN(etDate.getTime())) return '';
    
    const defaultOptions = {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: true,
        timeZone: 'America/New_York'
    };
    
    return etDate.toLocaleTimeString('en-US', { ...defaultOptions, ...options });
}

/**
 * Format date in ET for display
 * @param {string|Date} utcTimestamp - UTC timestamp
 * @param {Object} options - Formatting options (same as toLocaleDateString)
 * @returns {string} Formatted date string in ET
 */
function formatDateET(utcTimestamp, options = {}) {
    const etDate = utcToET(utcTimestamp);
    if (!etDate || isNaN(etDate.getTime())) return '';
    
    const defaultOptions = {
        timeZone: 'America/New_York'
    };
    
    return etDate.toLocaleDateString('en-US', { ...defaultOptions, ...options });
}

/**
 * Format date and time in ET for display
 * @param {string|Date} utcTimestamp - UTC timestamp
 * @param {Object} dateOptions - Date formatting options
 * @param {Object} timeOptions - Time formatting options
 * @returns {string} Formatted date and time string in ET
 */
function formatDateTimeET(utcTimestamp, dateOptions = {}, timeOptions = {}) {
    const etDate = utcToET(utcTimestamp);
    if (!etDate || isNaN(etDate.getTime())) return '';
    
    const dateStr = formatDateET(utcTimestamp, dateOptions);
    const timeStr = formatTimeET(utcTimestamp, timeOptions);
    return `${dateStr} ${timeStr}`;
}

/**
 * Get timezone label for ET
 * @returns {string} "ET" (handles DST automatically - shows EDT/EST based on date)
 */
function getETLabel() {
    const now = new Date();
    const etDate = new Date(now.toLocaleString('en-US', { timeZone: 'America/New_York' }));
    const utcDate = new Date(now.toLocaleString('en-US', { timeZone: 'UTC' }));
    
    // Check if DST is in effect (ET is 4 hours behind UTC in summer, 5 in winter)
    const offset = (utcDate.getTime() - etDate.getTime()) / (1000 * 60 * 60);
    return offset === 4 ? 'EDT' : 'EST';
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        nowET,
        utcToET,
        formatTimeET,
        formatDateET,
        formatDateTimeET,
        getETLabel
    };
} else {
    // Make available globally
    window.TimezoneUtils = {
        nowET,
        utcToET,
        formatTimeET,
        formatDateET,
        formatDateTimeET,
        getETLabel
    };
}
