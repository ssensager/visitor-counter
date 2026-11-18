/**
 * Visitor Analytics — Video & Virtual Line Module
 * Built according to Modern Web Guidance:
 * - Pointer Events API (pointerdown/pointermove/pointerup + setPointerCapture)
 * - HiDPI (devicePixelRatio) buffer scaling for crisp 4K/Retina canvas rendering
 * - Clean, minimalist virtual line representation with smooth anti-aliased handles
 */

const VideoPlayer = (() => {
  // DOM Elements
  const el = {
    viewport: document.getElementById('video-viewport'),
    streamImage: document.getElementById('stream-image'),
    lineCanvas: document.getElementById('line-canvas'),
    emptyState: document.getElementById('video-empty-state'),
    emptyStateHint: document.getElementById('empty-state-hint'),
    completedOverlay: document.getElementById('video-completed-overlay'),
    streamInfo: document.getElementById('stream-info'),
    liveIndicator: document.getElementById('live-indicator'),
    lineIndicator: document.getElementById('line-indicator'),
    btnResetLine: document.getElementById('btn-reset-line'),
  };

  let ctx = null;
  let isCustomLine = false;
  let dpr = window.devicePixelRatio || 1;

  // Normalized line coordinates (from 0.0 to 1.0)
  let line = {
    p1: { x: 0.0, y: 0.5 },
    p2: { x: 1.0, y: 0.5 },
  };

  let isDragging = false;
  let dragPoint = null; // 'p1' | 'p2'

  /**
   * Initialize canvas and unified Pointer Events
   */
  function init() {
    if (!el.lineCanvas) return;
    ctx = el.lineCanvas.getContext('2d');

    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    // Modern Pointer Events API (Unified Mouse, Touch & Stylus)
    el.lineCanvas.addEventListener('pointerdown', handlePointerDown);
    el.lineCanvas.addEventListener('pointermove', handlePointerMove);
    el.lineCanvas.addEventListener('pointerup', handlePointerUp);
    el.lineCanvas.addEventListener('pointercancel', handlePointerUp);

    if (el.btnResetLine) {
      el.btnResetLine.addEventListener('click', () => {
        resetLine();
        Dashboard.addLog('Виртуальная линия сброшена на центр', 'info');
      });
    }

    renderLine();
  }

  /**
   * Resize canvas buffer with devicePixelRatio for crisp rendering on Retina/HiDPI
   */
  function resizeCanvas() {
    if (!el.lineCanvas) return;
    dpr = window.devicePixelRatio || 1;
    const rect = el.lineCanvas.getBoundingClientRect();

    if (rect.width > 0 && rect.height > 0) {
      el.lineCanvas.width = Math.round(rect.width * dpr);
      el.lineCanvas.height = Math.round(rect.height * dpr);
      renderLine();
    }
  }

  /**
   * Reset line to default center horizontal
   */
  function resetLine() {
    line = {
      p1: { x: 0.0, y: 0.5 },
      p2: { x: 1.0, y: 0.5 },
    };
    isCustomLine = false;
    if (el.lineIndicator) {
      el.lineIndicator.textContent = 'Линия: по центру';
    }
    renderLine();
  }

  /**
   * Render Minimalist Virtual Line on Canvas
   */
  function renderLine() {
    if (!ctx || !el.lineCanvas) return;
    const w = el.lineCanvas.width;
    const h = el.lineCanvas.height;

    ctx.clearRect(0, 0, w, h);

    const x1 = line.p1.x * w;
    const y1 = line.p1.y * h;
    const x2 = line.p2.x * w;
    const y2 = line.p2.y * h;

    ctx.save();

    const lineColor = isCustomLine ? '#38bdf8' : '#10b981';

    // 1. Subtle Outer Glow
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.strokeStyle = isCustomLine ? 'rgba(56, 189, 248, 0.2)' : 'rgba(16, 185, 129, 0.2)';
    ctx.lineWidth = 5 * dpr;
    ctx.stroke();

    // 2. Crisp Dashed Line
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.strokeStyle = lineColor;
    ctx.lineWidth = 2 * dpr;
    ctx.setLineDash([6 * dpr, 5 * dpr]);
    ctx.stroke();
    ctx.setLineDash([]);

    // 3. Circular Endpoint Handles
    drawHandle(x1, y1, lineColor);
    drawHandle(x2, y2, lineColor);

    // 4. Directional Center Label
    const midX = (x1 + x2) / 2;
    const midY = (y1 + y2) / 2;
    drawDirectionLabel(midX, midY, lineColor);

    ctx.restore();
  }

  function drawHandle(x, y, color) {
    ctx.beginPath();
    ctx.arc(x, y, 6 * dpr, 0, Math.PI * 2);
    ctx.fillStyle = '#ffffff';
    ctx.fill();
    ctx.strokeStyle = color;
    ctx.lineWidth = 2 * dpr;
    ctx.stroke();
  }

  function drawDirectionLabel(x, y, color) {
    ctx.save();
    const fontSize = Math.max(9 * dpr, 10);
    ctx.font = `500 ${fontSize}px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`;
    const text = 'Линия контроля';
    const textMetrics = ctx.measureText(text);
    const boxW = textMetrics.width + 14 * dpr;
    const boxH = 18 * dpr;

    // Clean pill container
    ctx.fillStyle = 'rgba(18, 19, 22, 0.9)';
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.15)';
    ctx.lineWidth = 1 * dpr;

    ctx.beginPath();
    ctx.roundRect(x - boxW / 2, y - boxH / 2, boxW, boxH, 4 * dpr);
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = '#f4f4f5';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(text, x, y);
    ctx.restore();
  }

  /**
   * Pointer Events handling
   */
  function getPointerCoords(e) {
    const rect = el.lineCanvas.getBoundingClientRect();
    return {
      x: (e.clientX - rect.left) / rect.width,
      y: (e.clientY - rect.top) / rect.height,
    };
  }

  function handlePointerDown(e) {
    el.lineCanvas.setPointerCapture(e.pointerId);

    const coords = getPointerCoords(e);
    const rect = el.lineCanvas.getBoundingClientRect();
    const pixelDistP1 = Math.hypot((coords.x - line.p1.x) * rect.width, (coords.y - line.p1.y) * rect.height);
    const pixelDistP2 = Math.hypot((coords.x - line.p2.x) * rect.width, (coords.y - line.p2.y) * rect.height);

    isDragging = true;
    dragPoint = pixelDistP1 < pixelDistP2 ? 'p1' : 'p2';
    updateDrag(coords);
  }

  function handlePointerMove(e) {
    if (!isDragging) return;
    const coords = getPointerCoords(e);
    updateDrag(coords);
  }

  function handlePointerUp(e) {
    if (isDragging) {
      isDragging = false;
      dragPoint = null;
      try {
        el.lineCanvas.releasePointerCapture(e.pointerId);
      } catch (err) {}
    }
  }

  function updateDrag(coords) {
    const clampedX = Math.max(0, Math.min(1, coords.x));
    const clampedY = Math.max(0, Math.min(1, coords.y));

    if (dragPoint === 'p1') {
      line.p1 = { x: clampedX, y: clampedY };
    } else if (dragPoint === 'p2') {
      line.p2 = { x: clampedX, y: clampedY };
    }

    isCustomLine = true;
    if (el.lineIndicator) {
      el.lineIndicator.textContent = 'Линия: настроена';
    }
    renderLine();
  }

  /**
   * Get line coordinates scaled to target video resolution
   */
  function getLineCoordinates(actualWidth = 1280, actualHeight = 720) {
    if (!isCustomLine) {
      return null;
    }
    return [
      [Math.round(line.p1.x * actualWidth), Math.round(line.p1.y * actualHeight)],
      [Math.round(line.p2.x * actualWidth), Math.round(line.p2.y * actualHeight)],
    ];
  }

  /**
   * Activate MJPEG stream display
   */
  function setStream(jobId) {
    if (!jobId) return;

    el.emptyState.classList.add('hidden');
    el.completedOverlay.classList.add('hidden');

    const streamUrl = `/api/video/stream/${encodeURIComponent(jobId)}`;
    el.streamImage.src = streamUrl;
    el.streamImage.classList.remove('hidden');

    el.streamImage.onerror = () => {
      Dashboard.addLog('Ожидание подключения к видеопотоку MJPEG...', 'warning');
    };

    el.liveIndicator.classList.remove('hidden');
    el.streamInfo.textContent = `Прямой эфир - Задача ${jobId}`;

    resizeCanvas();
  }

  /**
   * Stop active stream display
   */
  function stopStream(reason = 'stopped') {
    el.streamImage.src = '';
    el.streamImage.classList.add('hidden');
    el.liveIndicator.classList.add('hidden');

    if (reason === 'completed') {
      el.completedOverlay.classList.remove('hidden');
      el.emptyState.classList.add('hidden');
      el.streamInfo.textContent = 'Обработка завершена';
    } else {
      el.completedOverlay.classList.add('hidden');
      el.emptyState.classList.remove('hidden');
      el.streamInfo.textContent = 'Поток остановлен';
    }
  }

  /**
   * Reset video player to empty initial state
   */
  function reset() {
    stopStream('reset');
    resetLine();
    el.emptyState.classList.remove('hidden');
    el.completedOverlay.classList.add('hidden');
    el.streamInfo.textContent = 'Ожидание запуска';
  }

  return {
    init,
    resizeCanvas,
    resetLine,
    renderLine,
    getLineCoordinates,
    setStream,
    stopStream,
    reset,
    getCanvas: () => el.lineCanvas,
    getViewport: () => el.viewport,
  };
})();
