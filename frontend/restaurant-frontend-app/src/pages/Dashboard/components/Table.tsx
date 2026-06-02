type ReportRow = {
  location: string;
  waiter: string;
  waiterEmail: string;
  reportPeriodStart: string;
  reportPeriodEnd: string;
  waiterWorkingHours: string;
  waiterOrdersProcessed: number;
  deltaOrdersVsPrevious: string;
  avgServiceFeedback: number;
  minServiceFeedback: number;
  deltaAvgFeedbackVsPrevious: string;
};

const reportRows: ReportRow[] = [
  {
    location: "Downtown",
    waiter: "John Doe",
    waiterEmail: "john.doe@restaurant.com",
    reportPeriodStart: "Jan 13, 2025",
    reportPeriodEnd: "Jan 19, 2025",
    waiterWorkingHours: "42h",
    waiterOrdersProcessed: 187,
    deltaOrdersVsPrevious: "+3%",
    avgServiceFeedback: 4.6,
    minServiceFeedback: 3.8,
    deltaAvgFeedbackVsPrevious: "+2%",
  },
  {
    location: "Riverside",
    waiter: "Ana Smith",
    waiterEmail: "ana.smith@restaurant.com",
    reportPeriodStart: "Jan 13, 2025",
    reportPeriodEnd: "Jan 19, 2025",
    waiterWorkingHours: "39h",
    waiterOrdersProcessed: 163,
    deltaOrdersVsPrevious: "-2%",
    avgServiceFeedback: 4.4,
    minServiceFeedback: 3.5,
    deltaAvgFeedbackVsPrevious: "-1%",
  },
  {
    location: "Old Town",
    waiter: "Mark Lee",
    waiterEmail: "mark.lee@restaurant.com",
    reportPeriodStart: "Jan 13, 2025",
    reportPeriodEnd: "Jan 19, 2025",
    waiterWorkingHours: "41h",
    waiterOrdersProcessed: 175,
    deltaOrdersVsPrevious: "+1%",
    avgServiceFeedback: 4.5,
    minServiceFeedback: 3.7,
    deltaAvgFeedbackVsPrevious: "+3%",
  },
];

const thClass = "px-4 py-5 whitespace-nowrap font-semibold";
const tdClass = "px-4 py-2 whitespace-nowrap";

const ReportTable = () => {
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
          {reportRows.map((row) => (
            <tr key={row.waiterEmail}>
              <td className={tdClass}>{row.location}</td>
              <td className={tdClass}>{row.waiter}</td>
              <td className={tdClass}>{row.waiterEmail}</td>
              <td className={tdClass}>{row.reportPeriodStart}</td>
              <td className={tdClass}>{row.reportPeriodEnd}</td>
              <td className={tdClass}>{row.waiterWorkingHours}</td>
              <td className={tdClass}>{row.waiterOrdersProcessed}</td>
              <td className={tdClass}>{row.deltaOrdersVsPrevious}</td>
              <td className={tdClass}>{row.avgServiceFeedback}</td>
              <td className={tdClass}>{row.minServiceFeedback}</td>
              <td className={tdClass}>{row.deltaAvgFeedbackVsPrevious}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default ReportTable;
