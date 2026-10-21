export type ProductType = "L" | "M" | "H";

export interface MachineReading {
  type: ProductType;
  air_temperature_k: number;
  process_temperature_k: number;
  rotational_speed_rpm: number;
  torque_nm: number;
  tool_wear_min: number;
}

export interface Prediction {
  failure_probability: number;
  prediction: 0 | 1;
  model_version: string;
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

// Same-origin path: nginx (or the Vite dev proxy) forwards it to the API and adds the key.
const PREDICT_URL = "/api/predict";

export async function predict(reading: MachineReading): Promise<Prediction> {
  const response = await fetch(PREDICT_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(reading),
  });
  if (!response.ok) {
    throw new ApiError(response.status, await errorMessage(response));
  }
  return (await response.json()) as Prediction;
}

async function errorMessage(response: Response): Promise<string> {
  if (response.status === 503) return "The model is not ready yet. Try again shortly.";
  if (response.status === 401) return "The proxy is not authorized to call the API.";
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (Array.isArray(body.detail)) {
      // FastAPI 422: a list of { loc, msg } validation errors.
      return body.detail
        .map((e: { loc?: unknown[]; msg?: string }) => `${e.loc?.at(-1)}: ${e.msg}`)
        .join("; ");
    }
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // Body was not JSON: fall through to the generic message.
  }
  return `Request failed with status ${response.status}.`;
}
