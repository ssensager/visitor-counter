/**
 * Visitor Analytics — Main Application Controller
 * Built according to Modern Web Guidance:
 * - AbortSignal.timeout() for robust fetch requests and network timeouts
 * - Keyboard accessibility for Drag-and-Drop file picker
 * - Automatic WebSocket lifecycle management with fallback polling
 * - Direct production integration with Backend REST API and MJPEG stream
 */

const App = (() => {
  // Application State
  const state = {
    currentJobId: null,
    selectedFile: null,
    jobStatus: 'idle', // 'idle' | 'uploaded' | 'processing' | 'stopped' | 'completed' | 'error'
    socket: null,
    pollTimer: null,
    healthTimer: null,
  };

  // DOM Elements
  const el = {
    dropZone: document.getElementById('drop-zone'),
    videoFileInput: document.getElementById('video-file-input'),
    fileInfoBox: document.getElementById('file-info-box'),
    selectedFileName: document.getElementById('selected-file-name'),
    selectedFileSize: document.getElementById('selected-file-size'),
    btnRemoveFile: document.getElementById('btn-remove-file'),

    btnUpload: document.getElementById('btn-upload'),
    btnUploadText: document.querySelector('#btn-upload .btn-text'),
    btnUploadSpinner: document.querySelector('#btn-upload .btn-spinner'),

    btnStart: document.getElementById('btn-start'),
    btnStop: document.getElementById('btn-stop'),
  };

  /**
   * Initialize Application
   */
  function init() {
    Dashboard.init();
    VideoPlayer.init();

    setupEventListeners();
    updateUIState('idle');

    Dashboard.addLog('Подключение к серверу аналитики...', 'info');
    startHealthChecking();
  }

  /**
   * Set up UI Event Listeners with Accessibility
   */
  function setupEventListeners() {
    // File input changes
    el.videoFileInput.addEventListener('change', handleFileSelect);

    // Keyboard support for custom drop zone (Enter or Space triggers file select)
    el.dropZone.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        el.videoFileInput.click();
      }
    });

    // Drag and Drop
    el.dropZone.addEventListener('dragover', (e) => {
      e.preventDefault();
      el.dropZone.classList.add('dragover');
    });

    el.dropZone.addEventListener('dragleave', () => {
      el.dropZone.classList.remove('dragover');
    });

    el.dropZone.addEventListener('drop', (e) => {
      e.preventDefault();
      el.dropZone.classList.remove('dragover');
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        setFile(e.dataTransfer.files[0]);
      }
    });

    // Remove file button
    el.btnRemoveFile.addEventListener('click', clearFile);

    // Control buttons
    el.btnUpload.addEventListener('click', handleUpload);
    el.btnStart.addEventListener('click', handleStart);
    el.btnStop.addEventListener('click', handleStop);
  }

  /**
   * Handle file selection from input
   */
  function handleFileSelect(e) {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
    }
  }

  /**
   * Set active file and update UI
   */
  function setFile(file) {
    const allowedExtensions = ['.mp4', '.avi'];
    const lowerName = file.name.toLowerCase();
    const isAllowed = allowedExtensions.some(ext => lowerName.endsWith(ext));

    if (!isAllowed) {
      Dashboard.showError(`Неподдерживаемый формат файла: "${file.name}". Выберите видео в формате .mp4 или .avi.`, true);
      return;
    }

    state.selectedFile = file;
    el.selectedFileName.textContent = file.name;
    el.selectedFileSize.textContent = formatBytes(file.size);

    el.dropZone.classList.add('hidden');
    el.fileInfoBox.classList.remove('hidden');

    Dashboard.hideError();
    Dashboard.addLog(`Выбран файл: ${file.name} (${formatBytes(file.size)})`, 'info');

    updateUIState('file_selected');
  }

  /**
   * Clear selected file
   */
  function clearFile() {
    state.selectedFile = null;
    el.videoFileInput.value = '';
    el.fileInfoBox.classList.add('hidden');
    el.dropZone.classList.remove('hidden');

    if (state.jobStatus !== 'processing') {
      updateUIState('idle');
    }
  }

  /**
   * Update button and input states according to current app status
   */
  function updateUIState(step) {
    switch (step) {
      case 'idle':
        el.btnUpload.disabled = true;
        el.btnStart.disabled = true;
        el.btnStop.disabled = true;
        el.videoFileInput.disabled = false;
        setUploadLoading(false);
        break;

      case 'file_selected':
        el.btnUpload.disabled = false;
        el.btnStart.disabled = true;
        el.btnStop.disabled = true;
        el.videoFileInput.disabled = false;
        setUploadLoading(false);
        break;

      case 'uploaded':
        el.btnUpload.disabled = true;
        el.btnStart.disabled = false;
        el.btnStop.disabled = true;
        el.videoFileInput.disabled = false;
        setUploadLoading(false);
        break;

      case 'processing':
        el.btnUpload.disabled = true;
        el.btnStart.disabled = true;
        el.btnStop.disabled = false;
        el.videoFileInput.disabled = true;
        setUploadLoading(false);
        break;

      case 'stopped':
      case 'completed':
        el.btnUpload.disabled = true;
        el.btnStart.disabled = true;
        el.btnStop.disabled = true;
        el.videoFileInput.disabled = false;
        setUploadLoading(false);
        break;

      case 'error':
        el.btnUpload.disabled = !state.selectedFile;
        el.btnStart.disabled = !state.currentJobId;
        el.btnStop.disabled = true;
        el.videoFileInput.disabled = false;
        setUploadLoading(false);
        break;
    }
  }

  function setUploadLoading(isLoading) {
    if (isLoading) {
      el.btnUploadText.textContent = 'Загрузка файла...';
      el.btnUploadSpinner.classList.remove('hidden');
      el.btnUpload.disabled = true;
    } else {
      el.btnUploadText.textContent = 'Загрузить файл';
      el.btnUploadSpinner.classList.add('hidden');
    }
  }

  /**
   * Server Health Check (/api/health) with AbortSignal.timeout()
   */
  async function checkHealth() {
    try {
      const response = await fetch('/api/health', {
        method: 'GET',
        cache: 'no-store',
        signal: AbortSignal.timeout(4000),
      });
      if (response.ok) {
        Dashboard.setServerHealth('online');
      } else {
        Dashboard.setServerHealth('offline');
      }
    } catch (err) {
      Dashboard.setServerHealth('offline');
    }
  }

  function startHealthChecking() {
    checkHealth();
    state.healthTimer = setInterval(checkHealth, 5000);
  }

  /**
   * 1. Upload Video (/api/video/upload)
   */
  async function handleUpload() {
    if (!state.selectedFile) return;

    setUploadLoading(true);
    Dashboard.hideError();
    Dashboard.addLog(`Загрузка "${state.selectedFile.name}" на сервер...`, 'info');

    const formData = new FormData();
    formData.append('file', state.selectedFile);

    try {
      const response = await fetch('/api/video/upload', {
        method: 'POST',
        body: formData,
        signal: AbortSignal.timeout(60000),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        const detail = data.detail || `Ошибка загрузки (код ${response.status})`;
        throw new Error(detail);
      }

      state.currentJobId = data.job_id;
      state.jobStatus = 'uploaded';

      Dashboard.setJobId(data.job_id);
      Dashboard.setStatus('uploaded');
      Dashboard.addLog(`Видео успешно загружено. Создана задача: ${data.job_id}`, 'success');

      updateUIState('uploaded');
    } catch (err) {
      state.jobStatus = 'error';
      Dashboard.setStatus('error');
      Dashboard.showError(err.message || 'Ошибка сети при загрузке видео', true);
      updateUIState('error');
    } finally {
      setUploadLoading(false);
    }
  }

  /**
   * 2. Start Processing (/api/video/start/{job_id})
   */
  async function handleStart() {
    if (!state.currentJobId) return;

    Dashboard.hideError();
    Dashboard.addLog(`Запуск анализа задачи ${state.currentJobId}...`, 'info');

    const lineCoords = VideoPlayer.getLineCoordinates();
    const payload = lineCoords ? { line: lineCoords } : {};

    try {
      const response = await fetch(`/api/video/start/${encodeURIComponent(state.currentJobId)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(10000),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        const detail = data.detail || `Ошибка запуска (код ${response.status})`;
        throw new Error(detail);
      }

      state.jobStatus = 'processing';
      Dashboard.setStatus('processing');
      Dashboard.addLog('Обработка запущена. Трансляция видеопотока...', 'success');

      updateUIState('processing');

      // Start MJPEG video stream
      VideoPlayer.setStream(state.currentJobId);

      // Connect real-time WebSocket
      connectStatsWebSocket(state.currentJobId);

    } catch (err) {
      Dashboard.setStatus('error');
      Dashboard.showError(err.message || 'Ошибка при запуске обработки', true);
      updateUIState('error');
    }
  }

  /**
   * 3. Stop Processing (/api/video/stop/{job_id})
   */
  async function handleStop() {
    if (!state.currentJobId) return;

    Dashboard.addLog(`Остановка задачи ${state.currentJobId}...`, 'warning');

    try {
      const response = await fetch(`/api/video/stop/${encodeURIComponent(state.currentJobId)}`, {
        method: 'POST',
        signal: AbortSignal.timeout(10000),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        const detail = data.detail || `Ошибка остановки (код ${response.status})`;
        throw new Error(detail);
      }

      state.jobStatus = 'stopped';
      Dashboard.setStatus('stopped');
      Dashboard.addLog('Обработка остановлена пользователем', 'warning');

      closeWebSocket();
      stopPolling();
      VideoPlayer.stopStream('stopped');
      updateUIState('stopped');

    } catch (err) {
      Dashboard.showError(err.message || 'Ошибка при остановке обработки');
    }
  }

  /**
   * Connect to WebSocket for real-time stats with fallback
   */
  function connectStatsWebSocket(jobId) {
    closeWebSocket();
    stopPolling();

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/stats/${encodeURIComponent(jobId)}`;

    Dashboard.addLog(`Подключение WebSocket: ${wsUrl}`, 'info');

    try {
      state.socket = new WebSocket(wsUrl);

      state.socket.onopen = () => {
        Dashboard.addLog('WebSocket соединение установлено', 'success');
      };

      state.socket.onmessage = (event) => {
        try {
          const stats = JSON.parse(event.data);
          handleStatsUpdate(stats);
        } catch (err) {
          console.error('Ошибка парсинга WebSocket сообщения:', err);
        }
      };

      state.socket.onerror = (err) => {
        console.warn('WebSocket ошибка. Переключение на fallback long-polling...', err);
        startPolling(jobId);
      };

      state.socket.onclose = () => {
        if (state.jobStatus === 'processing') {
          Dashboard.addLog('Соединение закрыто. Включён fallback-опрос /api/stats', 'warning');
          startPolling(jobId);
        }
      };

    } catch (err) {
      console.warn('Не удалось создать WebSocket, fallback на опрос /api/stats:', err);
      startPolling(jobId);
    }
  }

  function closeWebSocket() {
    if (state.socket) {
      state.socket.onclose = null;
      state.socket.onerror = null;
      state.socket.close();
      state.socket = null;
    }
  }

  /**
   * Fallback Polling via GET /api/stats/{job_id} with AbortSignal.timeout
   */
  function startPolling(jobId) {
    stopPolling();
    state.pollTimer = setInterval(async () => {
      try {
        const response = await fetch(`/api/stats/${encodeURIComponent(jobId)}`, {
          cache: 'no-store',
          signal: AbortSignal.timeout(3000),
        });
        if (response.ok) {
          const stats = await response.json();
          handleStatsUpdate(stats);
        }
      } catch (err) {
        console.error('Polling error:', err);
      }
    }, 500);
  }

  function stopPolling() {
    if (state.pollTimer) {
      clearInterval(state.pollTimer);
      state.pollTimer = null;
    }
  }

  /**
   * Handle incoming stats data (from WS or Polling)
   */
  function handleStatsUpdate(stats) {
    if (!stats) return;

    Dashboard.updateStats(stats);

    if (stats.status) {
      state.jobStatus = stats.status;
      if (stats.status === 'completed') {
        Dashboard.addLog('Обработка видеозаписи завершена (100%)', 'success');
        VideoPlayer.stopStream('completed');
        closeWebSocket();
        stopPolling();
        updateUIState('completed');
      } else if (stats.status === 'stopped') {
        VideoPlayer.stopStream('stopped');
        closeWebSocket();
        stopPolling();
        updateUIState('stopped');
      } else if (stats.status === 'error') {
        VideoPlayer.stopStream('stopped');
        closeWebSocket();
        stopPolling();
        updateUIState('error');
      }
    }
  }

  /**
   * Format bytes helper
   */
  function formatBytes(bytes, decimals = 1) {
    if (!+bytes) return '0 B';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
  }

  return {
    init,
  };
})();

// Bootstrap on DOM ready
document.addEventListener('DOMContentLoaded', App.init);
