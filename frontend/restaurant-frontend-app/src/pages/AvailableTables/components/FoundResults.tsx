import type { TableResult } from "../../../types/location";
import Card from "./Card";

type FoundResultsProps = {
  locationId: string;
  tables: TableResult[];
  date: string;
  initialGuests?: number;
};

const FoundResults = ({
  tables,
  date,
  initialGuests = 1,
  locationId,
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
            date={date}
            initialGuests={initialGuests}
            locationId={locationId}
          />
        ))}
      </section>
    </>
  );
};

export default FoundResults;
