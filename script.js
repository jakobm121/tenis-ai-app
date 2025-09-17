// Confidence Chart
if (document.getElementById("confidenceChart")) {
  new Chart(document.getElementById("confidenceChart"), {
    type: 'doughnut',
    data: {
      labels: ["Confidence", "Remaining"],
      datasets: [{
        data: [75, 25],
        backgroundColor: ["#0077b6", "#e0e0e0"]
      }]
    }
  });
}

// Accordion
const buttons = document.querySelectorAll(".accordion-btn");
buttons.forEach(btn => {
  btn.addEventListener("click", () => {
    const content = btn.nextElementSibling;
    content.style.display = content.style.display === "block" ? "none" : "block";
  });
});