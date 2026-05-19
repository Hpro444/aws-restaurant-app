import type { FormInputProps } from "../signup.types";
import classes from "../signup.styles";

const FormInput = ({
  id,
  label,
  example,
  className = "",
  ...props
}: FormInputProps) => {
  const helperId = example ? `${id}-helper` : undefined;

  return (
    <div className={classes.fieldWrap}>
      <label htmlFor={id} className={classes.label}>
        {label}
      </label>
      <input
        type="text"
        id={id}
        placeholder="Enter your first name"
        className={classes.input + " " + className}
        aria-describedby={helperId}
        {...props}
      />
      {example ? <small className={classes.helper}>{example}</small> : null}
    </div>
  );
};

export default FormInput;