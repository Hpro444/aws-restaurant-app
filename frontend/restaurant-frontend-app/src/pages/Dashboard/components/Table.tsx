import type {
  BackendReportRow,
  DashboardReportType,
  StaffPerformanceRow,
  SalesRow,
} from "../dashboard.services";

type ReportTableProps = {
  rows: BackendReportRow[];
  isLoading?: boolean;
  reportType: DashboardReportType | "";
};

const thClass = "px-4 py-5 whitespace-nowrap font-semibold";
const tdClass = "px-4 py-2 whitespace-nowrap";

const isStaffPerformanceRow = (
  row: BackendReportRow,
): row is StaffPerformanceRow => {
  return "waiter" in row;
};

const isSalesRow = (row: BackendReportRow): row is SalesRow => {
  return "revenue" in row;
};

const ReportTable = ({
  rows,
  isLoading = false,
  reportType,
}: ReportTableProps) => {
  if (reportType === "staff-performance") {
    return (
      <div className="w-full max-w-[1363px] overflow-x-auto rounded-lg border border-[#dadada]">
        <table className="min-w-[1800px] w-full border-collapse text-left text-sm">
          <thead className="bg-[#E9FFEA] font-medium text-[14px] leading-[24px] tracking-normal">
            <tr>
              <th className={thClass}>Location</th>
              <th className={thClass}>Waiter</th>
              <th className={thClass}>Waiter's email</th>
              <th className={thClass}>Report period start</th>
              <th className={thClass}>Report period end</th>
              <th className={thClass}>Waiter working hours</th>
              <th className={thClass}>Waiter Orders processed</th>
              <th className={thClass}>
                Delta of Waiter Orders processed to previous period in %
              </th>
              <th className={thClass}>
                Average Service Feedback Waiter (1 to 5)
              </th>
              <th className={thClass}>
                Minimum Service Feedback Waiter (1 to 5)
              </th>
              <th className={thClass}>
                Delta of Average Service Feedback Waiter to previous period in %
              </th>
            </tr>
          </thead>

          <tbody className="font-light text-[14px] leading-[24px] tracking-normal align-middle">
            {isLoading ? (
              <tr>
                <td className={tdClass} colSpan={11}>
                  Loading report...
                </td>
              </tr>
            ) : rows.length === 0 ? (
              <tr>
                <td className={tdClass} colSpan={11}>
                  No report data. Select filters and click Generate Report.
                </td>
              </tr>
            ) : (
              rows.map((row) => {
                if (!isStaffPerformanceRow(row)) return null;
                return (
                  <tr
                    key={
                      row.waiterEmail +
                      "-" +
                      row.reportPeriodStart +
                      "-" +
                      row.reportPeriodEnd
                    }
                  >
                    <td className={tdClass}>{row.location}</td>
                    <td className={tdClass}>{row.waiter}</td>
                    <td className={tdClass}>{row.waiterEmail}</td>
                    <td className={tdClass}>{row.reportPeriodStart}</td>
                    <td className={tdClass}>{row.reportPeriodEnd}</td>
                    <td className={tdClass}>{row.waiterWorkingHours}</td>
                    <td className={tdClass}>{row.waiterOrdersProcessed}</td>
                    <td className={tdClass}>
                      {row.deltaWaiterOrdersProcessedPct}
                    </td>
                    <td className={tdClass}>{row.averageServiceFeedback}</td>
                    <td className={tdClass}>{row.minimumServiceFeedback}</td>
                    <td className={tdClass}>
                      {row.deltaAverageServiceFeedbackPct}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    );
  }

  if (reportType === "sales") {
    return (
      <div className="w-full max-w-[1363px] overflow-x-auto rounded-lg border border-[#dadada]">
        <table className="min-w-[1200px] w-full border-collapse text-left text-sm">
          <thead className="bg-[#E9FFEA] font-medium text-[14px] leading-[24px] tracking-normal">
            <tr>
              <th className={thClass}>Location</th>
              <th className={thClass}>Report period start</th>
              <th className={thClass}>Report period end</th>
              <th className={thClass}>Orders Processed</th>
              <th className={thClass}>Delta Orders Processed %</th>
              <th className={thClass}>Revenue</th>
              <th className={thClass}>Delta Revenue %</th>
              <th className={thClass}>Average Cuisine Feedback (1 to 5)</th>
              <th className={thClass}>Minimum Cuisine Feedback (1 to 5)</th>
              <th className={thClass}>Delta Average Cuisine Feedback %</th>
            </tr>
          </thead>

          <tbody className="font-light text-[14px] leading-[24px] tracking-normal align-middle">
            {isLoading ? (
              <tr>
                <td className={tdClass} colSpan={10}>
                  Loading report...
                </td>
              </tr>
            ) : rows.length === 0 ? (
              <tr>
                <td className={tdClass} colSpan={10}>
                  No report data. Select filters and click Generate Report.
                </td>
              </tr>
            ) : (
              rows.map((row) => {
                if (!isSalesRow(row)) return null;
                return (
                  <tr
                    key={
                      row.location +
                      "-" +
                      row.reportPeriodStart +
                      "-" +
                      row.reportPeriodEnd
                    }
                  >
                    <td className={tdClass}>{row.location}</td>
                    <td className={tdClass}>{row.reportPeriodStart}</td>
                    <td className={tdClass}>{row.reportPeriodEnd}</td>
                    <td className={tdClass}>{row.ordersProcessed}</td>
                    <td className={tdClass}>{row.deltaOrdersProcessedPct}</td>
                    <td className={tdClass}>${row.revenue}</td>
                    <td className={tdClass}>{row.deltaRevenuePct}</td>
                    <td className={tdClass}>{row.averageCuisineFeedback}</td>
                    <td className={tdClass}>{row.minimumCuisineFeedback}</td>
                    <td className={tdClass}>
                      {row.deltaAverageCuisineFeedbackPct}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    );
  }

  return (
    <div className="w-full max-w-[1363px] rounded-lg border border-[#dadada] p-4">
      <p className="text-[#898989]">
        Select report type, location, and period to generate a report.
      </p>
    </div>
  );
};

export default ReportTable;
