const getApiBaseUrl = () => {
  const url = window.APP_RUNTIME_CONFIG?.apiBaseUrl;
  if (!url) {
    throw new Error("Missing apiBaseUrl in runtime config");
  }
  return url;
};

export default getApiBaseUrl;
