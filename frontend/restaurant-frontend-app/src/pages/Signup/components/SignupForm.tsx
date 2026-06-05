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
import { signupUser } from "../signup.services";
import { useNavigate } from "react-router-dom";
import { Link } from "react-router-dom";

import eyeClosed from "../../../assets/signup/Eye closed.png";
import eyeOpen from "../../../assets/signup/Eye.png";
import type { SignupPayload } from "../../../types/auth";

const VALID_COLOR = "#00AD0C";
const INVALID_COLOR = "#B70B0B";
const NEUTRAL_COLOR = "#898989";

const FIRST_NAME_ERROR =
  "First name must be up to 50 characters. Only Latin letters, hyphens, and apostrophes are allowed.";
const LAST_NAME_ERROR =
  "Last name must be up to 50 characters. Only Latin letters, hyphens, and apostrophes are allowed.";
const EMAIL_ERROR =
  "Invalid email address. Please ensure it follows the format: username@domain.com";

const EMAIL_REGEX =
  /^(?![\d])[A-Za-z][A-Za-z0-9._%+-]*@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/;
const isValidEmail = (value: string) => EMAIL_REGEX.test(value.trim());

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
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const navigate = useNavigate();

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
      lowercase: /[a-z]/.test(password || ""),
      uppercase: /[A-Z]/.test(password || ""),
      number: /\d/.test(password || ""),
      special: /[^A-Za-z0-9]/.test(password || ""),
      length: (password || "").length >= 8 && (password || "").length <= 16,
      confirm:
        (confirmPassword || "").length > 0 && confirmPassword === password,
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

  const showPasswordStrength =
    touchedFields.password || (password || "").length > 0;
  const passwordStrengthIsStrong =
    (password || "").length > 0 &&
    passwordRuleItems.every((rule) => rule.isMet);
  const passwordStrengthLabel = passwordStrengthIsStrong ? "Strong" : "Weak";
  const passwordStrengthColor = passwordStrengthIsStrong
    ? VALID_COLOR
    : INVALID_COLOR;

  const passwordValid = passwordRuleItems.every((rule) => rule.isMet);
  const confirmPasswordValid =
    (confirmPassword || "").length > 0 && confirmPassword === password;
  const firstNameValid =
    (register("firstName").name && !errors.firstName) || false;
  const lastNameValid =
    (register("lastName").name && !errors.lastName) || false;
  const emailValid = (register("email").name && !errors.email) || false;

  const canSubmit =
    isValid &&
    passwordValid &&
    confirmPasswordValid &&
    !isSubmitting &&
    firstNameValid &&
    lastNameValid &&
    emailValid;

  const onSubmit = async (data: SignupFormValues) => {
    setError(null);
    setSuccess(null);

    const payload: SignupPayload = {
      first_name: data.firstName.trim(),
      last_name: data.lastName.trim(),
      email: data.email.trim().toLowerCase(),
      password: data.password,
      confirmPassword: data.confirmPassword,
    };

    try {
      await signupUser(payload);
      setSuccess("Your account has been successfully created.");
      setTimeout(() => {
        navigate("/login");
      }, 2000);
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "An error occurred";
      setError(errorMessage);
    }
  };

  return (
    <>
      {(error || success) && (
        <div
          className={`
    fixed top-4 right-4 z-50 max-w-md w-full
    flex items-start gap-4 p-4 rounded-lg shadow-lg
    ${
      success
        ? "bg-[#eaffea] border border-[#00ad0c]"
        : "bg-[#fde8e8] border border-[#b70b0b]"
    }
  `}
        >
          <div className="flex-shrink-0">
            {success ? (
              <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-[#00ad0c]">
                <svg
                  className="w-5 h-5 text-white"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={2}
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M5 13l4 4L19 7"
                  />
                </svg>
              </span>
            ) : (
              <span
                className="inline-flex items-center justify-center w-8 h-
8 rounded-full bg-[#b70b0b]"
              >
                <svg
                  className="w-5 h-5 text-white"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={2}
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </span>
            )}
          </div>
          <div>
            <div className="font-semibold text-lg text-black">
              {success ? "Success" : "Error"}
            </div>
            <div className="text-black mt-1">{success ? success : error}</div>
          </div>
          <button
            type="button"
            onClick={() => {
              setError(null);
              setSuccess(null);
            }}
            aria-label="Close notification"
            className="ml-auto text-2xl cursor-pointer font-bold text-black hover:text-gray-700 focus:outline-none"
          >
            ×
          </button>
        </div>
      )}

      <form
        className={classes.form}
        noValidate
        onSubmit={handleSubmit(onSubmit)}
      >
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
          />
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
            required: "Email is required",
            pattern: {
              value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
              message: "Please enter a valid email address",
            },
            validate: {
              isValidEmail: (value) =>
                isValidEmail(value) ||
                "Invalid email address. Please ensure it follows the format: username@domain.com",
            },
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
            hasInput={
              (password || "").trim().length > 0 || !!touchedFields.password
            }
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
              required
              placeholder="Confirm your password"
              className={classes.input + " w-full"}
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
              aria-label={
                showConfirmPassword ? "Hide password" : "Show password"
              }
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
            hasInput={(confirmPassword || "").trim().length > 0}
          />
        </div>

        <div className={classes.actionWrap}>
          <button
            type="submit"
            disabled={!canSubmit || isSubmitting}
            className={classes.submit}
            style={{
              backgroundColor:
                canSubmit && !isSubmitting ? VALID_COLOR : NEUTRAL_COLOR,
              cursor: canSubmit && !isSubmitting ? "pointer" : "not-allowed",
              opacity: canSubmit && !isSubmitting ? 1 : 0.85,
            }}
          >
            {isSubmitting ? "Creating account..." : "Create Account"}
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
    </>
  );
};

export default SignUpForm;
