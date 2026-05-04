const socket = io();

const roomData = document.getElementById('room-data').dataset;
const roomId   = parseInt(roomData.roomId);
const userId   = parseInt(roomData.userId);
const username = roomData.username;

let localStream   = null;
let mySocketId    = null;
let cameraEnabled = false;
let micEnabled    = true;
const peers = {};

const iceConfig = {
  iceServers: [
    { urls: 'stun:stun.l.google.com:19302' },
    { urls: 'stun:stun1.l.google.com:19302' },
  ],
};

// ── Connection ────────────────────────────────────────────────
socket.on('connect', () => {
  mySocketId = socket.id;
  socket.emit('join', { room_id: roomId, username });
});

// ── Chat ──────────────────────────────────────────────────────
function sendMessage() {
  const input = document.getElementById('chat-input');
  if (!input) return;
  const content = input.value.trim();
  if (!content) return;
  socket.emit('send_message', { room_id: roomId, user_id: userId, content });
  input.value = '';
}

socket.on('new_message', (data) => {
  const box = document.getElementById('chat-messages');
  if (!box) return;
  const isMe = data.user_id === userId;
  const div  = document.createElement('div');
  div.className = `message ${isMe ? 'message-me' : 'message-other'}`;
  div.innerHTML = `
    <small class="text-muted">${isMe ? 'Vous' : escapeHtml(data.username)} · ${data.timestamp}</small>
    <div class="message-bubble">${escapeHtml(data.content)}</div>`;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
});

socket.on('user_joined', (d) => addSystemMsg(d.message));
socket.on('user_left',   (d) => addSystemMsg(d.message));

function addSystemMsg(text) {
  const box = document.getElementById('chat-messages');
  if (!box) return;
  const div = document.createElement('div');
  div.className = 'text-center text-muted small my-2';
  div.textContent = text;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

// ── Camera ────────────────────────────────────────────────────
async function toggleCamera() {
  if (!cameraEnabled) {
    try {
      localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      const localTile  = document.getElementById('local-tile');
      const localVideo = document.getElementById('local-video');
      localVideo.srcObject = localStream;
      localTile.style.display = 'block';
      document.getElementById('no-camera-msg').style.display = 'none';
      cameraEnabled = true;

      const btn = document.getElementById('camera-btn');
      btn.innerHTML = '<i class="fas fa-video-slash me-1"></i>Couper caméra';
      btn.classList.replace('btn-success', 'btn-danger');

      const micBtn = document.getElementById('mic-btn');
      if (micBtn) micBtn.disabled = false;

      socket.emit('camera_on', { room_id: roomId, socket_id: mySocketId, username });
    } catch (e) {
      alert('Impossible d\'accéder à la caméra : ' + e.message);
    }
  } else {
    stopCamera();
  }
}

function stopCamera() {
  if (localStream) {
    localStream.getTracks().forEach(t => t.stop());
    localStream = null;
  }
  document.getElementById('local-tile').style.display = 'none';
  document.getElementById('no-camera-msg').style.display = '';
  cameraEnabled = false;

  const btn = document.getElementById('camera-btn');
  btn.innerHTML = '<i class="fas fa-video me-1"></i>Activer caméra';
  btn.classList.replace('btn-danger', 'btn-success');

  const micBtn = document.getElementById('mic-btn');
  if (micBtn) micBtn.disabled = true;

  Object.values(peers).forEach(pc => pc.close());
  Object.keys(peers).forEach(k => delete peers[k]);
  document.getElementById('remote-videos').innerHTML = '';

  socket.emit('camera_off', { room_id: roomId, socket_id: mySocketId });
}

function toggleMic() {
  if (!localStream) return;
  localStream.getAudioTracks().forEach(t => { t.enabled = !t.enabled; });
  micEnabled = !micEnabled;
  const btn = document.getElementById('mic-btn');
  btn.innerHTML = micEnabled
    ? '<i class="fas fa-microphone me-1"></i>Micro'
    : '<i class="fas fa-microphone-slash me-1"></i>Muet';
  btn.classList.toggle('btn-outline-secondary', micEnabled);
  btn.classList.toggle('btn-outline-danger', !micEnabled);
}

// ── WebRTC ────────────────────────────────────────────────────
socket.on('camera_on', async (data) => {
  if (data.socket_id === mySocketId || !cameraEnabled) return;
  await createPeer(data.socket_id, true);
});

socket.on('camera_off', (data) => {
  removePeer(data.socket_id);
});

async function createPeer(peerId, isInitiator) {
  const pc = new RTCPeerConnection(iceConfig);
  peers[peerId] = pc;

  if (localStream) {
    localStream.getTracks().forEach(t => pc.addTrack(t, localStream));
  }

  pc.ontrack = (event) => {
    let tile = document.getElementById(`tile-${peerId}`);
    if (!tile) {
      tile = document.createElement('div');
      tile.className = 'video-tile';
      tile.id = `tile-${peerId}`;
      tile.innerHTML = `<video id="vid-${peerId}" autoplay playsinline></video>`;
      document.getElementById('remote-videos').appendChild(tile);
    }
    document.getElementById(`vid-${peerId}`).srcObject = event.streams[0];
  };

  pc.onicecandidate = (event) => {
    if (event.candidate) {
      socket.emit('webrtc_ice', {
        room_id: roomId, target: peerId, from: mySocketId,
        candidate: event.candidate,
      });
    }
  };

  pc.onconnectionstatechange = () => {
    if (pc.connectionState === 'disconnected' || pc.connectionState === 'failed') {
      removePeer(peerId);
    }
  };

  if (isInitiator) {
    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);
    socket.emit('webrtc_offer', {
      room_id: roomId, target: peerId, from: mySocketId, sdp: offer,
    });
  }

  return pc;
}

function removePeer(peerId) {
  if (peers[peerId]) {
    peers[peerId].close();
    delete peers[peerId];
  }
  const tile = document.getElementById(`tile-${peerId}`);
  if (tile) tile.remove();
}

socket.on('webrtc_offer', async (data) => {
  if (data.target !== mySocketId) return;
  const pc = await createPeer(data.from, false);
  await pc.setRemoteDescription(new RTCSessionDescription(data.sdp));
  const answer = await pc.createAnswer();
  await pc.setLocalDescription(answer);
  socket.emit('webrtc_answer', {
    room_id: roomId, target: data.from, from: mySocketId, sdp: answer,
  });
});

socket.on('webrtc_answer', async (data) => {
  if (data.target !== mySocketId) return;
  const pc = peers[data.from];
  if (pc) await pc.setRemoteDescription(new RTCSessionDescription(data.sdp));
});

socket.on('webrtc_ice', async (data) => {
  if (data.target !== mySocketId) return;
  const pc = peers[data.from];
  if (pc) await pc.addIceCandidate(new RTCIceCandidate(data.candidate));
});

// ── Helpers ───────────────────────────────────────────────────
function escapeHtml(text) {
  const d = document.createElement('div');
  d.appendChild(document.createTextNode(text));
  return d.innerHTML;
}

const chatInput = document.getElementById('chat-input');
if (chatInput) {
  chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
  });
}

window.addEventListener('beforeunload', () => {
  socket.emit('leave', { room_id: roomId, username });
});
