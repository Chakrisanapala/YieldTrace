/**
 * YieldTrace Enterprise SaaS Frontend Application Script
 * Orchestrates state, views, Chart.js analytics, and backend API interactions.
 */

// Global State
const state = {
  currentRole: "owner",
  currentView: "overview",
  selectedRunId: 1,
  chartInstances: {}
};

// Switch Active Navigation Section
function switchView(viewId) {
  state.currentView = viewId;
  document.querySelectorAll(".nav-link-custom").forEach(link => {
    link.classList.toggle("active", link.dataset.view === viewId);
  });
  document.querySelectorAll(".view-panel").forEach(panel => {
    panel.classList.toggle("d-none", panel.id !== `view-${viewId}`);
  });

  // Load View Specific Data
  if (viewId === "overview") loadDashboardData();
  else if (viewId === "orders") loadOrdersData();
  else if (viewId === "customers") loadCustomersData();
  else if (viewId === "suppliers") loadSuppliersData();
  else if (viewId === "products") loadProductsData();
  else if (viewId === "purchases") loadPurchasesData();
  else if (viewId === "inventory") loadInventoryData();
  else if (viewId === "bom") loadBOMData();
  else if (viewId === "production") loadProductionData();
  else if (viewId === "forensics") loadForensicsData(state.selectedRunId);
  else if (viewId === "costing") loadCostingData(state.selectedRunId);
  else if (viewId === "invoices") loadInvoicesData();
  else if (viewId === "payments") loadPaymentsData();
  else if (viewId === "planner") loadPlannerData();
  else if (viewId === "reports") loadReportsData();
  else if (viewId === "settings") loadSettingsData();
}

// ----------------------------------------------------
// 1. Overview & Dashboard
// ----------------------------------------------------
async function loadDashboardData() {
  try {
    const res = await fetch("/api/dashboard/metrics");
    const data = await res.json();
    const kpis = data.kpis;

    document.getElementById("kpi-sales").innerText = `₹${kpis.total_sales.toLocaleString("en-IN", {minimumFractionDigits: 2})}`;
    document.getElementById("kpi-orders").innerText = `${kpis.total_orders} (${kpis.pending_orders} pending)`;
    document.getElementById("kpi-yield").innerText = `${kpis.average_yield_percent}%`;
    document.getElementById("kpi-fg-stock").innerText = `${kpis.finished_goods_inventory_units} pkts`;
    document.getElementById("kpi-outstanding").innerText = `₹${kpis.total_outstanding.toLocaleString("en-IN", {minimumFractionDigits: 2})}`;
    document.getElementById("kpi-anomalies").innerText = `${kpis.total_anomalies_flagged}`;
    document.getElementById("kpi-pkg-mismatch").innerText = `${kpis.packaging_warnings}`;

    // Render activity
    const feedTbody = document.getElementById("dashboard-activity-feed");
    if (feedTbody) {
      feedTbody.innerHTML = data.recent_activity.map(a => `
        <tr>
          <td><span class="badge ${a.action === 'AUDIT_WARNING' ? 'bg-danger' : 'bg-primary'}">${a.action}</span></td>
          <td><strong>${a.entity}</strong> #${a.reference}</td>
          <td>${a.reason}</td>
          <td><small class="text-muted">${a.changed_by}</small></td>
          <td><small class="text-muted">${a.timestamp}</small></td>
        </tr>
      `).join("");
    }
  } catch (err) {
    console.error("Failed to load dashboard metrics:", err);
  }
}

// ----------------------------------------------------
// 2. Inventory & Stock Ledger
// ----------------------------------------------------
async function loadInventoryData() {
  try {
    const res = await fetch("/api/inventory/balances");
    const balances = await res.json();
    const tbody = document.getElementById("inventory-balances-tbody");
    if (tbody) {
      tbody.innerHTML = balances.map(b => `
        <tr>
          <td><strong>${b.code}</strong></td>
          <td>${b.name}</td>
          <td><span class="badge bg-secondary">${b.category}</span></td>
          <td><span class="fs-6 fw-bold ${b.balance < b.reorder_level ? 'text-danger' : 'text-success'}">${b.balance} ${b.unit}</span></td>
          <td>₹${b.standard_cost.toFixed(2)}</td>
          <td>₹${b.current_wauc.toFixed(2)}</td>
          <td><strong>₹${b.inventory_valuation.toLocaleString("en-IN", {minimumFractionDigits: 2})}</strong></td>
          <td>${b.low_stock_warning ? '<span class="badge bg-danger">Reorder Required</span>' : '<span class="badge bg-success">Optimal</span>'}</td>
        </tr>
      `).join("");
    }

    // Load recent ledger moves
    const ledgerRes = await fetch("/api/inventory/ledger?limit=15");
    const ledger = await ledgerRes.json();
    const ledgerTbody = document.getElementById("inventory-ledger-tbody");
    if (ledgerTbody) {
      ledgerTbody.innerHTML = ledger.map(m => `
        <tr>
          <td><small class="text-muted">${m.created_at ? m.created_at.replace("T", " ").substring(0, 16) : ''}</small></td>
          <td><strong>${m.item_code}</strong></td>
          <td><span class="badge ${m.direction === 'IN' ? 'bg-success' : 'bg-warning text-dark'}">${m.direction}</span></td>
          <td>${m.move_type}</td>
          <td>${m.quantity} ${m.unit}</td>
          <td>₹${m.unit_cost.toFixed(2)}</td>
          <td><span class="fw-bold">${m.balance_after} ${m.unit}</span></td>
          <td><small class="text-muted">${m.reference_type} #${m.reference_id}</small></td>
        </tr>
      `).join("");
    }
  } catch (err) {
    console.error("Failed to load inventory:", err);
  }
}

// ----------------------------------------------------
// 3. Variance Forensics Engine (The Core Innovation)
// ----------------------------------------------------
async function loadForensicsData(runId) {
  try {
    const res = await fetch(`/api/insight/forensics/run/${runId}`);
    const data = await res.json();
    const container = document.getElementById("forensics-findings-container");

    if (container) {
      if (!data.findings || data.findings.length === 0) {
        container.innerHTML = `<div class="alert alert-success">No anomalies or deviations detected for production run #${runId}. Performance is completely within tolerance.</div>`;
      } else {
        container.innerHTML = data.findings.map((f, idx) => `
          <div class="forensic-card ${f.severity.toLowerCase()}">
            <div class="d-flex justify-content-between align-items-center mb-2">
              <h6 class="mb-0 fw-bold text-dark"><i class="bi bi-shield-exclamation text-danger me-2"></i>Finding #${idx+1}: ${f.finding_title}</h6>
              <span class="badge ${f.severity === 'CRITICAL' ? 'bg-danger' : f.severity === 'WARNING' ? 'bg-warning text-dark' : 'bg-info text-dark'}">${f.severity}</span>
            </div>
            <div class="row g-2 mb-2 text-muted small">
              <div class="col-md-3"><strong>Material/Process:</strong> ${f.affected_material}</div>
              <div class="col-md-3"><strong>Expected (BOM):</strong> ${f.expected_value}</div>
              <div class="col-md-3"><strong>Actual Observed:</strong> ${f.actual_value}</div>
              <div class="col-md-3"><strong>Deviation:</strong> <span class="fw-bold text-danger">${f.difference_percentage > 0 ? '+' : ''}${f.difference_percentage}%</span></div>
            </div>
            <div class="p-2 mb-2 bg-white rounded border border-light">
              <div class="small mb-1"><strong>Forensic Detection Method:</strong> <code>${f.detection_method}</code> | <strong>Sample Size:</strong> ${f.sample_size} historical batches | <strong>Baseline:</strong> ${f.historical_baseline_range}</div>
              <div class="small text-secondary"><strong>Statistical Confidence / Limitation:</strong> ${f.confidence_limitations}</div>
            </div>
            <div class="alert alert-warning py-2 mb-0 small">
              <strong>Supervisor Actionable Recommendation:</strong> ${f.recommended_investigation}
            </div>
          </div>
        `).join("");
      }
    }

    // Load CUSUM Drift Chart for Oil
    loadCUSUMChart();
  } catch (err) {
    console.error("Failed to load forensics data:", err);
  }
}

// CUSUM Drift Chart
async function loadCUSUMChart() {
  try {
    const res = await fetch("/api/insight/forensics/cusum/2?target=0&k=0.5&h=3.0");
    const data = await res.json();
    const ctx = document.getElementById("cusumChart");
    if (!ctx) return;

    if (state.chartInstances["cusum"]) {
      state.chartInstances["cusum"].destroy();
    }

    const labels = data.cusum_series.map(s => s.run_number);
    const sHigh = data.cusum_series.map(s => s.s_high);
    const thresholds = data.cusum_series.map(() => data.decision_threshold_h);

    state.chartInstances["cusum"] = new Chart(ctx, {
      type: "line",
      data: {
        labels: labels,
        datasets: [
          {
            label: "CUSUM S+ (Cumulative Surplus Deviation)",
            data: sHigh,
            borderColor: "#ef4444",
            backgroundColor: "rgba(239, 68, 68, 0.1)",
            fill: true,
            tension: 0.2
          },
          {
            label: `Decision Threshold (H = ${data.decision_threshold_h})`,
            data: thresholds,
            borderColor: "#f59e0b",
            borderDash: [6, 6],
            pointRadius: 0
          }
        ]
      },
      options: {
        responsive: true,
        plugins: {
          legend: { position: "top" }
        },
        scales: {
          y: { beginAtZero: true, title: { display: true, text: "Cumulative Shift Statistic" } }
        }
      }
    });
  } catch (err) {
    console.error("Failed to load CUSUM chart:", err);
  }
}

// ----------------------------------------------------
// 4. Costing & Cost Waterfall
// ----------------------------------------------------
async function loadCostingData(runId) {
  try {
    const res = await fetch(`/api/production/runs/${runId}/costing`);
    const data = await res.json();

    document.getElementById("cost-std-baseline").innerText = `₹${data.total_standard_cost.toFixed(2)}`;
    document.getElementById("cost-actual-total").innerText = `₹${data.total_actual_cost.toFixed(2)}`;
    document.getElementById("cost-price-var").innerText = `₹${data.price_variance.toFixed(2)}`;
    document.getElementById("cost-usage-var").innerText = `₹${data.usage_variance.toFixed(2)}`;
    document.getElementById("cost-std-per-unit").innerText = `₹${data.standard_cost_per_packet.toFixed(4)}`;
    document.getElementById("cost-act-per-unit").innerText = `₹${data.actual_cost_per_packet.toFixed(4)}`;
    document.getElementById("cost-reconciled-badge").innerHTML = data.is_mathematically_reconciled
      ? '<span class="badge bg-success"><i class="bi bi-check-circle me-1"></i>Reconciled to ₹0.00 Paisa Precision</span>'
      : '<span class="badge bg-danger">Discrepancy Detected</span>';

    // Render Material Breakdown Table
    const tbody = document.getElementById("costing-material-tbody");
    if (tbody) {
      tbody.innerHTML = data.material_breakdown.map(m => `
        <tr>
          <td><strong>${m.item_code}</strong> - ${m.item_name}</td>
          <td>${m.planned_quantity} ${m.unit}</td>
          <td>${m.actual_quantity} ${m.unit}</td>
          <td>₹${m.standard_cost.toFixed(2)}</td>
          <td>₹${m.actual_wauc.toFixed(2)}</td>
          <td>₹${m.standard_total.toFixed(2)}</td>
          <td>₹${m.actual_total.toFixed(2)}</td>
          <td class="${m.usage_variance > 0 ? 'text-danger fw-bold' : 'text-success'}">₹${m.usage_variance.toFixed(2)}</td>
          <td class="${m.price_variance > 0 ? 'text-danger fw-bold' : 'text-success'}">₹${m.price_variance.toFixed(2)}</td>
        </tr>
      `).join("");
    }

    // Render Chart.js Waterfall Chart
    const ctx = document.getElementById("waterfallChart");
    if (!ctx) return;

    if (state.chartInstances["waterfall"]) {
      state.chartInstances["waterfall"].destroy();
    }

    const steps = data.waterfall_steps;
    const labels = steps.map(s => s.label);
    const amounts = steps.map(s => s.amount);
    const colors = steps.map(s => s.type === "baseline" ? "#1e3a8a" : s.type === "total" ? "#2563eb" : s.amount >= 0 ? "#ef4444" : "#10b981");

    state.chartInstances["waterfall"] = new Chart(ctx, {
      type: "bar",
      data: {
        labels: labels,
        datasets: [{
          label: "Amount (₹)",
          data: amounts,
          backgroundColor: colors
        }]
      },
      options: {
        responsive: true,
        plugins: {
          legend: { display: false }
        },
        scales: {
          y: { beginAtZero: true, title: { display: true, text: "Cost in Rupees (₹)" } }
        }
      }
    });
  } catch (err) {
    console.error("Failed to load costing waterfall:", err);
  }
}

// ----------------------------------------------------
// 5. Orders & Dispatches
// ----------------------------------------------------
async function loadOrdersData() {
  try {
    const res = await fetch("/api/sales/orders");
    const orders = await res.json();
    const tbody = document.getElementById("orders-tbody");
    if (tbody) {
      tbody.innerHTML = orders.map(o => `
        <tr>
          <td><strong>${o.order_number}</strong></td>
          <td>${o.customer_name} <small class="text-muted">(${o.customer_state})</small></td>
          <td><span class="badge ${o.status === 'FULFILLED' ? 'bg-success' : o.status === 'PARTIALLY_FULFILLED' ? 'bg-warning text-dark' : 'bg-primary'}">${o.status}</span></td>
          <td>${o.total_ordered} pkts</td>
          <td>${o.total_fulfilled} pkts</td>
          <td><span class="${o.total_backordered > 0 ? 'fw-bold text-danger' : ''}">${o.total_backordered} pkts</span></td>
          <td>${o.order_date.substring(0, 10)}</td>
          <td>
            ${o.status === 'APPROVED' ? `<button class="btn btn-sm btn-outline-success" onclick="dispatchOrder(${o.id})"><i class="bi bi-box-arrow-right me-1"></i>Dispatch</button>` : ''}
            ${o.status === 'DRAFT' ? `<button class="btn btn-sm btn-outline-primary" onclick="approveOrder(${o.id})"><i class="bi bi-check-lg me-1"></i>Approve</button>` : ''}
          </td>
        </tr>
      `).join("");
    }
  } catch (err) {
    console.error("Failed to load orders:", err);
  }
}

// ----------------------------------------------------
// 6. Invoices & Billing
// ----------------------------------------------------
async function loadInvoicesData() {
  try {
    const res = await fetch("/api/sales/invoices");
    const invoices = await res.json();
    const tbody = document.getElementById("invoices-tbody");
    if (tbody) {
      tbody.innerHTML = invoices.map(inv => `
        <tr>
          <td><strong>${inv.invoice_no}</strong></td>
          <td>${inv.customer_name}</td>
          <td><span class="badge ${inv.is_interstate ? 'bg-info text-dark' : 'bg-secondary'}">${inv.is_interstate ? 'Inter-State (IGST)' : 'Intra-State (CGST+SGST)'}</span></td>
          <td>₹${inv.taxable_amount.toFixed(2)}</td>
          <td>₹${inv.cgst_amount.toFixed(2)}</td>
          <td>₹${inv.sgst_amount.toFixed(2)}</td>
          <td>₹${inv.igst_amount.toFixed(2)}</td>
          <td><strong>₹${inv.total_amount.toFixed(2)}</strong></td>
          <td>₹${inv.paid_amount.toFixed(2)}</td>
          <td><span class="${inv.outstanding_amount > 0 ? 'text-danger fw-bold' : 'text-success'}">₹${inv.outstanding_amount.toFixed(2)}</span></td>
          <td><span class="badge ${inv.status === 'PAID' ? 'bg-success' : 'bg-warning text-dark'}">${inv.status}</span></td>
          <td>
            ${inv.outstanding_amount > 0 ? `<button class="btn btn-sm btn-outline-primary" onclick="openPaymentModal(${inv.id}, '${inv.invoice_no}', ${inv.outstanding_amount})">Pay</button>` : ''}
          </td>
        </tr>
      `).join("");
    }
  } catch (err) {
    console.error("Failed to load invoices:", err);
  }
}

// ----------------------------------------------------
// 7. Deterministic Production Planner
// ----------------------------------------------------
async function loadPlannerData() {
  try {
    const res = await fetch("/api/insight/planner/evaluate?finished_good_id=6");
    const data = await res.json();

    document.getElementById("planner-product").innerText = data.product_name;
    document.getElementById("planner-demand").innerText = `${data.gross_demand} pkts`;
    document.getElementById("planner-avail").innerText = `${data.available_finished_stock} pkts`;
    document.getElementById("planner-shortage").innerText = `${data.net_shortage} pkts`;
    document.getElementById("planner-batches").innerText = `${data.required_batches} batch(es)`;
    document.getElementById("planner-output").innerText = `${data.planned_production_output} pkts`;
    document.getElementById("planner-status-badge").innerHTML = data.is_plan_feasible
      ? '<span class="badge bg-success p-2 fs-6"><i class="bi bi-check-circle me-1"></i>Plan Feasible with Current Inventory</span>'
      : '<span class="badge bg-danger p-2 fs-6"><i class="bi bi-exclamation-triangle me-1"></i>Production Blocked — Material Shortage</span>';

    const tbody = document.getElementById("planner-materials-tbody");
    if (tbody) {
      tbody.innerHTML = data.material_feasibility.map(m => `
        <tr>
          <td><strong>${m.item_code}</strong></td>
          <td>${m.item_name}</td>
          <td>${m.standard_quantity_per_batch} ${m.unit}</td>
          <td>${m.total_required_quantity} ${m.unit}</td>
          <td><span class="fw-bold ${m.is_sufficient ? 'text-success' : 'text-danger'}">${m.current_stock_available} ${m.unit}</span></td>
          <td>${m.shortage > 0 ? `<span class="badge bg-danger">Deficit: ${m.shortage} ${m.unit}</span>` : '<span class="badge bg-success">Sufficient</span>'}</td>
        </tr>
      `).join("");
    }
  } catch (err) {
    console.error("Failed to load planner:", err);
  }
}

// ----------------------------------------------------
// Placeholder Data Loaders for other views
// ----------------------------------------------------
async function loadCustomersData() {
  const res = await fetch("/api/master/customers");
  const data = await res.json();
  const tbody = document.getElementById("customers-tbody");
  if (tbody) {
    tbody.innerHTML = data.map(c => `<tr><td><strong>${c.code}</strong></td><td>${c.name}</td><td>${c.customer_type}</td><td>${c.gstin || '-'}</td><td>${c.state}</td><td>${c.contact_phone || '-'}</td></tr>`).join("");
  }
}

async function loadSuppliersData() {
  const res = await fetch("/api/master/suppliers");
  const data = await res.json();
  const tbody = document.getElementById("suppliers-tbody");
  if (tbody) {
    tbody.innerHTML = data.map(s => `<tr><td><strong>${s.code}</strong></td><td>${s.name}</td><td>${s.gstin || '-'}</td><td>${s.state}</td><td>${s.contact_phone || '-'}</td></tr>`).join("");
  }
}

async function loadProductsData() {
  const res = await fetch("/api/master/items");
  const data = await res.json();
  const tbody = document.getElementById("products-tbody");
  if (tbody) {
    tbody.innerHTML = data.map(p => `<tr><td><strong>${p.code}</strong></td><td>${p.name}</td><td><span class="badge bg-secondary">${p.category}</span></td><td>${p.unit}</td><td>₹${p.standard_cost.toFixed(2)}</td><td>₹${p.selling_price.toFixed(2)}</td><td>${p.gst_rate}%</td></tr>`).join("");
  }
}

async function loadPurchasesData() {
  const res = await fetch("/api/reports/purchases?format=json");
  const data = await res.json();
  const tbody = document.getElementById("purchases-tbody");
  if (tbody) {
    tbody.innerHTML = data.map(p => `<tr><td><strong>${p.invoice_no}</strong></td><td>${p.date}</td><td>${p.supplier}</td><td>₹${p.total_amount.toFixed(2)}</td><td><span class="badge bg-success">${p.status}</span></td></tr>`).join("");
  }
}

async function loadBOMData() {
  const res = await fetch("/api/production/boms");
  const data = await res.json();
  const container = document.getElementById("bom-container");
  if (container && data.length > 0) {
    const b = data[0];
    container.innerHTML = `
      <div class="yield-card">
        <h5 class="fw-bold mb-3"><i class="bi bi-receipt-cutoff text-primary me-2"></i>${b.code} — ${b.name}</h5>
        <div class="row mb-3 text-muted">
          <div class="col-md-3"><strong>Standard Output:</strong> ${b.yield_packets} packets</div>
          <div class="col-md-3"><strong>Batch Size:</strong> ${b.batch_size} batch</div>
          <div class="col-md-3"><strong>Pack Carton Capacity:</strong> ${b.pack_carton_capacity} pkts/carton</div>
          <div class="col-md-3"><strong>Standard Overhead:</strong> ₹1,800.00</div>
        </div>
        <table class="table table-yield">
          <thead><tr><th>Item</th><th>Standard Requirement</th><th>Standard Unit Cost</th></tr></thead>
          <tbody>
            ${b.lines.map(l => `<tr><td><strong>${l.item_name}</strong></td><td>${l.standard_quantity} ${l.unit}</td><td>₹${l.standard_cost.toFixed(2)}</td></tr>`).join("")}
          </tbody>
        </table>
      </div>
    `;
  }
}

async function loadProductionData() {
  const res = await fetch("/api/reports/production-batches?format=json");
  const data = await res.json();
  const tbody = document.getElementById("production-batches-tbody");
  if (tbody) {
    tbody.innerHTML = data.map(r => `
      <tr>
        <td><strong>${r.run_number}</strong></td>
        <td>${r.date}</td>
        <td>${r.product}</td>
        <td>${r.planned_output} pkts</td>
        <td>${r.actual_output} pkts</td>
        <td><span class="badge ${r.yield_variance_percent < 0 ? 'bg-danger' : 'bg-success'}">${r.yield_variance_percent}%</span></td>
        <td><span class="badge ${r.packaging_warning.includes('MISMATCH') ? 'bg-danger' : 'bg-success'}">${r.packaging_warning}</span></td>
        <td><span class="${r.is_synthetic.includes('Synthetic') ? 'badge-synthetic' : 'badge-production'}">${r.is_synthetic}</span></td>
      </tr>
    `).join("");
  }
}

async function loadReportsData() {
  const res = await fetch("/api/reports/audit-trail?format=json");
  const data = await res.json();
  const tbody = document.getElementById("reports-audit-tbody");
  if (tbody) {
    tbody.innerHTML = data.map(l => `<tr><td>${l.timestamp}</td><td><span class="badge ${l.action === 'AUDIT_WARNING' ? 'bg-danger' : 'bg-primary'}">${l.action}</span></td><td>${l.entity}</td><td>${l.record_id}</td><td>${l.changed_by}</td><td>${l.reason}</td></tr>`).join("");
  }
}

async function loadSettingsData() {
  const res = await fetch("/api/auth/users");
  const data = await res.json();
  const tbody = document.getElementById("settings-users-tbody");
  if (tbody) {
    tbody.innerHTML = data.map(u => `<tr><td><strong>${u.username}</strong></td><td>${u.full_name || '-'}</td><td>${u.email}</td><td><span class="badge bg-secondary">${u.role}</span></td><td><span class="badge bg-success">Active</span></td></tr>`).join("");
  }
}

// User Role Switcher for Demo
function switchDemoRole(role) {
  state.currentRole = role;
  document.getElementById("current-user-role-badge").innerText = role.toUpperCase();
}

// Initialize on DOM Load
document.addEventListener("DOMContentLoaded", () => {
  switchView("overview");
});
