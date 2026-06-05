export type Location = {
  id: string;
  address: string;
  image_url?: string;
  total_capacity?: number;
  average_occupancy?: number;
  rating?: number;
  description?: string;
};

export type Feedback = {
  id: string;
  customer_id?: string;
  feedback: string;
  rate: number;
  date: string;
  user_name: string;
  user_image_url: string;
};

export type Filters = {
  locationId: string;
  date: string;
  fromTime: string;
  guests: number;
};

export type FeedbackResponse = {
  totalPages: number;
  totalElements: number;
  size: number;
  content: Feedback[];
  number: number;
  sort: string[];
  first: boolean;
  last: boolean;
  numberOfElements: number;
  pageable: {
    offset: number;
    sort: string[];
    paged: boolean;
    pageSize: number;
    pageNumber: number;
    unpaged: boolean;
  };
  empty: boolean;
};

export interface AllowedActions {
  can_edit: boolean;
  can_cancel: boolean;
}

export interface ReservationResponse {
  reservation_id: string;
  status: string;
  customer_id?: string;
  waiter_id?: string;
  location_id?: string;
  location_address?: string;
  table_number?: number;
  date: string;
  time_from: string;
  time_to: string;
  guests_number: number;
  allowed_actions: AllowedActions;
  cutoff_reason?: string;
}

export interface AvailableSlot {
  slot_id: string;
  start_time: string;
  end_time: string;
}

export interface TableResult {
  table_id: string;
  table_number: number;
  capacity: number;
  available_slots: AvailableSlot[];
}

export interface GetTablesParams {
  location_id: string;
  date: string;
  guests_number: number;
  from_time?: string;
  to_time?: string;
}

export interface GetTablesResponse {
  tables: TableResult[];
}

export interface LocationSelectOption {
  location_id: string;
  location_address: string;
}
