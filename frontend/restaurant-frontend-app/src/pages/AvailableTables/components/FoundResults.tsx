import Card from "./Card";
import { type TableResult } from "../availableTables.services";
import { LOCATIONS } from "../availableTables.config";

type FoundResultsProps = {
  tables: TableResult[];
  locationId: string;
  date: string;
};

const FoundResults = ({ tables, locationId, date }: FoundResultsProps) => {
  const location = LOCATIONS.find((l) => l.id === locationId);

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
            locationAddress={location?.address ?? ""}
            date={date}
          />
        ))}
      </section>
    </>
  );
};

export default FoundResults;
