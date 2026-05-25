import classes from "../signup.styles";
import FormInput from "./FormInput";
import {
  confirmRules,
  emailField,
  nameFields,
  passwordRules,
} from "../signup.config";
import RulesList from "./RulesList";
import { useMemo, useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { Link } from "react-router-dom";

import eyeClosed from "../../../assets/signup/Eye closed.png";
import eyeOpen from "../../../assets/signup/Eye.png";

const VALID_COLOR = "#00AD0C";
const INVALID_COLOR = "#B70B0B";
const NEUTRAL_COLOR = "#898989";

const FIRST_NAME_ERROR =
  "First name must be up to 50 characters. Only Latin letters, hyphens, and apostrophes are allowed.";
const LAST_NAME_ERROR =
  "Last name must be up to 50 characters. Only Latin letters, hyphens, and apostrophes are allowed.";
const EMAIL_ERROR =
  "Invalid email address. Please ensure it follows the format: username@domain.com";

type SignupFormValues = {
  firstName: string;
  lastName: string;
  email: string;
  password: string;
  confirmPassword: string;
};

const SignUpForm = () => {
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const {
    register,
    handleSubmit,
    control,
    formState: { errors, touchedFields, isValid, isSubmitting },
  } = useForm<SignupFormValues>({
    mode: "onChange",
    defaultValues: {
      firstName: "",
      lastName: "",
      email: "",
      password: "",
      confirmPassword: "",
    },
  });

  const password = useWatch({ control, name: "password" });
  const confirmPassword = useWatch({ control, name: "confirmPassword" });

  const passwordChecks = useMemo(
    () => ({
      lowercase: /[a-z]/.test(password),
      uppercase: /[A-Z]/.test(password),
      number: /\d/.test(password),
      special: /[^A-Za-z0-9]/.test(password),
      length: password.length >= 8 && password.length <= 16,
      confirm: confirmPassword.length > 0 && confirmPassword === password,
    }),
    [password, confirmPassword],
  );

  const passwordRuleItems = [
    { text: passwordRules[0], isMet: passwordChecks.lowercase },
    { text: passwordRules[1], isMet: passwordChecks.uppercase },
    { text: passwordRules[2], isMet: passwordChecks.number },
    { text: passwordRules[3], isMet: passwordChecks.special },
    { text: passwordRules[4], isMet: passwordChecks.length },
  ];

  const confirmRuleItems = [
    { text: confirmRules[0], isMet: passwordChecks.confirm },
  ];

  const getInvalidBorderColor = (isTouched?: boolean, hasError?: boolean) =>
    isTouched && hasError ? INVALID_COLOR : undefined;

  const getHelperColor = (isTouched?: boolean, hasError?: boolean) =>
    isTouched && hasError ? INVALID_COLOR : NEUTRAL_COLOR;

  const firstNameBorder = getInvalidBorderColor(
    touchedFields.firstName,
    !!errors.firstName,
  );
  const lastNameBorder = getInvalidBorderColor(
    touchedFields.lastName,
    !!errors.lastName,
  );
  const emailBorder = getInvalidBorderColor(
    touchedFields.email,
    !!errors.email,
  );
  const passwordBorder = getInvalidBorderColor(
    touchedFields.password,
    !!errors.password,
  );
  const confirmBorder = getInvalidBorderColor(
    touchedFields.confirmPassword,
    !!errors.confirmPassword,
  );

  const firstNameColor = getHelperColor(
    touchedFields.firstName,
    !!errors.firstName,
  );
  const lastNameColor = getHelperColor(
    touchedFields.lastName,
    !!errors.lastName,
  );
  const emailColor = getHelperColor(touchedFields.email, !!errors.email);

  const firstNameHelper =
    touchedFields.firstName && errors.firstName
      ? FIRST_NAME_ERROR
      : nameFields[0].example;

  const lastNameHelper =
    touchedFields.lastName && errors.lastName
      ? LAST_NAME_ERROR
      : nameFields[1].example;

  const emailHelper =
    touchedFields.email && errors.email ? EMAIL_ERROR : emailField.example;

  const showPasswordStrength = touchedFields.password || password.length > 0;
  const passwordStrengthIsStrong =
    password.length > 0 && passwordRuleItems.every((rule) => rule.isMet);
  const passwordStrengthLabel = passwordStrengthIsStrong ? "Strong" : "Weak";
  const passwordStrengthColor = passwordStrengthIsStrong
    ? VALID_COLOR
    : INVALID_COLOR;

  const onSubmit = (data: SignupFormValues) => {
    console.log("Signup payload", data);
  };

  return (
    <form className={classes.form} noValidate onSubmit={handleSubmit(onSubmit)}>
      <div className={classes.row}>
        <FormInput
          id={nameFields[0].id}
          label={nameFields[0].label}
          placeholder={nameFields[0].placeholder}
          type={nameFields[0].type}
          helperText={firstNameHelper}
          helperColor={firstNameColor}
          inputBorderColor={firstNameBorder}
          {...register("firstName", {
            required: true,
            maxLength: 50,
            pattern: /^[A-Za-z]+(?:[-'][A-Za-z]+)*$/,
          })}
        />{" "}
        <FormInput
          id={nameFields[1].id}
          label={nameFields[1].label}
          placeholder={nameFields[1].placeholder}
          type={nameFields[1].type}
          helperText={lastNameHelper}
          helperColor={lastNameColor}
          inputBorderColor={lastNameBorder}
          {...register("lastName", {
            required: true,
            maxLength: 50,
            pattern: /^[A-Za-z]+(?:[-'][A-Za-z]+)*$/,
          })}
        />
      </div>

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
          required: true,
          pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
        })}
      />

      <div className="flex flex-col gap-1">
        <div className="flex items-center justify-between">
          <label htmlFor="password" className={classes.label}>
            Password
          </label>
          {showPasswordStrength && (
            <div className="flex items-center gap-2">
              <span
                className="inline-block h-2 w-2 shrink-0 rounded-full"
                style={{ backgroundColor: passwordStrengthColor }}
              />
              <small className="font-light text-xs leading-4 tracking-normal">
                {passwordStrengthLabel}
              </small>
            </div>
          )}
        </div>

        <div className="relative">
          <input
            type={showPassword ? "text" : "password"}
            id="password"
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
            {...register("password", {
              required: true,
              validate: {
                lowercase: (v) => /[a-z]/.test(v),
                uppercase: (v) => /[A-Z]/.test(v),
                number: (v) => /\d/.test(v),
                special: (v) => /[^A-Za-z0-9]/.test(v),
                length: (v) => v.length >= 8 && v.length <= 16,
              },
            })}
          />
          <button
            type="button"
            onClick={() => setShowPassword((prev) => !prev)}
            aria-label={showPassword ? "Hide password" : "Show password"}
            aria-pressed={showPassword}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-[#666] hover:text-[var(--color-text-primary)] focus:outline-none cursor-pointer"
          >
            <img
              src={showPassword ? eyeClosed : eyeOpen}
              alt="Toggle password visibility"
            />
          </button>
        </div>

        <RulesList
          items={passwordRuleItems}
          hasInput={password.trim().length > 0 || !!touchedFields.password}
        />
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="confirmPassword" className={classes.label}>
          Confirm Password
        </label>
        <div className="relative">
          <input
            type={showConfirmPassword ? "text" : "password"}
            id="confirmPassword"
            placeholder="Confirm your password"
            className={classes.input + " w-full pr-12"}
            style={
              confirmBorder
                ? {
                    borderColor: confirmBorder,
                    boxShadow: "0 0 0 1px " + confirmBorder + "22",
                  }
                : undefined
            }
            {...register("confirmPassword", {
              required: true,
              validate: (value) => value === password,
            })}
          />
          <button
            type="button"
            onClick={() => setShowConfirmPassword((prev) => !prev)}
            aria-label={showConfirmPassword ? "Hide password" : "Show password"}
            aria-pressed={showConfirmPassword}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-[#666] hover:text-[var(--color-text-primary)] focus:outline-none cursor-pointer"
          >
            <img
              src={showConfirmPassword ? eyeClosed : eyeOpen}
              alt="Toggle password visibility"
            />
          </button>
        </div>
        <RulesList
          items={confirmRuleItems}
          hasInput={confirmPassword.trim().length > 0}
        />
      </div>

      <div className={classes.actionWrap}>
        <button
          type="submit"
          disabled={!isValid || isSubmitting}
          className={classes.submit}
          style={{
            backgroundColor: isValid ? VALID_COLOR : NEUTRAL_COLOR,
            cursor: isValid ? "pointer" : "not-allowed",
            opacity: isValid ? 1 : 0.85,
          }}
        >
          Create Account
        </button>

        <p className={classes.loginText}>
          Already have an account?{" "}
          <Link to="/login" className={classes.loginLink}>
            Login
          </Link>{" "}
          instead
        </p>
      </div>
    </form>
  );
};

export default SignUpForm;
