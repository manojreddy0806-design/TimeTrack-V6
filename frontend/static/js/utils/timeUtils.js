/**
 * Time utilities for 24-hour HH:MM parsing, formatting, and validation.
 * Canonical output: HH:MM (00:00–23:59). No AM/PM.
 * @see Time Input Micro-Interactions Spec
 */

(function (global) {
  'use strict';

  /** Digits-only parsing per spec:
   * 1 digit → hours, MM=00 (9 → 09:00)
   * 2 digits: 00–23 → HH:00 (19 → 19:00); 24–59 → 00:MM (45 → 00:45)
   * 3 digits → H + MM (930 → 09:30)
   * 4 digits → HH + MM (1230 → 12:30)
   * >4 digits → invalid
   */
  function parseDigitsOnly(digits) {
    const n = digits.length;
    if (n === 0) return { normalized: null, valid: false };
    if (n > 4) return { normalized: null, valid: false };
    let hh, mm;
    if (n === 1) {
      hh = parseInt(digits, 10);
      mm = 0;
    } else if (n === 2) {
      const v = parseInt(digits, 10);
      if (v >= 0 && v <= 23) {
        hh = v;
        mm = 0;
      } else if (v >= 24 && v <= 59) {
        hh = 0;
        mm = v;
      } else {
        return { normalized: null, valid: false };
      }
    } else if (n === 3) {
      hh = parseInt(digits[0], 10);
      mm = parseInt(digits.slice(1, 3), 10);
    } else {
      hh = parseInt(digits.slice(0, 2), 10);
      mm = parseInt(digits.slice(2, 4), 10);
    }
    if (isNaN(hh) || isNaN(mm)) return { normalized: null, valid: false };
    if (hh < 0 || hh > 23 || mm < 0 || mm > 59) {
      const norm = String(hh).padStart(2, '0') + ':' + String(mm).padStart(2, '0');
      return { normalized: norm, valid: false };
    }
    const normalized = String(hh).padStart(2, '0') + ':' + String(mm).padStart(2, '0');
    return { normalized, valid: true };
  }

  /**
   * Normalize raw input to canonical HH:MM.
   * Colon: "9:30" → 09:30, "19:5" → 19:05. Digits-only: 930 → 09:30, 45 → 00:45.
   * Returns { normalized: string | null, valid: boolean }.
   */
  function normalizeTime(raw) {
    if (raw == null || typeof raw !== 'string') return { normalized: null, valid: false };
    const s = raw.trim();
    if (s === '') return { normalized: '', valid: true };

    if (/:\d|\d:/.test(s)) {
      const parts = s.split(':');
      if (parts.length !== 2) return { normalized: null, valid: false };
      const ad = (parts[0].match(/\d/g) || []).join('');
      const bd = (parts[1].match(/\d/g) || []).join('');
      if (ad === '' && bd === '') return { normalized: null, valid: false };
      const hh = ad === '' ? 0 : parseInt(ad, 10);
      const mm = bd === '' ? 0 : parseInt(bd, 10);
      if (isNaN(hh) || isNaN(mm)) return { normalized: null, valid: false };
      const normalized = String(hh).padStart(2, '0') + ':' + String(mm).padStart(2, '0');
      const valid = hh >= 0 && hh <= 23 && mm >= 0 && mm <= 59;
      return { normalized, valid };
    }

    const digits = s.replace(/\D/g, '');
    return parseDigitsOnly(digits);
  }

  /**
   * Validate time. Returns { valid: boolean, error?: string }.
   * Messages: "Time is required." | "Enter a valid time in 24-hour format (HH:MM)."
   */
  function validateTime(value, required) {
    if (required && (value == null || String(value).trim() === '')) {
      return { valid: false, error: 'Time is required.' };
    }
    if (!required && (value == null || String(value).trim() === '')) {
      return { valid: true };
    }
    const { normalized, valid } = normalizeTime(String(value));
    if (normalized === null || !valid) {
      return { valid: false, error: 'Enter a valid time in 24-hour format (HH:MM).' };
    }
    return { valid: true };
  }

  /**
   * Format to canonical HH:MM. formatTime(h, m) or formatTime("HH:MM").
   */
  function formatTime(h, m) {
    if (typeof h === 'string' && m === undefined) {
      const { normalized } = normalizeTime(h);
      return normalized || '';
    }
    const hh = typeof h === 'number' ? h : parseInt(h, 10);
    const mm = typeof m === 'number' ? m : parseInt(m, 10);
    if (isNaN(hh) || isNaN(mm)) return '';
    return String(hh).padStart(2, '0') + ':' + String(mm).padStart(2, '0');
  }

  const TimeUtils = {
    parseTime: normalizeTime,
    normalizeTime: normalizeTime,
    formatTime: formatTime,
    validateTime: validateTime,
  };

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = TimeUtils;
  } else {
    global.TimeUtils = TimeUtils;
  }
})(typeof window !== 'undefined' ? window : this);
