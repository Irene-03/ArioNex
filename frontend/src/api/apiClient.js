export const createApiClient = (token, handleLogout) => {
  return async (url, options = {}) => {
    const headers = {
      ...options.headers,
    };
    
    if (options.body && !(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
    }
    
    const currentToken = token || localStorage.getItem('arionex_token');
    if (currentToken) {
      headers['Authorization'] = `Bearer ${currentToken}`;
    }
    
    const response = await fetch(url, {
      ...options,
      headers,
    });
    
    if (response.status === 401) {
      if (handleLogout) {
        handleLogout();
      }
      throw new Error('جلسه شما منقضی شده است. لطفاً مجدداً وارد شوید.');
    }
    
    return response;
  };
};
