export class ApiError extends Error {
  public status: number;
  public details?: unknown;

  constructor(message: string, status: number, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

export interface RequestOptions extends RequestInit {
  timeoutMs?: number;
  token?: string;
}

export class ApiClient {
  private baseUrl: string;

  constructor(baseUrl?: string) {
    this.baseUrl =
      baseUrl ||
      (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_BASE_URL) ||
      "http://localhost:8000/api/v1";
  }

  private async request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const { timeoutMs = 15000, token, headers = {}, ...rest } = options;
    const url = `${this.baseUrl}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    const isFormData = typeof FormData !== "undefined" && rest.body instanceof FormData;

    const mergedHeaders: Record<string, string> = {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      Accept: "application/json",
      ...(headers as Record<string, string>),
    };

    const effectiveToken =
      token ||
      (typeof window !== "undefined"
        ? localStorage.getItem("gramaseva_token") || localStorage.getItem("access_token")
        : undefined);

    if (effectiveToken) {
      mergedHeaders["Authorization"] = `Bearer ${effectiveToken}`;
    }

    try {
      const response = await fetch(url, {
        ...rest,
        headers: mergedHeaders,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        let errorData: any = null;
        try {
          errorData = await response.json();
        } catch {
          errorData = await response.text();
        }

        const message =
          (typeof errorData === "object" && errorData?.detail) ||
          (typeof errorData === "string" && errorData) ||
          `Request failed with status ${response.status}`;

        throw new ApiError(message, response.status, errorData);
      }

      if (response.status === 204) {
        return {} as T;
      }

      return (await response.json()) as T;
    } catch (err: any) {
      clearTimeout(timeoutId);
      if (err.name === "AbortError") {
        throw new ApiError("Request timed out after " + timeoutMs + "ms", 408);
      }
      if (err instanceof ApiError) {
        throw err;
      }
      throw new ApiError(err.message || "Network error", 0);
    }
  }

  public get<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: "GET" });
  }

  public post<T>(endpoint: string, body?: unknown, options?: RequestOptions): Promise<T> {
    const isFormData = typeof FormData !== "undefined" && body instanceof FormData;
    return this.request<T>(endpoint, {
      ...options,
      method: "POST",
      body: isFormData ? (body as any) : body !== undefined ? JSON.stringify(body) : undefined,
    });
  }

  public postForm<T>(endpoint: string, formData: FormData, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: "POST",
      body: formData as any,
    });
  }

  public patch<T>(endpoint: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: "PATCH",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  }

  public delete<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: "DELETE" });
  }

  public async checkHealth(): Promise<{ status: string; version: string }> {
    try {
      return await this.get<{ status: string; version: string }>("/health");
    } catch {
      return { status: "degraded", version: "0.1.0" };
    }
  }
}

export const apiClient = new ApiClient();
