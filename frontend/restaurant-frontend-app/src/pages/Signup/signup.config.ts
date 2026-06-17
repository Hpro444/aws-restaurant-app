import type { FieldConfig } from "../../types/auth";

export const nameFields: FieldConfig[] = [
  {
    id: "firstName",
    label: "First Name",
    name: "First Name",
    type: "text",
    placeholder: "Enter your first name",
    example: "e.g Jonson",
  },
  {
    id: "lastName",
    label: "Last Name",
    name: "Last Name",
    type: "text",
    placeholder: "Enter your last name",
    example: "e.g Doe",
  },
];

export const emailField = {
  id: "email",
  label: "Email",
  type: "email",
  name: "email",
  placeholder: "Enter your email",
  example: "e.g username@domain.com",
};

export const passwordRules = [
  "At least one uppercase letter required",
  "At least one lowercase letter required",
  "At least one number required",
  "At least one special character required",
  "Password must be 8-16 characters long",
];

export const confirmRules = ["Confirm password must match new password"];
