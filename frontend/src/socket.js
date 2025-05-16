import { io } from 'socket.io-client';

// Create a socket connection
const socket = io('/', {
  path: '/socket.io',
  transports: ['websocket'],
  autoConnect: true,
  reconnection: true,
  reconnectionAttempts: 5,
  reconnectionDelay: 1000
});

// Event listeners for connection status
socket.on('connect', () => {
  console.log('Socket.IO connected');
});

socket.on('disconnect', () => {
  console.log('Socket.IO disconnected');
});

socket.on('connect_error', (error) => {
  console.error('Socket.IO connection error:', error);
});

export { socket };
