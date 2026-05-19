import classes from "../signup.styles";

const RulesList = ({ items }: { items: string[] }) => {
  return (
    <ul className={classes.rulesList}>
      {items.map((item) => (
        <li key={item} className={classes.ruleItem}>
          <span className={classes.ruleDot} />
          <small className={classes.helper}>{item}</small>
        </li>
      ))}
    </ul>
  );
};

export default RulesList;
