document.addEventListener("DOMContentLoaded", () => {
  const origin = document.getElementById("origin");
  const destination = document.getElementById("destination");
  const routes = document.getElementById("available-routes");
  if (!origin || !destination || !routes) return;
  const pairs = JSON.parse(routes.textContent);
  origin.addEventListener("change", () => {
    const previous = destination.value;
    const cities = [...new Set(pairs.filter(([from]) => !origin.value || from === origin.value).map(([, to]) => to))].sort();
    destination.replaceChildren(new Option("Any destination", ""), ...cities.map(city => new Option(city, city)));
    if (cities.includes(previous)) destination.value = previous;
  });
});
