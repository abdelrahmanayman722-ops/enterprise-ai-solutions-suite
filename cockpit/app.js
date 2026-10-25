/**
 * Executive Pipeline Cockpit - Client Application Engine
 * Architecture: Clean Vanilla ES6 State Engine, Drag-and-Drop Kanban, Real-Time Telemetry
 * Eng. Abdelrahman Rashad | Global Revenue Engine
 */

(function () {
  'use strict';

  // --- Constants & Config ---
  const API_BASE = '';
  const STAGES = ['leads', 'pitched', 'interviewing', 'contract_sent', 'won', 'closed'];
  const STAGE_LABELS = {
    leads: 'محتمل (Leads)',
    pitched: 'تم التقديم (Pitched)',
    interviewing: 'مقابلات (Interviewing)',
    contract_sent: 'إرسال العقد (Contract Sent)',
    won: 'عقود نشطة (Won / Active)',
    closed: 'مؤرشف / ملغى (Closed)',
  };

  // --- App State ---
  const state = {
    deals: [],
    opportunities: [],
    metrics: {
      active_monthly_revenue: 0,
      annual_recurring_revenue: 0,
      in_flight_pipeline_value: 0,
      total_pipeline_value: 0,
      win_rate: 0,
      total_deals: 0,
      stage_breakdown: {},
    },
    activeTab: 'kanban',
    filters: {
      minSalary: 3500,
      tags: '',
      source: '',
      search: '',
    },
    activePitch: {
      position: '',
      company: '',
      skills: [],
      tone: 'cto',
      subject: '',
      body: '',
    },
    draggedDealId: null,
    isOffline: false,
  };

  // --- DOM Elements ---
  const dom = {
    apiStatusPill: document.getElementById('api-status-pill'),
    apiStatusDot: document.getElementById('api-status-dot'),
    apiStatusText: document.getElementById('api-status-text'),

    // KPI Metrics
    mrrValue: document.getElementById('kpi-mrr-value'),
    arrValue: document.getElementById('kpi-arr-value'),
    inFlightValue: document.getElementById('kpi-inflight-value'),
    winRateValue: document.getElementById('kpi-winrate-value'),
    totalValue: document.getElementById('kpi-total-value'),

    // Views & Tabs
    tabKanban: document.getElementById('tab-kanban'),
    tabExplorer: document.getElementById('tab-explorer'),
    viewKanban: document.getElementById('view-kanban'),
    viewExplorer: document.getElementById('view-explorer'),
    kanbanCountBadge: document.getElementById('kanban-count-badge'),
    explorerCountBadge: document.getElementById('explorer-count-badge'),

    // Kanban board
    kanbanBoard: document.getElementById('kanban-board'),

    // Explorer
    explorerTableBody: document.getElementById('explorer-table-body'),
    searchInput: document.getElementById('search-input'),
    salaryFilter: document.getElementById('salary-filter'),
    tagFilter: document.getElementById('tag-filter'),
    sourceFilter: document.getElementById('source-filter'),

    // Actions
    syncBtn: document.getElementById('btn-sync-feeds'),
    addDealBtn: document.getElementById('btn-add-deal'),
    exportJsonBtn: document.getElementById('btn-export-json'),
    exportCsvBtn: document.getElementById('btn-export-csv'),

    // Pitch Drawer
    pitchDrawerOverlay: document.getElementById('pitch-drawer-overlay'),
    closePitchDrawerBtn: document.getElementById('close-pitch-drawer'),
    pitchTargetRole: document.getElementById('pitch-target-role'),
    pitchSubject: document.getElementById('pitch-subject'),
    pitchBody: document.getElementById('pitch-body'),
    toneCtobtn: document.getElementById('tone-cto'),
    toneFounderbtn: document.getElementById('tone-founder'),
    toneFreelancebtn: document.getElementById('tone-freelance'),
    copyPitchBtn: document.getElementById('btn-copy-pitch'),
    mailPitchBtn: document.getElementById('btn-mail-pitch'),

    // Add Deal Modal
    addDealModal: document.getElementById('add-deal-modal'),
    closeAddDealBtn: document.getElementById('close-add-deal-modal'),
    cancelAddDealBtn: document.getElementById('btn-cancel-add-deal'),
    addDealForm: document.getElementById('add-deal-form'),

    // Toast Container
    toastContainer: document.getElementById('toast-container'),
  };

  // --- Utility Functions ---

  function formatCurrency(val) {
    const num = Number(val) || 0;
    return '$' + Math.round(num).toLocaleString('en-US');
  }

  function showToast(message, type = 'success') {
    if (!dom.toastContainer) return;
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    const icon = type === 'success' ? 'fa-check-circle' : 'fa-info-circle';
    toast.innerHTML = `<i class="fas ${icon}"></i> <span>${escapeHtml(message)}</span>`;
    dom.toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(15px)';
      toast.style.transition = 'all 0.25s ease';
      setTimeout(() => toast.remove(), 250);
    }, 3200);
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // --- Network & Data Layer ---

  async function checkHealth() {
    try {
      const res = await fetch(`${API_BASE}/api/health`, { method: 'GET' });
      if (res.ok) {
        state.isOffline = false;
        if (dom.apiStatusDot) dom.apiStatusDot.classList.remove('offline');
        if (dom.apiStatusText) dom.apiStatusText.textContent = 'متصل بالخادم (Port 8000)';
      } else {
        throw new Error('Health check returned non-200');
      }
    } catch (err) {
      state.isOffline = true;
      if (dom.apiStatusDot) dom.apiStatusDot.classList.add('offline');
      if (dom.apiStatusText) dom.apiStatusText.textContent = 'وضع عدم الاتصال (Offline Demo)';
    }
  }

  async function fetchPipeline() {
    try {
      const res = await fetch(`${API_BASE}/api/pipeline`);
      if (!res.ok) throw new Error('Failed to load pipeline');
      const data = await res.json();
      state.deals = data.deals || [];
    } catch (err) {
      console.warn('Network error fetching pipeline; using local state.', err);
    }
  }

  async function fetchMetrics() {
    try {
      const res = await fetch(`${API_BASE}/api/metrics`);
      if (!res.ok) throw new Error('Failed to load metrics');
      state.metrics = await res.json();
    } catch (err) {
      calculateClientMetrics();
    }
    renderMetrics();
  }

  function calculateClientMetrics() {
    let mrr = 0;
    let inFlight = 0;
    let total = 0;
    let won = 0;
    let closed = 0;

    state.deals.forEach((d) => {
      const val = Number(d.monthly_value) || 0;
      total += val;
      if (d.stage === 'won') {
        mrr += val;
        won++;
      } else if (d.stage === 'interviewing' || d.stage === 'contract_sent') {
        inFlight += val;
      } else if (d.stage === 'closed') {
        closed++;
      }
    });

    const decisionTotal = won + closed;
    const winRate = decisionTotal > 0 ? (won / decisionTotal) * 100 : 0;

    state.metrics = {
      active_monthly_revenue: mrr,
      annual_recurring_revenue: mrr * 12,
      in_flight_pipeline_value: inFlight,
      total_pipeline_value: total,
      win_rate: Number(winRate.toFixed(1)),
      total_deals: state.deals.length,
      stage_breakdown: {},
    };
  }

  async function fetchOpportunities() {
    try {
      const queryParams = new URLSearchParams();
      if (state.filters.minSalary) queryParams.set('min_salary', state.filters.minSalary);
      if (state.filters.tags) queryParams.set('tags', state.filters.tags);
      if (state.filters.source) queryParams.set('source', state.filters.source);
      if (state.filters.search) queryParams.set('search', state.filters.search);

      const res = await fetch(`${API_BASE}/api/opportunities?${queryParams.toString()}`);
      if (res.ok) {
        state.opportunities = await res.json();
      }
    } catch (err) {
      console.warn('Error fetching opportunities:', err);
    }
    renderOpportunities();
  }

  // --- Deal Mutations ---

  async function updateDealStage(dealId, newStage) {
    const deal = state.deals.find((d) => d.id === dealId);
    if (!deal || deal.stage === newStage) return;

    const oldStage = deal.stage;
    deal.stage = newStage;
    deal.updated_at = new Date().toISOString();

    // Optimistic re-render
    renderKanban();
    calculateClientMetrics();
    renderMetrics();

    try {
      const res = await fetch(`${API_BASE}/api/pipeline/${dealId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ stage: newStage }),
      });
      if (res.ok) {
        showToast(`تم نقل الصفقة إلى: ${STAGE_LABELS[newStage] || newStage}`);
      } else {
        throw new Error('Failed to update stage on server');
      }
    } catch (err) {
      showToast('خطأ في حفظ المرحلة على الخادم، تم التحديث محلياً', 'info');
    }
  }

  async function deleteDeal(dealId) {
    if (!confirm('هل أنت متأكد من حذف هذه الصفقة من مسار الصفقات؟')) return;

    state.deals = state.deals.filter((d) => d.id !== dealId);
    renderKanban();
    calculateClientMetrics();
    renderMetrics();

    try {
      await fetch(`${API_BASE}/api/pipeline/${dealId}`, { method: 'DELETE' });
      showToast('تم حذف الصفقة بنجاح');
    } catch (err) {
      showToast('تم الحذف محلياً (فشل الاتصال بالخادم)', 'info');
    }
  }

  async function addDeal(dealData) {
    try {
      const res = await fetch(`${API_BASE}/api/pipeline`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(dealData),
      });
      if (res.ok) {
        const created = await res.json();
        state.deals.push(created);
        showToast('تمت إضافة الصفقة الجديدة بنجاح! 🚀');
      } else {
        throw new Error('Server rejected creation');
      }
    } catch (err) {
      const localDeal = {
        id: `deal-loc-${Date.now().toString(16)}`,
        ...dealData,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      state.deals.push(localDeal);
      showToast('تمت الإضافة محلياً (الخادم غير متصل)', 'info');
    }

    renderKanban();
    calculateClientMetrics();
    renderMetrics();
  }

  // --- Rendering UI Components ---

  function renderMetrics() {
    const m = state.metrics;
    if (dom.mrrValue) dom.mrrValue.textContent = formatCurrency(m.active_monthly_revenue) + '/ش';
    if (dom.arrValue) dom.arrValue.textContent = formatCurrency(m.annual_recurring_revenue) + ' ARR';
    if (dom.inFlightValue) dom.inFlightValue.textContent = formatCurrency(m.in_flight_pipeline_value);
    if (dom.winRateValue) dom.winRateValue.textContent = (m.win_rate || 0) + '%';
    if (dom.totalValue) dom.totalValue.textContent = formatCurrency(m.total_pipeline_value);

    if (dom.kanbanCountBadge) dom.kanbanCountBadge.textContent = state.deals.length;
    if (dom.explorerCountBadge) dom.explorerCountBadge.textContent = state.opportunities.length;
  }

  function renderKanban() {
    if (!dom.kanbanBoard) return;
    dom.kanbanBoard.innerHTML = '';

    STAGES.forEach((stageKey) => {
      const stageDeals = state.deals.filter((d) => (d.stage || 'leads') === stageKey);
      const subtotal = stageDeals.reduce((sum, d) => sum + (Number(d.monthly_value) || 0), 0);

      const col = document.createElement('div');
      col.className = 'kanban-column';
      col.dataset.stage = stageKey;

      col.innerHTML = `
        <div class="column-header">
          <div class="column-title-group">
            <span class="stage-indicator stage-${stageKey}"></span>
            <span class="column-title">${STAGE_LABELS[stageKey] || stageKey}</span>
            <span class="column-badge">${stageDeals.length}</span>
          </div>
          <span class="column-subtotal">${formatCurrency(subtotal)}</span>
        </div>
        <div class="column-cards" data-stage="${stageKey}"></div>
      `;

      const cardsContainer = col.querySelector('.column-cards');

      // Drag and Drop listeners on column
      cardsContainer.addEventListener('dragover', (e) => {
        e.preventDefault();
        cardsContainer.classList.add('drag-over');
      });

      cardsContainer.addEventListener('dragleave', () => {
        cardsContainer.classList.remove('drag-over');
      });

      cardsContainer.addEventListener('drop', (e) => {
        e.preventDefault();
        cardsContainer.classList.remove('drag-over');
        if (state.draggedDealId) {
          updateDealStage(state.draggedDealId, stageKey);
          state.draggedDealId = null;
        }
      });

      // Render Deal Cards
      stageDeals.forEach((deal) => {
        const card = createDealCardElement(deal);
        cardsContainer.appendChild(card);
      });

      dom.kanbanBoard.appendChild(col);
    });
  }

  function createDealCardElement(deal) {
    const card = document.createElement('div');
    card.className = 'deal-card';
    card.draggable = true;
    card.dataset.id = deal.id;

    const skillsHtml = (deal.skills || [])
      .slice(0, 4)
      .map((s) => `<span class="tag-pill">${escapeHtml(s)}</span>`)
      .join('');

    const stageOptions = STAGES.map(
      (s) => `<option value="${s}" ${deal.stage === s ? 'selected' : ''}>${STAGE_LABELS[s]}</option>`
    ).join('');

    card.innerHTML = `
      <div class="card-top">
        <span class="card-company">${escapeHtml(deal.company)}</span>
        <span class="card-value">${formatCurrency(deal.monthly_value)}/ش</span>
      </div>
      <div class="card-title">${escapeHtml(deal.title)}</div>
      ${skillsHtml ? `<div class="card-tags">${skillsHtml}</div>` : ''}
      ${deal.notes ? `<div class="card-notes">${escapeHtml(deal.notes)}</div>` : ''}
      <div class="card-footer">
        <select class="stage-select-sm" data-deal-id="${deal.id}">
          ${stageOptions}
        </select>
        <div class="card-actions-quick">
          <button class="icon-btn-sm btn-quick-pitch" title="توليد Pitch للعميل" data-deal-id="${deal.id}">
            <i class="fas fa-bolt" style="color: var(--accent-cyan);"></i>
          </button>
          <button class="icon-btn-sm btn-delete-deal" title="حذف" data-deal-id="${deal.id}">
            <i class="fas fa-trash-alt" style="color: var(--text-faint);"></i>
          </button>
        </div>
      </div>
    `;

    // Drag events
    card.addEventListener('dragstart', (e) => {
      state.draggedDealId = deal.id;
      card.classList.add('dragging');
      e.dataTransfer.setData('text/plain', deal.id);
    });

    card.addEventListener('dragend', () => {
      card.classList.remove('dragging');
    });

    // 1-Click Stage Change via dropdown
    const select = card.querySelector('.stage-select-sm');
    select.addEventListener('change', (e) => {
      updateDealStage(deal.id, e.target.value);
    });

    // Quick Pitch Button
    const pitchBtn = card.querySelector('.btn-quick-pitch');
    pitchBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      openPitchDrawerForDeal(deal);
    });

    // Delete Button
    const deleteBtn = card.querySelector('.btn-delete-deal');
    deleteBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      deleteDeal(deal.id);
    });

    return card;
  }

  function renderOpportunities() {
    if (!dom.explorerTableBody) return;
    dom.explorerTableBody.innerHTML = '';

    if (state.opportunities.length === 0) {
      dom.explorerTableBody.innerHTML = `
        <tr>
          <td colspan="6" style="text-align: center; padding: 40px; color: var(--text-muted);">
            لا توجد فرص مطابقة للشروط الحالية. جرّب تقليل الحد الأدنى للمرتب أو تغيير كلمات البحث.
          </td>
        </tr>
      `;
      return;
    }

    state.opportunities.forEach((opp) => {
      const tr = document.createElement('tr');
      const tagsHtml = (opp.skills_tags || [])
        .slice(0, 3)
        .map((t) => `<span class="tag-pill">${escapeHtml(t)}</span>`)
        .join(' ');

      const salaryText =
        opp.salary_or_rate ||
        `$${Math.round(opp.monthly_rate_usd_min || 4000).toLocaleString()} - $${Math.round(
          opp.monthly_rate_usd_max || 6000
        ).toLocaleString()}/ش`;

      tr.innerHTML = `
        <td>
          <div style="font-weight: 700; color: var(--text-primary);">${escapeHtml(opp.title)}</div>
          <div style="font-size: 11px; color: var(--text-muted);">${escapeHtml(opp.location || 'Remote')}</div>
        </td>
        <td>
          <span style="font-weight: 600; color: var(--text-secondary);">${escapeHtml(opp.company)}</span>
        </td>
        <td>
          <span class="kpi-badge positive">${escapeHtml(salaryText)}</span>
        </td>
        <td>${tagsHtml}</td>
        <td>
          <span class="status-pill" style="font-size: 11px; padding: 2px 8px;">
            <i class="fas fa-globe" style="font-size: 10px;"></i> ${escapeHtml(opp.source_platform || 'Hunter')}
          </span>
        </td>
        <td style="text-align: left;">
          <div style="display: flex; gap: 6px; justify-content: flex-end;">
            <button class="btn btn-secondary btn-sm btn-pitch-opp" data-opp-id="${opp.id}">
              <i class="fas fa-feather-alt"></i> Pitch
            </button>
            <button class="btn btn-primary btn-sm btn-add-opp-pipeline" data-opp-id="${opp.id}">
              <i class="fas fa-plus"></i> إضافة للمسار
            </button>
          </div>
        </td>
      `;

      // Pitch Action
      tr.querySelector('.btn-pitch-opp').addEventListener('click', () => {
        openPitchDrawerForOpportunity(opp);
      });

      // Add to Pipeline Action
      tr.querySelector('.btn-add-opp-pipeline').addEventListener('click', () => {
        addOpportunityToPipeline(opp);
      });

      dom.explorerTableBody.appendChild(tr);
    });
  }

  function addOpportunityToPipeline(opp) {
    const val = opp.monthly_rate_usd_max || opp.monthly_rate_usd_min || 5000;
    addDeal({
      opportunity_id: opp.id,
      title: opp.title,
      company: opp.company,
      stage: 'leads',
      monthly_value: Number(val),
      source: opp.source_platform || 'Hunter',
      skills: opp.skills_tags || [],
      notes: `فرصة مستخرجة من ${opp.source_platform || 'Hunter'} برابط: ${opp.url || ''}`,
    });
  }

  // --- Pitch Generator Engine ---

  async function openPitchDrawerForDeal(deal) {
    state.activePitch.position = deal.title;
    state.activePitch.company = deal.company;
    state.activePitch.skills = deal.skills || [];
    state.activePitch.contactName = deal.contact_name || '';
    state.activePitch.customNotes = deal.notes || '';
    await generateActivePitch();
    showPitchDrawer();
  }

  async function openPitchDrawerForOpportunity(opp) {
    state.activePitch.position = opp.title;
    state.activePitch.company = opp.company;
    state.activePitch.skills = opp.skills_tags || [];
    state.activePitch.contactName = '';
    state.activePitch.customNotes = '';
    await generateActivePitch();
    showPitchDrawer();
  }

  async function generateActivePitch() {
    const p = state.activePitch;
    if (dom.pitchTargetRole) {
      dom.pitchTargetRole.textContent = `${p.position} • ${p.company}`;
    }

    try {
      const res = await fetch(`${API_BASE}/api/pitch/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          position: p.position,
          company: p.company,
          skills: p.skills,
          tone: p.tone,
          custom_notes: p.customNotes || '',
          contact_name: p.contactName || '',
        }),
      });

      if (res.ok) {
        const pitch = await res.json();
        p.subject = pitch.subject;
        p.body = pitch.body;
      } else {
        throw new Error('API pitch error');
      }
    } catch (err) {
      generateLocalFallbackPitch();
    }

    if (dom.pitchSubject) dom.pitchSubject.value = p.subject;
    if (dom.pitchBody) dom.pitchBody.value = p.body;
  }

  function generateLocalFallbackPitch() {
    const p = state.activePitch;
    const skills = (p.skills || []).join(', ') || 'Next.js, Python, Node.js, AI Automation';

    if (p.tone === 'cto') {
      p.subject = `Technical Architecture: ${p.position} - Clean Execution (${p.company})`;
      p.body =
        `Hi ${p.company} Engineering Team,\n\n` +
        `I noticed your opening for ${p.position}. As a Senior Full-Stack Engineer and Solutions Architect with mastery across ${skills}, ` +
        `I build modular, high-throughput systems with sub-30ms API response and zero architectural bloat.\n\n` +
        `Recent verified highlights:\n` +
        `• Next.js 15 App Router & React 19 dashboards with sub-100ms TTFB.\n` +
        `• Resilient Python RAG & automation pipelines with strict SafeSQL read-only barriers.\n` +
        `• High-concurrency Node.js REST APIs with Redis caching.\n\n` +
        `I work seamlessly in European and US time zones (Egypt GMT+3) with daily async updates.\n` +
        `Available for a brief 10-minute technical chat this week.\n\n` +
        `Best regards,\nEng. Abdelrahman Rashad\nSenior Full-Stack & Solutions Architect`;
    } else {
      p.subject = `Accelerating ${p.company}'s Velocity: ${p.position} (Eng. Abdelrahman Rashad)`;
      p.body =
        `Hi ${p.company} Team,\n\n` +
        `I saw your need for ${p.position}. Founders hire me when they need immediate senior engineering firepower ` +
        `to ship high-converting features and AI automation workflows in days, not months.\n\n` +
        `Stack: ${skills}.\n` +
        `Available on a high-impact monthly retainer ($3.5k - $6k/mo) starting this week.\n\n` +
        `Best regards,\nEng. Abdelrahman Rashad\nFull-Stack & AI Solutions Engineer`;
    }
  }

  function showPitchDrawer() {
    if (dom.pitchDrawerOverlay) dom.pitchDrawerOverlay.classList.add('active');
  }

  function closePitchDrawer() {
    if (dom.pitchDrawerOverlay) dom.pitchDrawerOverlay.classList.remove('active');
  }

  // --- Modal Managers ---

  function openAddDealModal() {
    if (dom.addDealForm) dom.addDealForm.reset();
    if (dom.addDealModal) dom.addDealModal.classList.add('active');
  }

  function closeAddDealModal() {
    if (dom.addDealModal) dom.addDealModal.classList.remove('active');
  }

  // --- Event Bindings ---

  function setupEventListeners() {
    // Tab switching
    if (dom.tabKanban) {
      dom.tabKanban.addEventListener('click', () => {
        state.activeTab = 'kanban';
        dom.tabKanban.classList.add('active');
        if (dom.tabExplorer) dom.tabExplorer.classList.remove('active');
        if (dom.viewKanban) dom.viewKanban.style.display = 'block';
        if (dom.viewExplorer) dom.viewExplorer.style.display = 'none';
      });
    }

    if (dom.tabExplorer) {
      dom.tabExplorer.addEventListener('click', () => {
        state.activeTab = 'explorer';
        dom.tabExplorer.classList.add('active');
        if (dom.tabKanban) dom.tabKanban.classList.remove('active');
        if (dom.viewKanban) dom.viewKanban.style.display = 'none';
        if (dom.viewExplorer) dom.viewExplorer.style.display = 'block';
        fetchOpportunities();
      });
    }

    // Filter controls
    let filterDebounce = null;
    function handleFilterChange() {
      clearTimeout(filterDebounce);
      filterDebounce = setTimeout(() => {
        if (dom.searchInput) state.filters.search = dom.searchInput.value.trim();
        if (dom.salaryFilter) state.filters.minSalary = Number(dom.salaryFilter.value) || 0;
        if (dom.tagFilter) state.filters.tags = dom.tagFilter.value.trim();
        if (dom.sourceFilter) state.filters.source = dom.sourceFilter.value.trim();
        fetchOpportunities();
      }, 250);
    }

    if (dom.searchInput) dom.searchInput.addEventListener('input', handleFilterChange);
    if (dom.salaryFilter) dom.salaryFilter.addEventListener('change', handleFilterChange);
    if (dom.tagFilter) dom.tagFilter.addEventListener('change', handleFilterChange);
    if (dom.sourceFilter) dom.sourceFilter.addEventListener('change', handleFilterChange);

    // Sync button
    if (dom.syncBtn) {
      dom.syncBtn.addEventListener('click', async () => {
        dom.syncBtn.disabled = true;
        dom.syncBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> جاري المزامنة...';
        try {
          const res = await fetch(`${API_BASE}/api/opportunities/sync`, { method: 'POST' });
          if (res.ok) {
            const data = await res.json();
            showToast(`تمت مزامنة ${data.count} فرصة عالية القيمة من محرك الاقتناص! ✅`);
            await fetchOpportunities();
            await fetchPipeline();
            renderKanban();
          }
        } catch (err) {
          showToast('فشلت المزامنة المباشرة مع الخادم', 'info');
        } finally {
          dom.syncBtn.disabled = false;
          dom.syncBtn.innerHTML = '<i class="fas fa-sync-alt"></i> مزامنة الفرص الحية';
        }
      });
    }

    // Add Deal Modal trigger
    if (dom.addDealBtn) dom.addDealBtn.addEventListener('click', openAddDealModal);
    if (dom.closeAddDealBtn) dom.closeAddDealBtn.addEventListener('click', closeAddDealModal);
    if (dom.cancelAddDealBtn) dom.cancelAddDealBtn.addEventListener('click', closeAddDealModal);

    // Add Deal Form submit
    if (dom.addDealForm) {
      dom.addDealForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const title = document.getElementById('deal-title-input').value.trim();
        const company = document.getElementById('deal-company-input').value.trim();
        const stage = document.getElementById('deal-stage-select').value;
        const monthly_value = parseFloat(document.getElementById('deal-value-input').value) || 4500;
        const source = document.getElementById('deal-source-input').value.trim() || 'Manual';
        const skillsRaw = document.getElementById('deal-skills-input').value;
        const skills = skillsRaw ? skillsRaw.split(',').map((s) => s.trim()).filter(Boolean) : [];
        const contact_name = document.getElementById('deal-contact-input').value.trim();
        const notes = document.getElementById('deal-notes-input').value.trim();

        if (!title || !company) {
          alert('يرجى كتابة المسمى واسم الشركة');
          return;
        }

        addDeal({
          title,
          company,
          stage,
          monthly_value,
          source,
          skills,
          contact_name,
          notes,
        });

        closeAddDealModal();
      });
    }

    // Export Buttons
    if (dom.exportJsonBtn) {
      dom.exportJsonBtn.addEventListener('click', () => {
        window.open(`${API_BASE}/api/export?format=json`, '_blank');
      });
    }
    if (dom.exportCsvBtn) {
      dom.exportCsvBtn.addEventListener('click', () => {
        window.open(`${API_BASE}/api/export?format=csv`, '_blank');
      });
    }

    // Pitch Drawer Controls
    if (dom.closePitchDrawerBtn) dom.closePitchDrawerBtn.addEventListener('click', closePitchDrawer);

    function setPitchTone(tone) {
      state.activePitch.tone = tone;
      [dom.toneCtobtn, dom.toneFounderbtn, dom.toneFreelancebtn].forEach((b) => b && b.classList.remove('active'));
      if (tone === 'cto' && dom.toneCtobtn) dom.toneCtobtn.classList.add('active');
      if (tone === 'founder' && dom.toneFounderbtn) dom.toneFounderbtn.classList.add('active');
      if (tone === 'freelance' && dom.toneFreelancebtn) dom.toneFreelancebtn.classList.add('active');
      generateActivePitch();
    }

    if (dom.toneCtobtn) dom.toneCtobtn.addEventListener('click', () => setPitchTone('cto'));
    if (dom.toneFounderbtn) dom.toneFounderbtn.addEventListener('click', () => setPitchTone('founder'));
    if (dom.toneFreelancebtn) dom.toneFreelancebtn.addEventListener('click', () => setPitchTone('freelance'));

    // Copy Pitch button
    if (dom.copyPitchBtn) {
      dom.copyPitchBtn.addEventListener('click', () => {
        const text = `${dom.pitchSubject.value}\n\n${dom.pitchBody.value}`;
        navigator.clipboard
          .writeText(text)
          .then(() => showToast('تم نسخ خطاب الـ Pitch بنجاح إلى الحافظة! 📋'))
          .catch(() => {
            const ta = document.createElement('textarea');
            ta.value = text;
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            ta.remove();
            showToast('تم النسخ بنجاح! 📋');
          });
      });
    }

    // Mail Pitch button
    if (dom.mailPitchBtn) {
      dom.mailPitchBtn.addEventListener('click', () => {
        const sub = encodeURIComponent(dom.pitchSubject.value);
        const body = encodeURIComponent(dom.pitchBody.value);
        window.location.href = `mailto:?subject=${sub}&body=${body}`;
      });
    }

    // Keyboard escape to close modals
    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        closePitchDrawer();
        closeAddDealModal();
      }
    });
    // Global Quick Pitch Hook for external/solution buttons
    window.cockpitQuickPitch = async function (position, company, skills, tone = 'founder') {
      state.activePitch.position = position;
      state.activePitch.company = company;
      state.activePitch.skills = skills || [];
      state.activePitch.tone = tone;
      state.activePitch.contactName = '';
      state.activePitch.customNotes = '';
      if (dom.toneCtobtn && dom.toneFounderbtn && dom.toneFreelancebtn) {
        [dom.toneCtobtn, dom.toneFounderbtn, dom.toneFreelancebtn].forEach((b) => b && b.classList.remove('active'));
        if (tone === 'cto' && dom.toneCtobtn) dom.toneCtobtn.classList.add('active');
        else if (tone === 'founder' && dom.toneFounderbtn) dom.toneFounderbtn.classList.add('active');
        else if (tone === 'freelance' && dom.toneFreelancebtn) dom.toneFreelancebtn.classList.add('active');
      }
      await generateActivePitch();
      showPitchDrawer();
    };
  }

  // --- Bootstrap Engine ---
  async function init() {
    await checkHealth();
    await fetchPipeline();
    await fetchMetrics();
    await fetchOpportunities();
    renderKanban();
    setupEventListeners();
  }

  // Kickoff on DOM loaded
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
