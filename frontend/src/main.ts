import { ApiError, predict, type MachineReading, type Prediction, type ProductType } from "./api";
import "./style.css";

const form = document.querySelector<HTMLFormElement>("#predict-form")!;
const result = document.querySelector<HTMLElement>("#result")!;
const button = form.querySelector<HTMLButtonElement>("button")!;

function readForm(): MachineReading {
  const data = new FormData(form);
  const number = (name: string): number => Number(data.get(name));
  return {
    type: data.get("type") as ProductType,
    air_temperature_k: number("air_temperature_k"),
    process_temperature_k: number("process_temperature_k"),
    rotational_speed_rpm: number("rotational_speed_rpm"),
    torque_nm: number("torque_nm"),
    tool_wear_min: number("tool_wear_min"),
  };
}

function showPrediction(prediction: Prediction): void {
  const atRisk = prediction.prediction === 1;
  const percent = (prediction.failure_probability * 100).toFixed(1);
  result.className = `result ${atRisk ? "risk" : "ok"}`;
  // textContent (not innerHTML) so nothing from the response is interpreted as HTML.
  result.replaceChildren(
    element("p", "status", atRisk ? "AT RISK" : "OK"),
    element("p", "probability", `Failure probability: ${percent}%`),
    element("p", "meta", `Model version ${prediction.model_version}`),
  );
  result.hidden = false;
}

function showError(message: string): void {
  result.className = "result error";
  result.replaceChildren(element("p", "status", "Error"), element("p", "meta", message));
  result.hidden = false;
}

function element(tag: string, className: string, text: string): HTMLElement {
  const node = document.createElement(tag);
  node.className = className;
  node.textContent = text;
  return node;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!form.reportValidity()) return;

  button.disabled = true;
  try {
    showPrediction(await predict(readForm()));
  } catch (error) {
    showError(error instanceof ApiError ? error.message : "Cannot reach the service.");
  } finally {
    button.disabled = false;
  }
});
