import classes from "../login.styles";
import FormInput from "./FormInput.tsx";
import { emailField } from "../login.config";
import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";

import eyeClosed from "../../../assets/signup/Eye closed.png";
import eyeOpen from "../../../assets/signup/Eye.png";

const VALID_COLOR = "#00AD0C";
const INVALID_COLOR = "#B70B0B";
const NEUTRAL_COLOR = "#898989";

const ACCOUNT_LOCKED_MESSAGE =
  "Your account is temporarily locked due to multiple failed login attempts. Please try again later.";

const EMAIL_ERROR =
  "Email address is required. Please enter your email to continue";
const PASSWORD_ERROR =
  "Password is required. Please enter your password to continue";

const isValidEmail = (value: string) =>
  /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());

type LoginFormValues = {
  email: string;
  password: string;
};

const LoginForm = () => {
  const [showPassword, setShowPassword] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [accountLocked, setAccountLocked] = useState(false);

  const {
    register,
    handleSubmit,
    control,
    formState: { errors, touchedFields, isValid, isSubmitting },
  } = useForm<LoginFormValues>({
    mode: "onChange",
    defaultValues: {
      email: "",
      password: "",
    },
  });

  const email = useWatch({ control, name: "email" });
  const password = useWatch({ control, name: "password" });

  const hasEmailValue = (email || "").trim().length > 0;
  const isEmailValid = !errors.email && hasEmailValue;
  const hasPasswordValue = (password || "").trim().length > 0;
  const isPasswordValid = !errors.password && hasPasswordValue;

  const canSubmit =
    isValid &&
    !accountLocked &&
    !isSubmitting &&
    isEmailValid &&
    isPasswordValid;

  const getInvalidBorderColor = (isTouched?: boolean, hasError?: boolean) =>
    isTouched && hasError ? INVALID_COLOR : undefined;

  const getHelperColor = (isTouched?: boolean, hasError?: boolean) =>
    isTouched && hasError ? INVALID_COLOR : NEUTRAL_COLOR;

  const emailBorder = getInvalidBorderColor(
    touchedFields.email,
    !!errors.email,
  );
  const passwordBorder =
    errorMessage || accountLocked
      ? INVALID_COLOR
      : getInvalidBorderColor(touchedFields.password, !!errors.password);

  const emailColor = getHelperColor(touchedFields.email, !!errors.email);

  const emailHelper =
    touchedFields.email && errors.email ? EMAIL_ERROR : emailField.example;

  const passwordHelper =
    touchedFields.password && errors.password ? PASSWORD_ERROR : "";

  const onSubmit = async (data: LoginFormValues) => {
    console.log("Login payload", data);
    setErrorMessage("");
    setAccountLocked(false);
  };

  return (
    <form
      className={`${classes.form} w-[496px]`}
      onSubmit={handleSubmit(onSubmit)}
    >
      {accountLocked && (
        <div className="bg-[#fde8e8] border border-[#f5c2c7] text-[#b70b0b] rounded-lg p-4 mb-6 text-base font-medium">
          {ACCOUNT_LOCKED_MESSAGE}
        </div>
      )}

      <FormInput
        id={emailField.id}
        label={emailField.label}
        placeholder={emailField.placeholder}
        type={emailField.type}
        className="w-full"
        helperText={emailHelper}
        helperColor={emailColor}
        inputBorderColor={emailBorder}
        {...register("email", {
          required: EMAIL_ERROR,
          validate: {
            isValidEmail: (value) => isValidEmail(value) || EMAIL_ERROR,
          },
        })}
      />

      <div className={classes.fieldWrap}>
        <label htmlFor="password" className={classes.label}>
          Password
        </label>

        <div className="relative">
          <input
            type={showPassword ? "text" : "password"}
            id="password"
            required
            placeholder="Enter your password"
            className={classes.input + " w-full pr-12"}
            style={
              passwordBorder
                ? {
                    borderColor: passwordBorder,
                    boxShadow: "0 0 0 1px " + passwordBorder + "22",
                  }
                : undefined
            }
            disabled={accountLocked}
            {...register("password", {
              required: PASSWORD_ERROR,
              validate: {
                hasValue: (value) => value.trim().length > 0 || PASSWORD_ERROR,
              },
            })}
          />
          <button
            type="button"
            onClick={() => setShowPassword((prev) => !prev)}
            aria-label={showPassword ? "Hide password" : "Show password"}
            aria-pressed={showPassword}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-[#666] hover:text-[var(--color-text-primary)] focus:outline-none cursor-pointer"
            disabled={accountLocked}
          >
            <img
              src={showPassword ? eyeClosed : eyeOpen}
              alt="Toggle password visibility"
            />
          </button>
        </div>
        {!accountLocked && errorMessage && (
          <div
            className={classes.helper}
            style={{ color: INVALID_COLOR, marginTop: "4px" }}
          >
            {errorMessage}
          </div>
        )}
        <small
          className={classes.helper}
          style={{
            color: getHelperColor(touchedFields.password, !!errors.password),
          }}
        >
          {passwordHelper}
        </small>

        <a href="/forgot-password" className={classes.loginLink}>
          Forgot password?
        </a>
      </div>

      <div className={classes.actionWrap}>
        <button
          type="submit"
          disabled={!canSubmit}
          className={classes.submit}
          style={{
            backgroundColor: canSubmit ? VALID_COLOR : NEUTRAL_COLOR,
            cursor: canSubmit ? "pointer" : "not-allowed",
            opacity: canSubmit ? 1 : 0.85,
          }}
        >
          {isSubmitting ? "Signing In..." : "Sign In"}
        </button>

        <p className={classes.loginText}>
          Don't have an account?{" "}
          <a href="/signup" className={classes.loginLink}>
            Create an Account
          </a>
        </p>
      </div>
    </form>
  );
};

export default LoginForm;
