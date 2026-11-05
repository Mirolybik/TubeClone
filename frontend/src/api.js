export class ApiError extends Error {
  constructor(message, status = 0, data = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

export class ApiClient {
  constructor(baseUrl = '/api') {
    this.baseUrl = baseUrl;
  }

  static errorMessage(data, status) {
    let detail = data && data.detail;
    if (Array.isArray(detail)) {
      detail = detail.map((item) => item.msg || item.message || String(item)).join('; ');
    }
    if (typeof detail === 'string' && detail.trim()) return detail;
    if (status === 401) return 'Требуется авторизация';
    if (status === 403) return 'Недостаточно прав';
    if (status === 404) return 'Не найдено';
    return `Ошибка ${status}`;
  }

  async request(path, { method = 'GET', body, headers = {}, signal } = {}) {
    const config = {
      method,
      credentials: 'include',
      headers: { ...headers },
      signal,
    };
    if (body !== undefined) {
      if (body instanceof FormData) {
        config.body = body;
      } else {
        config.headers['Content-Type'] = 'application/json';
        config.body = JSON.stringify(body);
      }
    }
    let response;
    try {
      response = await fetch(`${this.baseUrl}${path}`, config);
    } catch (error) {
      if (error.name === 'AbortError') throw error;
      throw new ApiError('Сервер недоступен. Проверьте подключение.', 0);
    }
    const text = await response.text();
    let data = null;
    if (text) {
      try {
        data = JSON.parse(text);
      } catch {
        data = text;
      }
    }
    if (!response.ok) {
      throw new ApiError(ApiClient.errorMessage(data, response.status), response.status, data);
    }
    return data;
  }

  get(path, options) {
    return this.request(path, { ...options, method: 'GET' });
  }

  post(path, body, options) {
    return this.request(path, { ...options, method: 'POST', body });
  }

  patch(path, body, options) {
    return this.request(path, { ...options, method: 'PATCH', body });
  }

  put(path, body, options) {
    return this.request(path, { ...options, method: 'PUT', body });
  }

  delete(path, options) {
    return this.request(path, { ...options, method: 'DELETE' });
  }

  uploadVideo(formData, onProgress) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', `${this.baseUrl}/videos`);
      xhr.withCredentials = true;
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable && onProgress) {
          onProgress(Math.round((event.loaded / event.total) * 100));
        }
      };
      xhr.onload = () => {
        let data = null;
        try {
          data = JSON.parse(xhr.responseText);
        } catch {
          data = xhr.responseText;
        }
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(data);
        } else {
          reject(new ApiError(ApiClient.errorMessage(data, xhr.status), xhr.status, data));
        }
      };
      xhr.onerror = () => reject(new ApiError('Не удалось загрузить файл. Проверьте соединение.', 0));
      xhr.onabort = () => reject(new ApiError('Загрузка отменена', 0));
      xhr.send(formData);
    });
  }

  uploadThumbnail(videoId, file) {
    const formData = new FormData();
    formData.append('thumbnail', file);
    return this.request(`/videos/${videoId}/thumbnail`, { method: 'POST', body: formData });
  }
}

export const apiClient = new ApiClient();

// Совместимые экспорты для существующих компонентов.
export const api = apiClient;
export const uploadVideo = (formData, onProgress) => apiClient.uploadVideo(formData, onProgress);
export const uploadThumbnail = (videoId, file) => apiClient.uploadThumbnail(videoId, file);
