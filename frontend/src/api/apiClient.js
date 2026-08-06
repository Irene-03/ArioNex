import { API_BASE } from './config';

export const createApiClient = (token, refreshToken, handleLogout, onTokenRefresh) => {
  let isRefreshing = false;
  let refreshSubscribers = [];

  const subscribeTokenRefresh = (cb) => {
    refreshSubscribers.push(cb);
  };

  const onRefreshed = (newToken) => {
    refreshSubscribers.forEach((cb) => cb(newToken));
    refreshSubscribers = [];
  };

  const executeRefresh = async () => {
    const currentRefreshToken = refreshToken || localStorage.getItem('arionex_refresh_token');
    if (!currentRefreshToken) {
      throw new Error('Refresh token not found');
    }

    const res = await fetch(`${API_BASE}/v1/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh_token: currentRefreshToken }),
    });

    if (!res.ok) {
      throw new Error('Refresh request failed');
    }

    const data = await res.json();
    return data;
  };

  return async (url, options = {}) => {
    const headers = {
      ...options.headers,
    };
    
    if (options.body && !(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
    }
    
    let currentToken = token || localStorage.getItem('arionex_token');
    if (currentToken) {
      headers['Authorization'] = `Bearer ${currentToken}`;
    }
    
    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });
      
      if (response.status === 401) {
        const currentRefreshToken = refreshToken || localStorage.getItem('arionex_refresh_token');
        if (!currentRefreshToken) {
          if (handleLogout) handleLogout();
          throw new Error('جلسه شما منقضی شده است. لطفاً مجدداً وارد شوید.');
        }

        if (!isRefreshing) {
          isRefreshing = true;
          try {
            const data = await executeRefresh();
            const newAccessToken = data.access_token;
            const newRefreshToken = data.refresh_token;

            localStorage.setItem('arionex_token', newAccessToken);
            localStorage.setItem('arionex_refresh_token', newRefreshToken);

            if (onTokenRefresh) {
              onTokenRefresh(newAccessToken, newRefreshToken);
            }

            isRefreshing = false;
            onRefreshed(newAccessToken);
          } catch (err) {
            isRefreshing = false;
            if (handleLogout) handleLogout();
            throw new Error('جلسه شما منقضی شده است. لطفاً مجدداً وارد شوید.', { cause: err });
          }
        }

        const retryRequest = new Promise((resolve) => {
          subscribeTokenRefresh((newToken) => {
            const retryHeaders = {
              ...headers,
              'Authorization': `Bearer ${newToken}`,
            };
            resolve(fetch(url, { ...options, headers: retryHeaders }));
          });
        });

        return retryRequest;
      }
      
      return response;
    } catch (err) {
      if (err.message === 'جلسه شما منقضی شده است. لطفاً مجدداً وارد شوید.') {
        throw err;
      }
      throw err;
    }
  };
};
