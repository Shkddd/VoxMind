/* VoxMind Frontend App */
const API = '/api/v1';

// --- Navigation ---
document.querySelectorAll('.nav-links a').forEach(a => {
  a.addEventListener('click', e => {
    e.preventDefault();
    const page = a.dataset.page;
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById(`page-${page}`).classList.add('active');
    document.querySelectorAll('.nav-links a').forEach(l => l.classList.remove('active'));
    a.classList.add('active');
    if (page === 'home') loadHome();
  });
});

// --- Home ---
async function loadHome() {
  const list = document.getElementById('recent-list');
  list.innerHTML = '<div class="loading">加载中...</div>';
  try {
    const r = await fetch(`${API}/audio/search?q=&limit=20`);
    const data = await r.json();
    list.innerHTML = '';
    if (!data.results || data.results.length === 0) {
      list.innerHTML = '<div class="loading">暂无录音记录，上传后会自动出现在这里。</div>';
      document.getElementById('stat-recordings').textContent = '0';
      document.getElementById('stat-hours').textContent = '0';
      return;
    }
    document.getElementById('stat-recordings').textContent = data.total;

    let totalHours = 0;
    data.results.forEach(item => {
      const div = document.createElement('div');
      div.className = 'recording-item';
      div.innerHTML = `
        <div class="recording-title">${item.title || '未命名会议'}</div>
        <div class="recording-meta">${item.recorded_at || '—'}</div>
        <div class="recording-snippet">${item.summary_snippet || ''}</div>
      `;
      div.addEventListener('click', () => {
        document.getElementById('search-input').value = item.title;
        document.querySelector('[data-page="search"]').click();
        doSearch(item.title);
      });
      list.appendChild(div);
    });
    document.getElementById('stat-hours').textContent = totalHours.toFixed(1);
  } catch (err) {
    list.innerHTML = `<div class="loading">加载失败: ${err.message}</div>`;
  }
}

// --- Search ---
document.getElementById('search-btn').addEventListener('click', () => doSearch());
document.getElementById('search-input').addEventListener('keydown', e => {
  if (e.key === 'Enter') doSearch();
});

async function doSearch(query) {
  const input = document.getElementById('search-input');
  const q = query || input.value.trim();
  if (!q) return;

  const results = document.getElementById('search-results');
  results.innerHTML = '<div class="loading">搜索中...</div>';

  try {
    const r = await fetch(`${API}/audio/search?q=${encodeURIComponent(q)}&limit=10`);
    const data = await r.json();
    results.innerHTML = '';
    if (!data.results || data.results.length === 0) {
      results.innerHTML = '<div class="loading">未找到相关会议记录。</div>';
      return;
    }
    data.results.forEach(item => {
      const div = document.createElement('div');
      div.className = 'recording-item';
      div.innerHTML = `
        <div class="recording-title">${item.title || '未命名会议'}</div>
        <div class="recording-meta">
          ${item.recorded_at || '—'} · 相关度 ${(item.relevance_score * 100).toFixed(0)}%
        </div>
        <div class="recording-snippet">${item.summary_snippet || ''}</div>
      `;
      results.appendChild(div);
    });
  } catch (err) {
    results.innerHTML = `<div class="loading">搜索失败: ${err.message}</div>`;
  }
}

// --- Chat ---
const chatMessages = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-input');
const chatBtn = document.getElementById('chat-btn');

chatBtn.addEventListener('click', () => sendChat());
chatInput.addEventListener('keydown', e => {
  if (e.key === 'Enter') sendChat();
});

function addMessage(role, text, sources) {
  const div = document.createElement('div');
  div.className = `chat-message ${role}`;
  let html = `<div class="msg-bubble">${text}</div>`;
  if (sources && sources.length > 0) {
    html += `<div class="msg-sources">来源: ${sources.map(s => s.title).join(', ')}</div>`;
  }
  div.innerHTML = html;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

async function sendChat() {
  const question = chatInput.value.trim();
  if (!question) return;

  addMessage('user', question);
  chatInput.value = '';
  chatBtn.disabled = true;
  chatBtn.textContent = '思考中...';

  try {
    const r = await fetch(`${API}/chat/question`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    });
    const data = await r.json();
    addMessage('assistant', data.answer, data.sources);
  } catch (err) {
    addMessage('assistant', `错误：${err.message}`);
  } finally {
    chatBtn.disabled = false;
    chatBtn.textContent = '发送';
  }
}

// --- Init ---
loadHome();
