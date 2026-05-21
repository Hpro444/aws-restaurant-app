import classes from "../signup.styles";

const VALID_COLOR = "#00AD0C";
const INVALID_COLOR = "#B70B0B";
const NEUTRAL_COLOR = "#898989";

type RuleItem = {
  text: string;
  isMet: boolean;
};

type RulesListProps = {
  items: RuleItem[];
  hasInput: boolean;
};

const RulesList = ({ items, hasInput }: RulesListProps) => {
  return (
    <ul className={classes.rulesList}>
      {items.map((item) => {
        const color = !hasInput
          ? NEUTRAL_COLOR
          : item.isMet
            ? VALID_COLOR
            : INVALID_COLOR;

        return (
          <li key={item.text} className={classes.ruleItem}>
            <span
              className={classes.ruleDot}
              style={{ backgroundColor: color }}
            />
            <small className={classes.helper} style={{ color }}>
              {item.text}
            </small>
          </li>
        );
      })}
    </ul>
  );
};

export default RulesList;
