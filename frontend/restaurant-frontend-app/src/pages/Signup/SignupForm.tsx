import classes from "./signup.styles";
import FormInput from "./components/FormInput";
import {
  confirmRules,
  emailField,
  nameFields,
  passwordRules,
} from "./signup.config";
import RulesList from "./components/RulesList";

const SignUpForm = () => {
  return (
    <form className={classes.form}>
      <div className={classes.row}>
        {nameFields.map((field) => (
          <FormInput
            key={field.id}
            id={field.id}
            name={field.name}
            label={field.label}
            placeholder={field.placeholder}
            example={field.example}
            type={field.type}
          />
        ))}
      </div>
      <FormInput
        id={emailField.id}
        name={emailField.name}
        label={emailField.label}
        placeholder={emailField.placeholder}
        example={emailField.example}
        type={emailField.type}
        className="w-full"
      />
      <div className="flex flex-col gap-1">
        <div className="flex justify-between">
          <label htmlFor="password" className={classes.label}>
            Password
          </label>
          <ul className="hidden" aria-hidden="true">
            <li>
              <span className="mt-1 mr-1 inline-block w-2 h-2 rounded-full bg-[var(--color-brand)] shrink-0" />
              <small className="font-light text-xs leading-4 tracking-normal">
                Strong
              </small>
            </li>
          </ul>
        </div>
        <input
          type="password"
          id="password"
          name="password"
          required
          placeholder="Enter your password"
          className={classes.input + " w-full"}
        />
        <RulesList items={passwordRules} />
      </div>
      <div className="flex flex-col gap-1">
        <label htmlFor="confirmPassword" className={classes.label}>
          Confirm Password
        </label>
        <input
          type="password"
          name="confirmPassword"
          id="confirmPassword"
          required
          placeholder="Confirm your password"
          className={classes.input + " w-full"}
        />
        <RulesList items={confirmRules} />
      </div>
      <div className={classes.actionWrap}>
        <button type="submit" className={classes.submit}>
          Create Account
        </button>
        <p className={classes.loginText}>
          Already have an account?{""}
          <a href="/login" className={classes.loginLink}>
            Login
          </a>{" "}
          instead
        </p>
      </div>
    </form>
  );
};

export default SignUpForm;
