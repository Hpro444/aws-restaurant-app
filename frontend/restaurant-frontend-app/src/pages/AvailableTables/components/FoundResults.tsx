import type { TableResult } from "../../../types/location";
import Card from "./Card";

type FoundResultsProps = {
  tables: TableResult[];
  locationAddress: string;
  locationId: string;
  date: string;
  initialGuests: number;
};

const FoundResults = ({
  tables,
  locationId,
  locationAddress,
  date,
  initialGuests,
}: FoundResultsProps) => {
  return (
    <>
      <p>
        {tables.length} {tables.length === 1 ? "table" : "tables"} available
      </p>
      <section className="grid grid-cols-2 gap-8">
        {tables.map((table) => (
          <Card
            key={table.table_id}
            table={table}
            locationId={locationId}
            locationAddress={locationAddress}
            date={date}
            initialGuests={initialGuests}
          />
        ))}
      </section>
    </>
  );
};

export default FoundResults;
