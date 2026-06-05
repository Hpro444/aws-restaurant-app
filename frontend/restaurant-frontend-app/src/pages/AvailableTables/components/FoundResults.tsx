import type { TableResult } from "../../../types/location";
import Card from "./Card";

type FoundResultsProps = {
  tables: TableResult[];
  locationAddress: string;
  date: string;
};

const FoundResults = ({ tables, locationAddress, date }: FoundResultsProps) => {
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
            locationAddress={locationAddress}
            date={date}
          />
        ))}
      </section>
    </>
  );
};

export default FoundResults;
