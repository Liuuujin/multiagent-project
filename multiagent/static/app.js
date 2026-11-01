// 多智能体系统前端逻辑
(function () {
  const roleListEl = document.getElementById('roleList');
  const pipelineEl = document.getElementById('pipeline');
  const logEl = document.getElementById('log');
  const statusBadge = document.getElementById('statusBadge');
  const taskInput = document.getElementById('taskInput');
  const runBtn = document.getElementById('runBtn');

  const roles = {};   // key -> role
  const pipelineOrder = ['pm', 'architect', 'developer', 'tester', 'reviewer'];
  const activeStates = {};  // key -> 'active'|'done'

  // ---- 加载角色 ----
  async function loadRoles() {
    const res = await fetch('/api/roles');
    const data = await res.json();
    data.forEach(r => {
      roles[r.key] = r;
      const item = document.createElement('div');
      item.className = 'role-item';
      item.id = 'role-' + r.key;
      item.innerHTML = `
        <span class="icon">${r.icon}</span>
        <div class="info">
          <div class="name">${r.name}</div>
          <div class="desc">${r.description}</div>
        </div>
        <span class="dot" style="background:${r.color}"></span>`;
      roleListEl.appendChild(item);
    });
    renderPipeline();
  }

  // ---- 渲染流程条 ----
  function renderPipeline() {
    pipelineEl.innerHTML = '';
    pipelineOrder.forEach((key, i) => {
      const r = roles[key];
      if (!r) return;
      const node = document.createElement('div');
      node.className = 'pipe-node';
      node.id = 'pipe-' + key;
      node.innerHTML = `<span class="icon">${r.icon}</span><span>${r.name}</span>`;
      pipelineEl.appendChild(node);
      if (i < pipelineOrder.length - 1) {
        const arrow = document.createElement('span');
        arrow.className = 'pipe-arrow';
        arrow.textContent = '→';
        pipelineEl.appendChild(arrow);
      }
    });
  }

  // ---- 更新节点状态 ----
  function setNodeState(key, state) {
    activeStates[key] = state;
    const node = document.getElementById('pipe-' + key);
    if (node) {
      node.classList.remove('active', 'done');
      if (state === 'active') node.classList.add('active');
      if (state === 'done') node.classList.add('done');
    }
    const roleItem = document.getElementById('role-' + key);
    if (roleItem) {
      roleItem.classList.remove('active');
      if (state === 'active') roleItem.classList.add('active');
    }
  }

  // ---- 添加日志 ----
  function addLog(roleKey, name, content, color) {
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    entry.style.borderLeftColor = color || '#4f8cff';
    const time = new Date().toLocaleTimeString();
    entry.innerHTML = `
      <div class="head">
        <span class="name">${name}</span>
        <span class="time">${time}</span>
      </div>
      <div class="body"></div>`;
    const body = entry.querySelector('.body');
    // 简单转义 + 代码块高亮
    body.textContent = content;
    logEl.appendChild(entry);
    logEl.scrollTop = logEl.scrollHeight;
  }

  // ---- 设置状态徽章 ----
  function setStatus(text, cls) {
    statusBadge.textContent = text;
    statusBadge.className = 'status' + (cls ? ' ' + cls : '');
  }

  // ---- 启动任务 ----
  async function runTask() {
    const task = taskInput.value.trim();
    if (!task) { alert('请输入任务描述'); return; }
    runBtn.disabled = true;
    setStatus('运行中...', 'running');
    logEl.innerHTML = '';
    pipelineOrder.forEach(k => setNodeState(k, ''));
    const res = await fetch('/api/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task })
    });
    const data = await res.json();
    if (!data.ok) {
      setStatus('错误', '');
      runBtn.disabled = false;
      alert(data.error || '启动失败');
    }
  }

  // ---- SSE 事件流 ----
  function connectSSE() {
    const es = new EventSource('/api/events');
    es.onmessage = (e) => {
      let msg;
      try { msg = JSON.parse(e.data); } catch { return; }
      handleEvent(msg.type, msg.data);
    };
    es.onerror = () => { /* 自动重连 */ };
  }

  function handleEvent(type, data) {
    switch (type) {
      case 'snapshot':
        // 恢复历史
        if (data.history && data.history.length) {
          logEl.innerHTML = '';
          data.history.forEach(h => addLog(h.role, h.name, h.content, roles[h.role]?.color));
          pipelineOrder.forEach(k => setNodeState(k, 'done'));
          if (data.running) setStatus('运行中...', 'running');
          else { setStatus('完成', 'done'); runBtn.disabled = false; }
        }
        break;
      case 'run_start':
        setStatus('运行中...', 'running');
        break;
      case 'agent_start':
        setNodeState(data.role, 'active');
        break;
      case 'agent_done':
        setNodeState(data.role, 'done');
        addLog(data.role, data.name, data.content, roles[data.role]?.color);
        break;
      case 'loop_capped':
        addLog('system', '流程终止', data.message || '已达最大迭代次数', '#e67e22');
        break;
      case 'run_end':
        setStatus('完成', 'done');
        runBtn.disabled = false;
        break;
      case 'error':
        setStatus('错误', '');
        runBtn.disabled = false;
        addLog('error', '系统错误', data.message, '#e74c3c');
        break;
    }
  }

  // ---- 加载模型信息 ----
  async function loadConfig() {
    const el = document.getElementById('modelBadge');
    if (!el) return;
    try {
      const res = await fetch('/api/config');
      const cfg = await res.json();
      el.textContent = cfg.label;
      if (cfg.mock) {
        el.classList.add('mock');
        el.title = '当前为模拟模式：流程真实执行，但文本由规则模板生成，非真实模型推理';
      } else {
        el.title = `推理后端：${cfg.provider} · 模型：${cfg.model}`;
      }
    } catch (e) {
      el.textContent = '模型状态未知';
      el.classList.add('mock');
    }
  }

  // ---- 初始化 ----
  runBtn.addEventListener('click', runTask);
  loadConfig();
  loadRoles();
  connectSSE();
})();
