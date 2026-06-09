import getApiBaseUrl from "../../config/GetApiBaseUrl";
import type { Dish } from "../../types/dish";

export type DishType = "APPETIZER" | "DESSERT" | "MAIN_COURSE" | "DRINK";
export type DishSort =
  | "popularity,asc"
  | "popularity,desc"
  | "price,asc"
  | "price,desc";

type BackendValidationError = {
  field?: string;
  message?: string;
};

type BackendErrorPayload = {
  message?: string;
  error?: string;
  errors?: BackendValidationError[];
};

type GetDishesParams = {
  dishType: DishType;
  sort: DishSort;
};

const getDishesErrorMessage = (status: number, payload: unknown): string => {
  const maybe = payload as BackendErrorPayload | null;

  if (Array.isArray(maybe?.errors) && maybe.errors.length > 0) {
    return maybe.errors
      .map((e) => {
        if (e.field && e.message) return `${e.field}: ${e.message}`;
        return e.message || "Validation error";
      })
      .join(", ");
  }

  if (typeof maybe?.message === "string" && maybe.message) return maybe.message;
  if (typeof maybe?.error === "string" && maybe.error) return maybe.error;

  return `Failed to fetch dishes (${status})`;
};

export const getDishes = async ({
  dishType,
  sort,
}: GetDishesParams): Promise<Dish[]> => {
  const query = new URLSearchParams({
    dishType,
    sort,
  });

  const response = await fetch(
    `${getApiBaseUrl()}/dishes?${query.toString()}`,
    {
      method: "GET",
    },
  );

  const payload: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(getDishesErrorMessage(response.status, payload));
  }

  if (!Array.isArray(payload)) {
    return [];
  }

  return payload as Dish[];
};
