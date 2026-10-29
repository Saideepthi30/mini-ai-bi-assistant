const $ = (id) => document.getElementById(id);
const money = (value) => new Intl.NumberFormat("en-IN", {
  style: "currency", currency: "INR", maximumFractionDigits: 2
}).format(Number(value || 0));

async function loadSummary() {
  try {
    const response = await fetch("/api/summary");
    const data = await response.json();
    $("transactions").textContent = data.transactions;
    $("revenue").textContent = money(data.total_revenue);
    $("products").textContent = data.products;
    $("regions").textContent = data.regions;
  } catch {
    $("status").textContent = "Could not connect to the API. Is the server running?";
  }
}

function renderData(data) {
  if (data === null || data === undefined) return "";
  const rows = Array.isArray(data) ? data : [data];
  if (!rows.length) return "<p>No matching records found.</p>";
  const keys = [...new Set(rows.flatMap(row => Object.keys(row)))];
  const header = keys.map(k => `<th>${escapeHtml(k.replaceAll("_", " "))}</th>`).join("");
  const body = rows.map(row => "<tr>" + keys.map(k => {
    const v = row[k];
    const display = typeof v === "number" && /revenue|change|amount/i.test(k) ? money(v) : (v ?? "—");
    return `<td>${escapeHtml(String(display))}</td>`;
  }).join("") + "</tr>").join("");
  return `<table><thead><tr>${header}</tr></thead><tbody>${body}</tbody></table>`;
}
function escapeHtml(value) {
  return value.replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[c]));
}

async function askQuestion() {
  const question = $("question").value.trim();
  if (!question) {
    $("status").textContent = "Enter a question first.";
    return;
  }
  $("ask").disabled = true;
  $("status").textContent = "Querying sales database…";
  try {
    const response = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question })
    });
    const result = await response.json();
    if (!response.ok) {
      const detail = result.detail || result;
      $("status").textContent = detail.error || "Question could not be answered.";
      $("result").hidden = true;
      return;
    }
    $("answer").textContent = result.answer;
    $("data").innerHTML = renderData(result.data);
    $("sql").textContent = result.sql + (result.params?.length ? "\nParameters: " + JSON.stringify(result.params) : "");
    $("result").hidden = false;
    $("status").textContent = "Answer ready.";
  } catch {
    $("status").textContent = "Request failed. Check that the backend is running.";
  } finally {
    $("ask").disabled = false;
  }
}
$("ask").addEventListener("click", askQuestion);
$("question").addEventListener("keydown", event => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    askQuestion();
  }
});
document.querySelectorAll(".example").forEach(button => {
  button.addEventListener("click", () => {
    $("question").value = button.textContent;
    askQuestion();
  });
});
loadSummary();
