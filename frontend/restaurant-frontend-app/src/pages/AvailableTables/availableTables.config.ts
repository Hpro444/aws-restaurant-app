export type Location = {
  id: string;
  name: string;
  address: string;
};

// TODO: Replace these IDs with actual location UUIDs from your backend
export const LOCATIONS: Location[] = [
  {
    id: "00000000-0000-0000-0000-000000000001",
    name: "Downtown",
    address: "123 Main Street",
  },
  {
    id: "00000000-0000-0000-0000-000000000002",
    name: "Airport Terminal",
    address: "456 Terminal Boulevard",
  },
];
