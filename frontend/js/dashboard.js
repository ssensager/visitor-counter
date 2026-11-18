/**
 * Visitor Analytics — Dashboard Module
 * Built according to Modern Web Guidance:
 * - Intl.NumberFormat and Intl.DateTimeFormat for localized formatting
 * - Native <progress> element synchronization
 * - Native <dialog> API for modal notifications (Top Layer)
 * - Screen-reader announcements via live regions (accessible-error-announcement)
 */

const Dashboard = (() => {
  // Localization formatters (Baseline Web APIs)
  const numberFormatter = new Intl.NumberFormat('ru-RU');
  const timeFormatter = new Intl.DateTimeFormat('ru-RU', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });

  // DOM Elements
  const el = {
    valEntered: document.getElementById('val-entered'),
    valExited: document.getElementById('val-exited'),
    valCurrent: document.getElementById('val-current'),
    valFps: document.getElementById('val-fps'),
    valProgressText: document.getElementById('val-progress-text'),
    nativeProgress: document.getElementById('native-progress'),

    jobStatusBadge: document.getElementById('job-status-badge'),
    jobStatusText: document.getElementById('job-status-text'),
    serverStatusDot: document.getElementById('server-status-dot'),
    serverStatusText: document.getElementById('server-status-text'),

    alertBanner: document.getElementById('alert-banner'),
    alertText: document.getElementById('alert-text'),
    alertCloseBtn: document.getElementById('alert-close-btn'),

    // Modern Native <dialog>
    errorDialog: document.getElementById('error-dialog'),
    dialogErrorMsg: document.getElementById('dialog-error-msg'),
    dialogCloseBtn: document.getElementById('dialog-close-btn'),
    dialogOkBtn: document.getElementById('dialog-ok-btn'),

    activityLog: document.getElementById('activity-log'),
    btnClearLog: document.getElementById('btn-clear-log'),
    jobIdDisplay: document.getElementById('job-id-display'),
    srAnnouncer: document.getElementById('sr-announcer'),
  };

  // State cache for smooth counter animations
  const cachedValues = {
    entered: 0,
    exited: 0,
    current: 0,
  };

  const statusTranslations = {
    idle: { label: 'Ожидание', badgeClass: 'badge-idle' },
    uploaded: { label: 'Загружено', badgeClass: 'badge-uploaded' },
    processing: { label: 'Обработка', badgeClass: 'badge-processing' },
    stopped: { label: 'Остановлено', badgeClass: 'badge-stopped' },
    completed: { label: 'Завершено', badgeClass: 'badge-completed' },
    error: { label: 'Ошибка', badgeClass: 'badge-error' },
  };

  /**
   * Accessible announcement for screen readers
   */
  function announce(text) {
    if (el.srAnnouncer) {
      el.srAnnouncer.textContent = text;
    }
  }

  /**
   * Smooth number transition effect with Intl formatting
   */
  function animateNumber(element, start, end, duration = 300) {
    if (!element) return;
    if (start === end) {
      element.textContent = numberFormatter.format(end);
      return;
    }

    const startTime = performance.now();
    const diff = end - start;

    function step(currentTime) {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const current = Math.round(start + diff * progress);
      element.textContent = numberFormatter.format(current);

      if (progress < 1) {
        requestAnimationFrame(step);
      } else {
        element.textContent = numberFormatter.format(end);
      }
    }

    requestAnimationFrame(step);
  }

  /**
   * Update metric cards and status from stats response
   */
  function updateStats(stats) {
    if (!stats) return;

    // Entered
    if (typeof stats.entered === 'number') {
      animateNumber(el.valEntered, cachedValues.entered, stats.entered);
      cachedValues.entered = stats.entered;
    }

    // Exited
    if (typeof stats.exited === 'number') {
      animateNumber(el.valExited, cachedValues.exited, stats.exited);
      cachedValues.exited = stats.exited;
    }

    // Current (balance)
    if (typeof stats.current === 'number') {
      animateNumber(el.valCurrent, cachedValues.current, stats.current);
      cachedValues.current = stats.current;
    } else if (typeof stats.entered === 'number' && typeof stats.exited === 'number') {
      const calcCurrent = stats.entered - stats.exited;
      animateNumber(el.valCurrent, cachedValues.current, calcCurrent);
      cachedValues.current = calcCurrent;
    }

    // FPS
    if (typeof stats.fps === 'number') {
      el.valFps.textContent = stats.fps.toFixed(1);
    } else if (stats.fps === null) {
      el.valFps.textContent = '0.0';
    }

    // Progress (Native <progress>)
    if (typeof stats.progress === 'number' && stats.progress !== null) {
      const percent = Math.min(Math.max(Math.round(stats.progress * 100), 0), 100);
      el.valProgressText.textContent = `${percent}%`;
      if (el.nativeProgress) {
        el.nativeProgress.value = percent;
      }
    }

    // Status
    if (stats.status) {
      setStatus(stats.status);
    }

    // Job ID
    if (stats.job_id) {
      setJobId(stats.job_id);
    }

    // Error message from stats
    if (stats.error) {
      showError(stats.error);
    }
  }

  /**
   * Set task status badge
   */
  function setStatus(statusKey) {
    const info = statusTranslations[statusKey] || { label: statusKey, badgeClass: 'badge-idle' };
    el.jobStatusText.textContent = info.label;
    el.jobStatusBadge.className = 'badge ' + info.badgeClass;

    announce(`Статус задачи: ${info.label}`);
  }

  /**
   * Set server health indicator
   */
  function setServerHealth(state) {
    el.serverStatusDot.className = 'health-dot';
    if (state === 'online') {
      el.serverStatusDot.classList.add('health-online');
      el.serverStatusText.textContent = 'Сервер: онлайн';
    } else if (state === 'offline') {
      el.serverStatusDot.classList.add('health-offline');
      el.serverStatusText.textContent = 'Сервер: нет связи';
    } else {
      el.serverStatusDot.classList.add('health-checking');
      el.serverStatusText.textContent = 'Сервер: проверка';
    }
  }

  /**
   * Set current Job ID in footer
   */
  function setJobId(jobId) {
    el.jobIdDisplay.textContent = jobId ? `Задача: ${jobId}` : 'Задача: —';
  }

  /**
   * Display error alert banner & optional modal dialog
   */
  function showError(message, asModal = false) {
    if (!message) return;
    el.alertText.textContent = message;
    el.alertBanner.classList.remove('hidden');
    addLog(`Ошибка: ${message}`, 'error');
    announce(`Ошибка: ${message}`);

    if (asModal && el.errorDialog && typeof el.errorDialog.showModal === 'function') {
      el.dialogErrorMsg.textContent = message;
      try {
        el.errorDialog.showModal();
      } catch (e) {
        // Fallback
      }
    }
  }

  /**
   * Hide error alert banner
   */
  function hideError() {
    el.alertBanner.classList.add('hidden');
  }

  /**
   * Add entry to Activity Log with clean formatting
   */
  function addLog(message, type = 'info') {
    if (!el.activityLog) return;

    const entry = document.createElement('div');
    entry.className = `log-entry log-${type}`;

    const timeStr = timeFormatter.format(new Date());

    const timeSpan = document.createElement('time');
    timeSpan.className = 'log-time';
    timeSpan.textContent = timeStr;

    const msgSpan = document.createElement('span');
    msgSpan.className = 'log-msg';
    msgSpan.textContent = message;

    entry.appendChild(timeSpan);
    entry.appendChild(msgSpan);

    el.activityLog.appendChild(entry);
    el.activityLog.scrollTop = el.activityLog.scrollHeight;
  }

  /**
   * Clear activity log
   */
  function clearLog() {
    if (!el.activityLog) return;
    el.activityLog.innerHTML = '';
    addLog('Журнал очищен', 'info');
  }

  /**
   * Reset all counters and metrics to zero
   */
  function reset() {
    cachedValues.entered = 0;
    cachedValues.exited = 0;
    cachedValues.current = 0;

    el.valEntered.textContent = '0';
    el.valExited.textContent = '0';
    el.valCurrent.textContent = '0';
    el.valFps.textContent = '0.0';
    el.valProgressText.textContent = '0%';
    if (el.nativeProgress) {
      el.nativeProgress.value = 0;
    }

    setStatus('idle');
    setJobId(null);
    hideError();
  }

  /**
   * Initialize event handlers
   */
  function init() {
    if (el.alertCloseBtn) {
      el.alertCloseBtn.addEventListener('click', hideError);
    }
    if (el.btnClearLog) {
      el.btnClearLog.addEventListener('click', clearLog);
    }

    // Modern Native <dialog> handlers
    if (el.dialogCloseBtn && el.errorDialog) {
      el.dialogCloseBtn.addEventListener('click', () => el.errorDialog.close());
    }
    if (el.dialogOkBtn && el.errorDialog) {
      el.dialogOkBtn.addEventListener('click', () => el.errorDialog.close());
    }
    if (el.errorDialog) {
      el.errorDialog.addEventListener('click', (e) => {
        const rect = el.errorDialog.getBoundingClientRect();
        const isInDialog = (
          rect.top <= e.clientY &&
          e.clientY <= rect.top + rect.height &&
          rect.left <= e.clientX &&
          e.clientX <= rect.left + rect.width
        );
        if (!isInDialog) {
          el.errorDialog.close();
        }
      });
    }
  }

  return {
    init,
    updateStats,
    setStatus,
    setServerHealth,
    setJobId,
    showError,
    hideError,
    addLog,
    clearLog,
    reset,
  };
})();
