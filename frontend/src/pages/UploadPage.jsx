import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { uploadVideo } from '../api';
import { useAuth } from '../auth';
import { formatBytes, formatDuration, visibilityLabel } from '../utils';
import { CloseIcon, FilmIcon, LockIcon, UploadIcon } from '../icons';
import { useToast } from '../components/Toast';

const MAX_MB = 1024;

const FILTER_OPTIONS = [
  { value: 'none', label: 'Без фильтра', css: 'none' },
  { value: 'grayscale', label: 'Чёрно-белое', css: 'grayscale(1)' },
  { value: 'sepia', label: 'Сепия', css: 'sepia(0.85)' },
  { value: 'contrast', label: 'Контраст', css: 'contrast(1.25)' },
  { value: 'bright', label: 'Яркость', css: 'brightness(1.08)' },
  { value: 'vivid', label: 'Насыщенность', css: 'saturate(1.3) contrast(1.1)' },
];

const CROP_OPTIONS = [
  { value: 'original', label: 'Как в оригинале' },
  { value: '16:9', label: '16:9 — широкий' },
  { value: '9:16', label: '9:16 — вертикальный' },
  { value: '1:1', label: '1:1 — квадрат' },
  { value: '4:3', label: '4:3 — классический' },
];

const FILTER_CSS = Object.fromEntries(FILTER_OPTIONS.map((item) => [item.value, item.css]));
const ASPECT_CSS = {
  '16:9': '16 / 9',
  '9:16': '9 / 16',
  '1:1': '1 / 1',
  '4:3': '4 / 3',
};
const ASPECT_RATIO = {
  '16:9': 16 / 9,
  '9:16': 9 / 16,
  '1:1': 1,
  '4:3': 4 / 3,
};
const QUALITY_OPTIONS = [
  { value: '1080p', height: 1080 },
  { value: '720p', height: 720 },
  { value: '480p', height: 480 },
];

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

export default function UploadPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { push } = useToast();
  const inputRef = useRef(null);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const pendingCapture = useRef(false);

  const [file, setFile] = useState(null);
  const [videoUrl, setVideoUrl] = useState('');
  const [duration, setDuration] = useState(0);
  const [sourceSize, setSourceSize] = useState({ width: 0, height: 0 });
  const [thumbnail, setThumbnail] = useState(null);
  const [thumbPreview, setThumbPreview] = useState('');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [visibility, setVisibility] = useState('public');
  const [dragging, setDragging] = useState(false);
  const [progress, setProgress] = useState(0);
  const [uploading, setUploading] = useState(false);

  const [trimStart, setTrimStart] = useState(0);
  const [trimEnd, setTrimEnd] = useState(0);
  const [rotate, setRotate] = useState(0);
  const [flipHorizontal, setFlipHorizontal] = useState(false);
  const [flipVertical, setFlipVertical] = useState(false);
  const [cropAspect, setCropAspect] = useState('original');
  const [videoFilter, setVideoFilter] = useState('none');
  const [speed, setSpeed] = useState(1);
  const [mute, setMute] = useState(false);
  const [volume, setVolume] = useState(1);
  const [qualities, setQualities] = useState([]);

  const [thumbMode, setThumbMode] = useState('auto');
  const [frameTime, setFrameTime] = useState(0);
  const [framePreview, setFramePreview] = useState('');

  useEffect(() => {
    return () => {
      if (thumbPreview) URL.revokeObjectURL(thumbPreview);
    };
  }, [thumbPreview]);

  useEffect(() => {
    if (!file) {
      setVideoUrl('');
      return undefined;
    }
    const url = URL.createObjectURL(file);
    setVideoUrl(url);
    setDuration(0);
    setSourceSize({ width: 0, height: 0 });
    setTrimStart(0);
    setTrimEnd(0);
    setRotate(0);
    setFlipHorizontal(false);
    setFlipVertical(false);
    setCropAspect('original');
    setVideoFilter('none');
    setSpeed(1);
    setMute(false);
    setVolume(1);
    setQualities([]);
    setThumbMode('auto');
    setFrameTime(0);
    setFramePreview('');
    setThumbnail(null);
    setThumbPreview('');
    return () => URL.revokeObjectURL(url);
  }, [file]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    video.playbackRate = speed;
    video.muted = mute;
    video.volume = clamp(volume, 0, 1);
  }, [speed, mute, volume, videoUrl]);

  const editedDuration =
    duration > 0 && trimEnd > trimStart ? (trimEnd - trimStart) / speed : duration;

  const outputHeight = (() => {
    if (!sourceSize.height) return 0;
    const rotated = rotate === 90 || rotate === 270;
    const width = rotated ? sourceSize.height : sourceSize.width;
    const height = rotated ? sourceSize.width : sourceSize.height;
    const ratio = ASPECT_RATIO[cropAspect];
    if (!ratio) return height;
    return Math.round(Math.min(height, width / ratio));
  })();

  useEffect(() => {
    if (!outputHeight) return;
    setQualities((current) =>
      current.filter((quality) => {
        const option = QUALITY_OPTIONS.find((item) => item.value === quality);
        return option ? option.height < outputHeight : false;
      }),
    );
  }, [outputHeight]);

  const captureFrame = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || !video.videoWidth || !video.videoHeight) return;

    const width = video.videoWidth;
    const height = video.videoHeight;
    const rotated = rotate === 90 || rotate === 270;
    const stageWidth = rotated ? height : width;
    const stageHeight = rotated ? width : height;

    const stage = document.createElement('canvas');
    stage.width = stageWidth;
    stage.height = stageHeight;
    const stageContext = stage.getContext('2d');
    if (!stageContext) return;

    stageContext.save();
    stageContext.filter = FILTER_CSS[videoFilter] || 'none';
    stageContext.translate(stageWidth / 2, stageHeight / 2);
    stageContext.scale(flipHorizontal ? -1 : 1, flipVertical ? -1 : 1);
    stageContext.rotate((rotate * Math.PI) / 180);
    stageContext.drawImage(video, -width / 2, -height / 2, width, height);
    stageContext.restore();

    const ratio = ASPECT_RATIO[cropAspect];
    let cropWidth = stageWidth;
    let cropHeight = stageHeight;
    let cropX = 0;
    let cropY = 0;
    if (ratio) {
      if (stageWidth / stageHeight > ratio) {
        cropWidth = Math.round(stageHeight * ratio);
      } else {
        cropHeight = Math.round(stageWidth / ratio);
      }
      cropX = Math.round((stageWidth - cropWidth) / 2);
      cropY = Math.round((stageHeight - cropHeight) / 2);
    }

    const outputWidth = Math.max(1, Math.min(640, cropWidth));
    const outputHeight = Math.max(1, Math.round((cropHeight / cropWidth) * outputWidth));
    canvas.width = outputWidth;
    canvas.height = outputHeight;
    const context = canvas.getContext('2d');
    if (!context) return;
    try {
      context.drawImage(
        stage,
        cropX,
        cropY,
        cropWidth,
        cropHeight,
        0,
        0,
        outputWidth,
        outputHeight,
      );
      setFramePreview(canvas.toDataURL('image/jpeg', 0.85));
    } catch {
      // Браузер может запретить чтение кадра — тогда превью просто не покажем.
    }
  };

  const seekToFinalTime = (finalTime) => {
    const video = videoRef.current;
    if (!video || !duration) return;
    const safeFinal = clamp(finalTime, 0, Math.max(0, editedDuration - 0.1));
    const sourceTime = clamp(trimStart + safeFinal * speed, 0, Math.max(0, duration - 0.05));
    setFrameTime(safeFinal);
    video.pause();
    if (Math.abs(video.currentTime - sourceTime) < 0.01) {
      captureFrame();
    } else {
      pendingCapture.current = true;
      video.currentTime = sourceTime;
    }
  };

  useEffect(() => {
    const video = videoRef.current;
    if (thumbMode !== 'frame' || !video || !duration) return;
    const target = clamp(frameTime, 0, Math.max(0, editedDuration - 0.1));
    if (Math.abs(target - frameTime) > 0.01) setFrameTime(target);
    const sourceTime = clamp(trimStart + target * speed, 0, Math.max(0, duration - 0.05));
    if (Math.abs(video.currentTime - sourceTime) < 0.01) {
      captureFrame();
    } else {
      pendingCapture.current = true;
      video.currentTime = sourceTime;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    trimStart,
    trimEnd,
    speed,
    thumbMode,
    duration,
    rotate,
    flipHorizontal,
    flipVertical,
    cropAspect,
    videoFilter,
  ]);

  const chooseFile = (selected) => {
    if (!selected) return;
    const isVideo =
      selected.type.startsWith('video/') || /\.(mp4|webm|mov|m4v)$/i.test(selected.name);
    if (!isVideo) {
      push('Выберите видеофайл MP4, WebM, MOV или M4V', 'error');
      return;
    }
    if (selected.size > MAX_MB * 1024 * 1024) {
      push(`Файл больше ${MAX_MB} МБ`, 'error');
      return;
    }
    setFile(selected);
    if (!title.trim()) {
      setTitle(selected.name.replace(/\.[^.]+$/, '').slice(0, 200));
    }
  };

  const chooseThumbnail = (selected) => {
    if (!selected) return;
    if (!selected.type.startsWith('image/')) {
      push('Превью должно быть изображением', 'error');
      return;
    }
    if (thumbPreview) URL.revokeObjectURL(thumbPreview);
    setThumbnail(selected);
    setThumbPreview(URL.createObjectURL(selected));
  };

  const clearFile = () => {
    setFile(null);
    setProgress(0);
    if (inputRef.current) inputRef.current.value = '';
  };

  const onLoadedMetadata = () => {
    const video = videoRef.current;
    if (!video || !Number.isFinite(video.duration)) return;
    const total = video.duration;
    setDuration(total);
    setSourceSize({ width: video.videoWidth, height: video.videoHeight });
    setTrimEnd((current) => (current > 0 ? Math.min(current, total) : total));
    setFrameTime((current) => clamp(current, 0, Math.max(0, total - 0.1)));
  };

  const onTimeUpdate = () => {
    const video = videoRef.current;
    if (!video || video.paused || !duration) return;
    const isTrimmed = trimEnd > trimStart && trimEnd < duration - 0.05;
    if (isTrimmed && video.currentTime >= trimEnd) {
      video.currentTime = trimStart;
    } else if (video.currentTime < trimStart - 0.05) {
      video.currentTime = trimStart;
    }
  };

  const changeTrimStart = (value) => {
    const next = clamp(Number(value), 0, Math.max(0, trimEnd - 0.1));
    setTrimStart(next);
    if (videoRef.current) videoRef.current.currentTime = next;
  };

  const changeTrimEnd = (value) => {
    const next = clamp(Number(value), Math.min(duration, trimStart + 0.1), duration);
    setTrimEnd(next);
  };

  const resetEdits = () => {
    setTrimStart(0);
    setTrimEnd(duration);
    setRotate(0);
    setFlipHorizontal(false);
    setFlipVertical(false);
    setCropAspect('original');
    setVideoFilter('none');
    setSpeed(1);
    setMute(false);
    setVolume(1);
  };

  const switchThumbMode = (mode) => {
    setThumbMode(mode);
    if (mode === 'frame' && duration) {
      seekToFinalTime(framePreview ? frameTime : Math.min(2, Math.max(0, editedDuration / 3)));
    }
  };

  const takeCurrentFrame = () => {
    const video = videoRef.current;
    if (!video || !duration) return;
    const finalTime = clamp(
      (video.currentTime - trimStart) / speed,
      0,
      Math.max(0, editedDuration - 0.1),
    );
    seekToFinalTime(finalTime);
  };

  const submit = async (event) => {
    event.preventDefault();
    if (!file) {
      push('Сначала выберите видеофайл', 'error');
      return;
    }
    if (!title.trim()) {
      push('Укажите название', 'error');
      return;
    }
    setUploading(true);
    setProgress(0);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', title.trim());
    formData.append('description', description);
    formData.append('visibility', visibility);

    if (trimStart > 0.05) formData.append('trim_start', trimStart.toFixed(2));
    if (duration > 0 && trimEnd > 0 && trimEnd < duration - 0.05) {
      formData.append('trim_end', trimEnd.toFixed(2));
    }
    if (rotate !== 0) formData.append('rotate', String(rotate));
    if (flipHorizontal) formData.append('flip_horizontal', 'true');
    if (flipVertical) formData.append('flip_vertical', 'true');
    if (cropAspect !== 'original') formData.append('crop_aspect', cropAspect);
    if (videoFilter !== 'none') formData.append('video_filter', videoFilter);
    if (Math.abs(speed - 1) > 0.001) formData.append('speed', String(speed));
    if (mute) formData.append('mute', 'true');
    if (Math.abs(volume - 1) > 0.001) formData.append('volume', String(volume));
    if (qualities.length) formData.append('qualities', qualities.join(','));

    if (thumbMode === 'frame') {
      formData.append('thumbnail_timestamp', Math.max(0, frameTime).toFixed(2));
    } else if (thumbMode === 'upload' && thumbnail) {
      formData.append('thumbnail', thumbnail);
    }

    try {
      const video = await uploadVideo(formData, setProgress);
      push('Видео загружено');
      navigate(`/watch/${video.id}`);
    } catch (error) {
      push(error.message, 'error');
      setProgress(0);
    } finally {
      setUploading(false);
    }
  };

  const previewTransform = `rotate(${rotate}deg) scaleX(${flipHorizontal ? -1 : 1}) scaleY(${flipVertical ? -1 : 1})`;
  const previewAspect = ASPECT_CSS[cropAspect];
  const hasEdits =
    trimStart > 0.05 ||
    (duration > 0 && trimEnd > 0 && trimEnd < duration - 0.05) ||
    rotate !== 0 ||
    flipHorizontal ||
    flipVertical ||
    cropAspect !== 'original' ||
    videoFilter !== 'none' ||
    Math.abs(speed - 1) > 0.001 ||
    mute ||
    Math.abs(volume - 1) > 0.001;

  return (
    <div className="page upload-page">
      <div className="page-header">
        <div>
          <h1>Загрузка видео</h1>
          <p className="page-subtitle">Выберите файл, отредактируйте его и настройте доступ</p>
        </div>
      </div>

      <form className="upload-layout" onSubmit={submit}>
        <div className="upload-main">
          <div
            className={`dropzone ${dragging ? 'dragging' : ''} ${file ? 'has-file' : ''}`}
            onDragOver={(event) => {
              event.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(event) => {
              event.preventDefault();
              setDragging(false);
              chooseFile(event.dataTransfer.files?.[0]);
            }}
            onClick={() => !file && inputRef.current?.click()}
            role="button"
            tabIndex={0}
            onKeyDown={(event) => event.key === 'Enter' && !file && inputRef.current?.click()}
          >
            <input
              ref={inputRef}
              type="file"
              accept="video/mp4,video/webm,video/quicktime,video/x-m4v,.mp4,.webm,.mov,.m4v"
              hidden
              onChange={(event) => chooseFile(event.target.files?.[0])}
            />
            {file ? (
              <div className="file-card">
                <span className="file-icon"><FilmIcon size={30} /></span>
                <div className="file-info">
                  <strong>{file.name}</strong>
                  <span>{formatBytes(file.size)}</span>
                </div>
                <button
                  type="button"
                  className="icon-button"
                  onClick={(event) => {
                    event.stopPropagation();
                    clearFile();
                  }}
                  aria-label="Убрать файл"
                >
                  <CloseIcon size={18} />
                </button>
              </div>
            ) : (
              <>
                <span className="dropzone-icon"><UploadIcon size={38} /></span>
                <h2>Перетащите видео сюда</h2>
                <p>или нажмите, чтобы выбрать файл</p>
                <span className="muted">MP4, WebM, MOV, M4V · до {MAX_MB} МБ</span>
              </>
            )}
          </div>

          {file ? (
            <div className="form-card editor-card">
              <div className="editor-head">
                <div>
                  <h2>Редактор видео</h2>
                  <p className="hint">
                    Превью в браузере, финальные правки применит сервер при публикации.
                  </p>
                </div>
                <button type="button" className="btn btn-ghost btn-sm" onClick={resetEdits}>
                  Сбросить правки
                </button>
              </div>

              <div className="editor-preview">
                <div
                  className={`editor-preview-frame ${cropAspect !== 'original' ? 'cropped' : ''}`}
                  style={previewAspect ? { aspectRatio: previewAspect } : undefined}
                >
                  <video
                    ref={videoRef}
                    src={videoUrl}
                    controls
                    playsInline
                    preload="metadata"
                    onLoadedMetadata={onLoadedMetadata}
                    onTimeUpdate={onTimeUpdate}
                    onSeeked={() => {
                      if (!pendingCapture.current) return;
                      pendingCapture.current = false;
                      captureFrame();
                    }}
                    style={{
                      transform: previewTransform,
                      filter: FILTER_CSS[videoFilter] || 'none',
                      objectFit: cropAspect === 'original' ? 'contain' : 'cover',
                    }}
                  />
                </div>
                <div className="editor-preview-meta">
                  <span>Исходная длительность: {formatDuration(duration)}</span>
                  <span>
                    После правок: {formatDuration(editedDuration)}
                    {speed !== 1 ? ` · ${speed}x` : ''}
                  </span>
                  {hasEdits ? <span className="editor-badge">Правки будут применены</span> : null}
                </div>
              </div>

              <div className="editor-controls">
                <div className="editor-group">
                  <div className="editor-group-head">
                    <h3>Обрезка</h3>
                    <span className="muted">
                      {formatDuration(trimStart)} — {formatDuration(trimEnd)}
                    </span>
                  </div>
                  <label className="editor-range">
                    <span>Начало</span>
                    <input
                      type="range"
                      min="0"
                      max={Math.max(0.1, duration)}
                      step="0.1"
                      value={trimStart}
                      onChange={(event) => changeTrimStart(event.target.value)}
                      disabled={!duration}
                    />
                  </label>
                  <label className="editor-range">
                    <span>Конец</span>
                    <input
                      type="range"
                      min="0"
                      max={Math.max(0.1, duration)}
                      step="0.1"
                      value={trimEnd}
                      onChange={(event) => changeTrimEnd(event.target.value)}
                      disabled={!duration}
                    />
                  </label>
                </div>

                <div className="editor-group">
                  <div className="editor-group-head">
                    <h3>Поворот и отражение</h3>
                  </div>
                  <div className="editor-chip-row">
                    {[0, 90, 180, 270].map((value) => (
                      <button
                        key={value}
                        type="button"
                        className={`chip-button ${rotate === value ? 'active' : ''}`}
                        onClick={() => setRotate(value)}
                      >
                        {value === 0 ? 'Без поворота' : `${value}°`}
                      </button>
                    ))}
                  </div>
                  <div className="editor-chip-row">
                    <button
                      type="button"
                      className={`chip-button ${flipHorizontal ? 'active' : ''}`}
                      onClick={() => setFlipHorizontal((value) => !value)}
                    >
                      Отразить ↔
                    </button>
                    <button
                      type="button"
                      className={`chip-button ${flipVertical ? 'active' : ''}`}
                      onClick={() => setFlipVertical((value) => !value)}
                    >
                      Отразить ↕
                    </button>
                  </div>
                </div>

                <div className="editor-group">
                  <div className="editor-group-head">
                    <h3>Кадр и цвет</h3>
                  </div>
                  <label className="field compact">
                    <span>Формат кадра</span>
                    <select value={cropAspect} onChange={(event) => setCropAspect(event.target.value)}>
                      {CROP_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="field compact">
                    <span>Фильтр</span>
                    <select value={videoFilter} onChange={(event) => setVideoFilter(event.target.value)}>
                      {FILTER_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>

                <div className="editor-group">
                  <div className="editor-group-head">
                    <h3>Скорость и звук</h3>
                  </div>
                  <label className="editor-range">
                    <span>Скорость: {speed}x</span>
                    <input
                      type="range"
                      min="0.5"
                      max="2"
                      step="0.25"
                      value={speed}
                      onChange={(event) => setSpeed(Number(event.target.value))}
                    />
                  </label>
                  <label className="editor-check">
                    <input
                      type="checkbox"
                      checked={mute}
                      onChange={(event) => setMute(event.target.checked)}
                    />
                    <span>Отключить звук</span>
                  </label>
                  <label className="editor-range">
                    <span>Громкость: {Math.round(volume * 100)}%</span>
                    <input
                      type="range"
                      min="0"
                      max="2"
                      step="0.05"
                      value={volume}
                      onChange={(event) => setVolume(Number(event.target.value))}
                      disabled={mute}
                    />
                  </label>
                </div>

                <div className="editor-group">
                  <div className="editor-group-head">
                    <h3>Качество</h3>
                    <span className="muted">
                      {sourceSize.height ? `${sourceSize.width}×${sourceSize.height}` : 'Оригинал'}
                    </span>
                  </div>
                  <div className="editor-quality-list">
                    {QUALITY_OPTIONS.map((option) => {
                      const unavailable = !outputHeight || outputHeight <= option.height;
                      return (
                        <label
                          key={option.value}
                          className={`editor-check ${unavailable ? 'disabled' : ''}`}
                        >
                          <input
                            type="checkbox"
                            checked={qualities.includes(option.value)}
                            disabled={unavailable}
                            onChange={(event) => {
                              setQualities((current) =>
                                event.target.checked
                                  ? [...current, option.value]
                                  : current.filter((item) => item !== option.value),
                              );
                            }}
                          />
                          <span>
                            {option.value}
                            {unavailable && outputHeight ? ' — не требуется' : ''}
                          </span>
                        </label>
                      );
                    })}
                  </div>
                  <p className="hint">
                    Оригинал доступен всегда. Дополнительные версии появятся в переключателе
                    качества плеера.
                  </p>
                </div>
              </div>
            </div>
          ) : null}

          {uploading ? (
            <div className="progress-card">
              <div className="progress-head">
                <span>{progress < 100 ? 'Загрузка файла' : 'Обработка на сервере'}</span>
                <strong>{progress}%</strong>
              </div>
              <div className="progress-track">
                <div className="progress-bar" style={{ width: `${progress}%` }} />
              </div>
              <p className="muted">
                {progress < 100
                  ? 'Не закрывайте страницу до завершения загрузки.'
                  : 'Применяем правки через ffmpeg. Это может занять несколько секунд.'}
              </p>
            </div>
          ) : null}

          <div className="form-card">
            <h2>Метаданные</h2>
            <label className="field">
              <span>Название *</span>
              <input
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                placeholder="О чём это видео?"
                maxLength={200}
                required
              />
            </label>
            <label className="field">
              <span>Описание</span>
              <textarea
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                placeholder="Расскажите зрителям о видео"
                rows={5}
                maxLength={10000}
              />
            </label>
          </div>

          <div className="form-card">
            <h2>Превью</h2>
            <div className="segmented">
              <button
                type="button"
                className={thumbMode === 'auto' ? 'active' : ''}
                onClick={() => switchThumbMode('auto')}
              >
                Авто
              </button>
              <button
                type="button"
                className={thumbMode === 'frame' ? 'active' : ''}
                onClick={() => switchThumbMode('frame')}
              >
                Кадр из видео
              </button>
              <button
                type="button"
                className={thumbMode === 'upload' ? 'active' : ''}
                onClick={() => switchThumbMode('upload')}
              >
                Загрузить файл
              </button>
            </div>

            {thumbMode === 'auto' ? (
              <p className="hint">
                Если не выбрать кадр или файл, превью будет создано автоматически через ffmpeg.
              </p>
            ) : null}

            {thumbMode === 'frame' ? (
              <>
                <label className="editor-range">
                  <span>Кадр: {formatDuration(frameTime)}</span>
                  <input
                    type="range"
                    min="0"
                    max={Math.max(0.1, editedDuration)}
                    step="0.1"
                    value={frameTime}
                    onChange={(event) => seekToFinalTime(Number(event.target.value))}
                    disabled={!duration}
                  />
                </label>
                <div className="editor-inline-actions">
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    onClick={takeCurrentFrame}
                    disabled={!duration}
                  >
                    Взять текущий кадр
                  </button>
                  <span className="hint">Кадр вырезается из финального видео после обработки.</span>
                </div>
                {framePreview ? (
                  <div className="thumb-preview">
                    <img src={framePreview} alt="Кадр для превью" />
                  </div>
                ) : (
                  <p className="hint">Подвиньте ползунок или нажмите «Взять текущий кадр».</p>
                )}
              </>
            ) : null}

            {thumbMode === 'upload' ? (
              <>
                <label className="field">
                  <span>Изображение JPG, PNG или WebP</span>
                  <input
                    className="hidden-file-input"
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    onChange={(event) => chooseThumbnail(event.target.files?.[0])}
                  />
                  <span className="btn btn-ghost btn-sm file-picker">Выбрать изображение</span>
                </label>
                {thumbPreview ? (
                  <div className="thumb-preview">
                    <img src={thumbPreview} alt="Превью" />
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      onClick={() => {
                        setThumbPreview('');
                        setThumbnail(null);
                      }}
                    >
                      Убрать превью
                    </button>
                  </div>
                ) : (
                  <p className="hint">Файл превью заменит автоматически созданный кадр.</p>
                )}
              </>
            ) : null}
          </div>
        </div>

        <aside className="upload-side">
          <div className="form-card">
            <h2>Доступ</h2>
            <div className="radio-list">
              {['public', 'unlisted', 'private'].map((value) => (
                <label key={value} className={`radio-card ${visibility === value ? 'active' : ''}`}>
                  <input
                    type="radio"
                    name="visibility"
                    value={value}
                    checked={visibility === value}
                    onChange={(event) => setVisibility(event.target.value)}
                  />
                  <span>
                    <strong>{visibilityLabel(value)}</strong>
                    <small>
                      {value === 'public'
                        ? 'Видно всем в лентах и поиске'
                        : value === 'unlisted'
                          ? 'Только по прямой ссылке'
                          : 'Только владельцу и приглашённым'}
                    </small>
                  </span>
                </label>
              ))}
            </div>
            {visibility === 'private' ? (
              <p className="hint">
                <LockIcon size={14} /> После загрузки откройте видео и добавьте зрителей по username.
              </p>
            ) : null}
          </div>

          <div className="form-card upload-summary">
            <h2>Публикация</h2>
            <p className="muted">Автор: <strong>{user?.display_name || user?.username}</strong></p>
            <p className="hint">
              {hasEdits
                ? 'Видео будет перекодировано с учётом правок и заменит исходный файл.'
                : 'Видео сохранится без перекодирования.'}
            </p>
            <button type="submit" className="btn btn-primary btn-block" disabled={uploading || !file || !title.trim()}>
              {uploading ? `Загрузка… ${progress}%` : 'Опубликовать видео'}
            </button>
          </div>
        </aside>
      </form>

      <canvas ref={canvasRef} hidden />
    </div>
  );
}
