export type Dish = {
  id?: string;
  name: string;
  description?: string;
  price: number;
  image_url?: string;
  weight_gram?: string | number;
  state?: "Available" | "Unavailable" | string;
};
