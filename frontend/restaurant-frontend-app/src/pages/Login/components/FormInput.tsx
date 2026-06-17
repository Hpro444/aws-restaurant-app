import type { FormInputProps } from "../../../types/auth";
import classes from "../login.styles";

const FormInput = ({
  id,
  label,
  example,
  helperText,
  helperColor,
  inputBorderColor,
  className = "",
  ...props
}: FormInputProps) => {
  const text = helperText ?? example;
  const helperId = text ? `${id}-helper` : undefined;

  return (
    <div className={classes.fieldWrap}>
      <label htmlFor={id} className={classes.label}>
        {label}
      </label>

      <input
        id={id}
        className={classes.input + " " + className}
        aria-describedby={helperId}
        style={
          inputBorderColor
            ? {
                borderColor: inputBorderColor,
                boxShadow: `0 0 0 1px ${inputBorderColor}22`,
              }
            : undefined
        }
        {...props}
      />

      {text && (
        <small
          id={helperId}
          className={classes.helper}
          style={{ color: helperColor }}
        >
          {text}
        </small>
      )}
    </div>
  );
};

export default FormInput;
