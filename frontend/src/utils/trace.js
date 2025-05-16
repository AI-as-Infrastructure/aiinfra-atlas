// frontend/src/utils/trace.js

// Generate a 16-byte (32 hex chars) trace ID
export function generateTraceId() {
  return Array.from({ length: 32 }, () => Math.floor(Math.random() * 16).toString(16)).join('');
}

// Generate an 8-byte (16 hex chars) span ID
export function generateSpanId() {
  return Array.from({ length: 16 }, () => Math.floor(Math.random() * 16).toString(16)).join('');
}

// Generate a W3C traceparent header value
export function generateTraceparent() {
  // version (00), trace-id, span-id, trace-flags (01 = sampled)
  return `00-${generateTraceId()}-${generateSpanId()}-01`;
} 