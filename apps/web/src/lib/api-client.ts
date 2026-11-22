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
    const envUrl =
      typeof process !== "undefined"
        ? process.env.NEXT_PUBLIC_API_BASE_URL || process.env.NEXT_PUBLIC_API_URL
        : undefined;

    if (baseUrl) {
      this.baseUrl = baseUrl.replace(/\/+$/, "");
    } else if (envUrl) {
      this.baseUrl = envUrl.replace(/\/+$/, "");
    } else if (typeof window !== "undefined") {
      const host = window.location.hostname;
      const isLocal = host === "localhost" || host === "127.0.0.1";
      this.baseUrl = isLocal ? "http://127.0.0.1:8000/api/v1" : "https://gramaseva-0p3u.onrender.com/api/v1";
    } else {
      this.baseUrl = "http://127.0.0.1:8000/api/v1";
    }
  }

  public getBaseUrl(): string {
    return this.baseUrl;
  }

  private getCandidateBaseUrls(): string[] {
    const list: string[] = [];
    if (this.baseUrl) {
      list.push(this.baseUrl);
    }
    if (typeof window !== "undefined") {
      const host = window.location.hostname;
      const isLocal = host === "localhost" || host === "127.0.0.1";
      if (isLocal) {
        if (!list.includes("http://127.0.0.1:8000/api/v1")) list.push("http://127.0.0.1:8000/api/v1");
        if (!list.includes("http://localhost:8000/api/v1")) list.push("http://localhost:8000/api/v1");
        if (!list.includes("/api/v1")) list.push("/api/v1");
      } else {
        if (!list.includes("https://gramaseva-0p3u.onrender.com/api/v1")) list.push("https://gramaseva-0p3u.onrender.com/api/v1");
        if (!list.includes("/api/v1")) list.push("/api/v1");
      }
    }
    return list;
  }

  private async request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const { timeoutMs = 25000, token, headers = {}, ...rest } = options;
    const cleanEndpoint = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;

    const candidates = this.getCandidateBaseUrls();
    let lastError: any = null;

    for (let i = 0; i < candidates.length; i++) {
      const candidate = candidates[i];
      const url = `${candidate}${cleanEndpoint}`;

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

        // Remember working endpoint if different from initial
        if (candidate !== this.baseUrl && !candidate.startsWith("/")) {
          this.baseUrl = candidate;
        }

        // Read the response body stream EXACTLY ONCE as text to prevent stream exhaustion errors
        const rawText = await response.text();
        let parsedData: any = null;
        if (rawText && rawText.trim().length > 0) {
          try {
            parsedData = JSON.parse(rawText);
          } catch {
            parsedData = rawText;
          }
        }

        if (!response.ok) {
          const message =
            (typeof parsedData === "object" && parsedData !== null && (parsedData.detail || parsedData.message || parsedData.error)) ||
            (typeof parsedData === "string" && parsedData.trim().length > 0 && parsedData) ||
            `Request failed with status ${response.status}`;

          throw new ApiError(
            typeof message === "string" ? message : JSON.stringify(message),
            response.status,
            parsedData
          );
        }

        if (response.status === 204 || parsedData === null || parsedData === undefined) {
          return {} as T;
        }

        return parsedData as T;
      } catch (err: any) {
        clearTimeout(timeoutId);
        if (err instanceof ApiError) {
          // Server responded with an HTTP status (e.g. 400, 401, 403, 404), so server was reached!
          throw err;
        }

        // Connection/network error
        lastError = err;
        if (i < candidates.length - 1) {
          console.warn(`[ApiClient] Failed to connect to ${candidate}, trying fallback endpoint ${candidates[i + 1]}...`);
          continue;
        }
      }
    }

    if (lastError?.name === "AbortError") {
      throw new ApiError(
        "Request timed out after " + Math.round(timeoutMs / 1000) + "s. Please verify connection and retry.",
        408
      );
    }

    const rawMsg = lastError?.message || "Network error";
    const userMsg =
      rawMsg.toLowerCase().includes("failed to fetch") || rawMsg.toLowerCase().includes("networkerror")
        ? `Could not reach the GramaSeva API server (${this.baseUrl}). Please verify server is running or check your connection.`
        : rawMsg;
    throw new ApiError(userMsg, 0);
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

export function getMediaUrl(mediaPathOrId?: string): string {
  if (!mediaPathOrId) return "";
  if (mediaPathOrId.startsWith("http://") || mediaPathOrId.startsWith("https://")) {
    return mediaPathOrId;
  }
  const clean = mediaPathOrId.startsWith("/") ? mediaPathOrId : `/${mediaPathOrId}`;
  const fullPath = clean.startsWith("/api/v1") ? clean : `/api/v1/public/media/${clean.replace(/^\//, "")}/view`;

  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    const isLocal = host === "localhost" || host === "127.0.0.1";
    if (isLocal) {
      return `http://127.0.0.1:8000${fullPath}`;
    }
    const envApi = process.env.NEXT_PUBLIC_API_BASE_URL || process.env.NEXT_PUBLIC_API_URL;
    if (envApi) {
      const baseHost = envApi.replace(/\/api\/v1\/?$/, "").replace(/\/+$/, "");
      return `${baseHost}${fullPath}`;
    }
    return `https://gramaseva-0p3u.onrender.com${fullPath}`;
  }
  return fullPath;
}
