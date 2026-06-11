import getApiBaseUrl from "../../config/GetApiBaseUrl";

export type DashboardReportType = "staff-performance" | "sales";

export interface FetchReportParams {
  reportType: DashboardReportType;
  periodStart: string;
  periodEnd: string;
  locationId: string;
  accessToken?: string;
}

export interface StaffPerformanceRow {
  location: string;
  waiter: string;
  waiterEmail: string;
  reportPeriodStart: string;
  reportPeriodEnd: string;
  waiterWorkingHours: string;
  waiterOrdersProcessed: number;
  deltaWaiterOrdersProcessedPct: string;
  averageServiceFeedback: string;
  minimumServiceFeedback: number;
  deltaAverageServiceFeedbackPct: string;
}

export interface SalesRow {
  location: string;
  reportPeriodStart: string;
  reportPeriodEnd: string;
  ordersProcessed: number;
  deltaOrdersProcessedPct: string;
  revenue: string;
  deltaRevenuePct: string;
  averageCuisineFeedback: string;
  deltaAverageCuisineFeedbackPct: string;
  minimumCuisineFeedback: number;
}

export type BackendReportRow = StaffPerformanceRow | SalesRow;

export interface BackendReportResponse {
  reportType: string;
  periodStart: string;
  periodEnd: string;
  rows: BackendReportRow[];
}

const toBackendReportType = (type: DashboardReportType): string => {
  return type === "staff-performance" ? "staff_performance" : "sales";
};

const getErrorMessage = (payload: unknown, fallback: string): string => {
  if (typeof payload !== "object" || payload === null) return fallback;
  const maybe = payload as Record<string, unknown>;

  if (typeof maybe.message === "string" && maybe.message) return maybe.message;
  if (typeof maybe.error === "string" && maybe.error) return maybe.error;

  return fallback;
};

export const fetchDashboardReport = async (
  params: FetchReportParams,
): Promise<BackendReportResponse> => {
  const query = new URLSearchParams({
    reportType: toBackendReportType(params.reportType),
    periodStart: params.periodStart,
    periodEnd: params.periodEnd,
    locationId: params.locationId,
  });

  const response = await fetch(
    `${getApiBaseUrl()}/reports?${query.toString()}`,
    {
      method: "GET",
      headers: {
        ...(params.accessToken
          ? { Authorization: `Bearer ${params.accessToken}` }
          : {}),
      },
    },
  );

  const payload: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(
      getErrorMessage(payload, `Failed to fetch report (${response.status})`),
    );
  }

  const data = payload as BackendReportResponse;

  if (!Array.isArray(data?.rows)) {
    return {
      reportType: data?.reportType ?? "",
      periodStart: data?.periodStart ?? params.periodStart,
      periodEnd: data?.periodEnd ?? params.periodEnd,
      rows: [],
    };
  }

  return data;
};
