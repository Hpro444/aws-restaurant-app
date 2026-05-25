import Card from "./Card";

const FoundResults = () => {
  return (
    <>
      <p>4 tables available</p>
      <section className="grid grid-cols-2 grid-rows-2 gap-8">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i} number={i + 1} />
        ))}
      </section>
    </>
  );
};

export default FoundResults;
