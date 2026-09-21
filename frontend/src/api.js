export async function apiRequest(path, body) {
  let response
  try {
    response = await fetch(
      '/api' + path,
      body === undefined
        ? {}
        : {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
          }
    )
  } catch {
    throw new Error('Cannot reach the server. Check that the backend is running.')
  }
  let data
  try {
    data = await response.json()
  } catch {
    throw new Error(
      'The server returned an unexpected response. Check the backend connection.'
    )
  }
  if (!response.ok) {
    const message = Array.isArray(data.detail)
      ? data.detail.map((item) => item.msg).join(' ')
      : data.detail
    throw new Error(message || 'Something went wrong. Please try again.')
  }
  return data
}
