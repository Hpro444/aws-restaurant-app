import type { InputHTMLAttributes } from "react";

export type InputType = "text" | "email" | "password";

export type FieldConfig = {
  id: string;
  name: string;
  label: string;
  type: InputType;
  placeholder: string;
  example?: string;
};

export type FormInputProps = InputHTMLAttributes<HTMLInputElement> & {
  id: string;
  label: string;
  example?: string;
};
