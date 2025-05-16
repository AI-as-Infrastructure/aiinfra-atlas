// Utility to POST session config to backend telemetry
export async function logSessionConfig(sessionId, config) {
  try {
    const res = await fetch('/api/telemetry/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, config })
    });
    if (!res.ok) throw new Error('Failed to log session config');
    return await res.json();
  } catch (e) {
    console.error('Error logging session config:', e);
    return null;
  }
}
