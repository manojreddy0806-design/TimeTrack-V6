/**
 * Shared TimeInput component: single-line HH:MM input, clock icon, picker-only-on-icon.
 * Uses TimeUtils for parse/format/validate. Canonical output: HH:MM (00:00–23:59).
 * @see Time Input Micro-Interactions Spec
 */

(function (global) {
  'use strict';

  if (!global.TimeUtils) {
    console.warn('TimeInput: TimeUtils required. Load utils/timeUtils.js first.');
    return;
  }

  const VISIBLE_ROWS = 5;
  const ROW_HEIGHT = 32;

  function hours() {
    return Array.from({ length: 24 }, (_, i) => String(i).padStart(2, '0'));
  }

  function minutes(step) {
    const s = Math.max(1, Math.min(15, step || 1));
    const out = [];
    for (let i = 0; i < 60; i += s) out.push(String(i).padStart(2, '0'));
    return out;
  }

  function createList(values, label, className) {
    const wrap = document.createElement('div');
    wrap.className = 'time-input-list-wrap ' + (className || '');
    const ul = document.createElement('ul');
    ul.className = 'time-input-list';
    ul.setAttribute('role', 'listbox');
    ul.setAttribute('aria-label', label);
    values.forEach((v) => {
      const li = document.createElement('li');
      li.className = 'time-input-list-item';
      li.setAttribute('role', 'option');
      li.dataset.value = v;
      li.textContent = v;
      ul.appendChild(li);
    });
    wrap.appendChild(ul);
    wrap.style.height = (VISIBLE_ROWS * ROW_HEIGHT) + 'px';
    wrap.style.overflowY = 'auto';
    return { wrap, ul, values };
  }

  function stripInvalidChars(v) {
    let hasColon = false;
    const out = [];
    for (const c of v) {
      if (/\d/.test(c)) {
        out.push(c);
      } else if (c === ':' && !hasColon) {
        hasColon = true;
        out.push(c);
      }
    }
    return out.join('');
  }

  function setupOne(root) {
    const valueId = root.getAttribute('data-value-id');
    const required = root.hasAttribute('data-required');
    const step = parseInt(root.getAttribute('data-minute-step') || '1', 10) || 1;
    const minuteStep = [1, 5, 10, 15].includes(step) ? step : 1;

    let input = root.querySelector('input[type="text"]');
    let iconBtn = root.querySelector('.time-input-icon');
    let panel = root.querySelector('.time-input-panel');
    let errEl = root.querySelector('.time-input-error');

    if (!input || !valueId) return;
    if (!input.id) input.id = valueId;

    if (!iconBtn) {
      iconBtn = document.createElement('button');
      iconBtn.type = 'button';
      iconBtn.className = 'time-input-icon';
      iconBtn.setAttribute('aria-label', 'Open time picker');
      iconBtn.setAttribute('aria-haspopup', 'listbox');
      iconBtn.setAttribute('aria-expanded', 'false');
      iconBtn.innerHTML = '<i class="fa-regular fa-clock" aria-hidden="true"></i>';
      const wrap = root.querySelector('.time-input-field-wrap');
      if (wrap) wrap.appendChild(iconBtn);
      else root.appendChild(iconBtn);
    }

    if (!panel) {
      panel = document.createElement('div');
      panel.className = 'time-input-panel';
      panel.setAttribute('role', 'dialog');
      panel.setAttribute('aria-label', 'Time picker');
      panel.hidden = true;
      const hrs = createList(hours(), 'Hours', 'time-input-hours');
      const mins = createList(minutes(minuteStep), 'Minutes', 'time-input-minutes');
      panel.appendChild(hrs.wrap);
      panel.appendChild(mins.wrap);
      root.appendChild(panel);
    }

    const hoursWrap = panel.querySelector('.time-input-hours');
    const minutesWrap = panel.querySelector('.time-input-minutes');
    const hoursList = hoursWrap && hoursWrap.querySelector('.time-input-list');
    const minutesList = minutesWrap && minutesWrap.querySelector('.time-input-list');
    const hourItems = hoursList ? hoursList.querySelectorAll('.time-input-list-item') : [];
    const minuteItems = minutesList ? minutesList.querySelectorAll('.time-input-list-item') : [];

    let pickerOpen = false;
    let selectedHour = '00';
    let selectedMinute = '00';

    function syncInputToPicker() {
      input.value = selectedHour + ':' + selectedMinute;
      input.dispatchEvent(new Event('change', { bubbles: true }));
    }

    function setError(msg) {
      root.classList.add('time-input-error-state');
      if (errEl) {
        errEl.textContent = msg || '';
        errEl.style.display = msg ? 'block' : 'none';
      }
    }

    function clearError() {
      root.classList.remove('time-input-error-state');
      if (errEl) {
        errEl.textContent = '';
        errEl.style.display = 'none';
      }
    }

    function validateAndNormalize(applyNormalize) {
      const raw = input.value.trim();
      if (required && !raw) {
        setError('Time is required.');
        return false;
      }
      if (!required && !raw) {
        clearError();
        return true;
      }
      const { normalized, valid } = global.TimeUtils.normalizeTime(raw);
      if (normalized === null) {
        setError('Enter a valid time in 24-hour format (HH:MM).');
        return false;
      }
      if (!valid) {
        setError('Enter a valid time in 24-hour format (HH:MM).');
        return false;
      }
      clearError();
      if (applyNormalize && normalized !== raw) {
        input.value = normalized;
        input.dispatchEvent(new Event('change', { bubbles: true }));
      }
      return true;
    }

    function openPicker() {
      if (pickerOpen) return;
      const raw = input.value.trim();
      if (raw) {
        const { normalized, valid } = global.TimeUtils.normalizeTime(raw);
        if (valid && normalized) {
          const [h, m] = normalized.split(':');
          selectedHour = h;
          const mm = parseInt(m, 10);
          selectedMinute = minuteStep === 1 ? m : String(Math.min(59, Math.round(mm / minuteStep) * minuteStep)).padStart(2, '0');
        } else {
          selectedHour = '00';
          selectedMinute = '00';
        }
      } else {
        selectedHour = '00';
        selectedMinute = '00';
      }
      hourItems.forEach((el) => {
        el.classList.toggle('time-input-selected', el.dataset.value === selectedHour);
        if (el.dataset.value === selectedHour) el.scrollIntoView({ block: 'nearest', behavior: 'auto' });
      });
      minuteItems.forEach((el) => {
        el.classList.toggle('time-input-selected', el.dataset.value === selectedMinute);
        if (el.dataset.value === selectedMinute) el.scrollIntoView({ block: 'nearest', behavior: 'auto' });
      });
      panel.hidden = false;
      pickerOpen = true;
      iconBtn.setAttribute('aria-expanded', 'true');
    }

    function closePicker(focusTarget) {
      if (!pickerOpen) return;
      panel.hidden = true;
      pickerOpen = false;
      iconBtn.setAttribute('aria-expanded', 'false');
      if (focusTarget === 'input') input.focus();
      else if (focusTarget === 'icon' && iconBtn) iconBtn.focus();
    }

    function commitPicker() {
      syncInputToPicker();
      clearError();
      closePicker(null);
    }

    input.addEventListener('input', function () {
      input.value = stripInvalidChars(input.value);
    });

    input.addEventListener('blur', function () {
      validateAndNormalize(true);
    });

    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        validateAndNormalize(true);
      }
    });

    input.addEventListener('focus', function () {
      // Picker does NOT open on input focus
    });

    iconBtn.addEventListener('click', function (e) {
      e.preventDefault();
      e.stopPropagation();
      if (pickerOpen) {
        closePicker('icon');
      } else {
        openPicker();
      }
    });

    iconBtn.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        iconBtn.click();
      }
    });

    hourItems.forEach((el) => {
      el.addEventListener('click', function () {
        selectedHour = el.dataset.value;
        hourItems.forEach((x) => x.classList.toggle('time-input-selected', x.dataset.value === selectedHour));
        syncInputToPicker();
      });
    });

    minuteItems.forEach((el) => {
      el.addEventListener('click', function () {
        selectedMinute = el.dataset.value;
        minuteItems.forEach((x) => x.classList.toggle('time-input-selected', x.dataset.value === selectedMinute));
        syncInputToPicker();
        commitPicker();
      });
    });

    function onDocKeydown(e) {
      if (e.key !== 'Escape' || !pickerOpen) return;
      e.preventDefault();
      e.stopPropagation();
      closePicker('input');
    }

    function onDocClick(e) {
      if (!pickerOpen) return;
      if (root.contains(e.target)) return;
      closePicker(null);
    }

    root._timeInputEsc = onDocKeydown;
    root._timeInputOutside = onDocClick;
    document.addEventListener('keydown', onDocKeydown, true);
    document.addEventListener('click', onDocClick);

    root._timeInput = {
      setValue: function (hhmm) {
        if (!hhmm || !/^([01]?\d|2[0-3]):([0-5]\d)$/.test(hhmm)) {
          input.value = '';
          clearError();
          return;
        }
        const [h, m] = hhmm.split(':');
        input.value = h.padStart(2, '0') + ':' + m.padStart(2, '0');
        clearError();
      },
      getValue: function () {
        return input.value.trim();
      },
      clear: function () {
        input.value = '';
        clearError();
        closePicker(false);
      },
      validate: function () {
        return validateAndNormalize(true);
      },
    };
  }

  function init() {
    const roots = document.querySelectorAll('[data-time-input]');
    roots.forEach(setupOne);
  }

  function clear(valueId) {
    const hidden = document.getElementById(valueId);
    if (!hidden) return;
    const root = hidden.closest('[data-time-input]');
    if (root && root._timeInput) root._timeInput.clear();
  }

  function setValue(valueId, hhmm) {
    const hidden = document.getElementById(valueId);
    if (!hidden) return;
    const root = hidden.closest('[data-time-input]');
    if (root && root._timeInput) root._timeInput.setValue(hhmm);
  }

  function getValue(valueId) {
    const el = document.getElementById(valueId);
    if (!el) return '';
    const root = el.closest('[data-time-input]');
    if (root && root._timeInput) return root._timeInput.getValue();
    return el.value || '';
  }

  const TimeInput = {
    init: init,
    clear: clear,
    setValue: setValue,
    getValue: getValue,
  };

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = TimeInput;
  } else {
    global.TimeInput = TimeInput;
  }
})(typeof window !== 'undefined' ? window : this);
