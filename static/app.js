const textArea = document.getElementById("patientText");
const counter = document.getElementById("counter");
const triageBtn = document.getElementById("triageBtn");
const clearBtn = document.getElementById("clearBtn");

const emptyState = document.getElementById("emptyState");
const resultBox = document.getElementById("result");
const status = document.getElementById("status");

let scenarios = [];

function updateCounter() {
  counter.textContent = textArea.value.length;
}

textArea.addEventListener("input", updateCounter);

clearBtn.addEventListener("click", () => {
  textArea.value = "";
  updateCounter();

  resultBox.classList.add("hidden");
  emptyState.classList.remove("hidden");
});

document.querySelectorAll("[data-demo]").forEach(button => {

  button.addEventListener("click", () => {

    const scenario = scenarios[Number(button.dataset.demo)];

    if (scenario) {
      textArea.value = scenario.text;
      updateCounter();
      runTriage();
    }

  });

});

function fillList(id, values) {

  const element = document.getElementById(id);

  element.innerHTML = "";

  (values || []).forEach(value => {

    const li = document.createElement("li");

    li.textContent = value;

    element.appendChild(li);

  });

}

function renderResult(data) {

  const result = data.result;

  document.getElementById("urgency").textContent =
    result.urgency;

  document.getElementById("department").textContent =
    result.department;

  document.getElementById("rule").textContent =
    "RULE " + result.rule_id;

  document.getElementById("reasoning").textContent =
    result.reasoning;

  document.getElementById("action").textContent =
    result.action;

  fillList("knowns", result.knowns);

  fillList("unknowns", result.unknowns);

  fillList(
    "followups",
    result.follow_up_questions
  );

  const followupBlock =
    document.getElementById("followupBlock");

  followupBlock.classList.toggle(
    "hidden",
    !result.follow_up_questions ||
    result.follow_up_questions.length === 0
  );

  const card =
    document.getElementById("urgencyCard");

  if (result.urgency === "EMERGENCY") {

    card.style.borderColor = "#7b3434";

  } else if (result.urgency === "URGENT") {

    card.style.borderColor = "#715e2a";

  } else if (result.urgency === "NON-URGENT") {

    card.style.borderColor = "#315343";

  } else {

    card.style.borderColor = "#39404d";

  }

  emptyState.classList.add("hidden");

  resultBox.classList.remove("hidden");

}

async function runTriage() {

  const text = textArea.value.trim();

  if (!text) {

    textArea.focus();

    return;

  }

  triageBtn.disabled = true;

  triageBtn.querySelector("span").textContent =
    "Assessing...";

  try {

    const response = await fetch("/triage", {

      method: "POST",

      headers: {
        "Content-Type": "application/json"
      },

      body: JSON.stringify({
        text: text
      })

    });

    const data = await response.json();

    if (!response.ok) {

      throw new Error(
        data.error || "Triage failed"
      );

    }

    renderResult(data);

  } catch (error) {

    alert(error.message);

  } finally {

    triageBtn.disabled = false;

    triageBtn.querySelector("span").textContent =
      "Run Triage";

  }

}

triageBtn.addEventListener(
  "click",
  runTriage
);

async function init() {

  try {

    const healthResponse =
      await fetch("/health");

    const scenariosResponse =
      await fetch("/scenarios");

    const health =
      await healthResponse.json();

    scenarios =
      await scenariosResponse.json();

    if (health.gemini_configured) {

      status.textContent =
        "● Gemini connected";

      status.style.color =
        "#70e1b5";

    } else {

      status.textContent =
        "● Demo fallback active";

      status.style.color =
        "#ffc857";

    }

  } catch {

    status.textContent =
      "● Local mode";

  }

}

init();
