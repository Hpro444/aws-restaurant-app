import { useEffect, useMemo, useState } from "react";
import getApiBaseUrl from "../../../config/GetApiBaseUrl";
import { useAuth } from "../../../context/AuthContext";
import { Calendar } from "primereact/calendar";
import type { Nullable } from "primereact/ts-helpers";

type CustomerType = "visitor" | "existing";

interface CustomerApiItem {
  user_name: string;
  email: string;
}

interface CustomerOption {
  userName: string;
  email: string;
}

interface NewReservationPayload {
  customerType: CustomerType;
  customerName: string;
  guests: number;
  fromTime: string;
  toTime: string;
  table: string;
}

interface NewReservationFormState {
  customerType: CustomerType;
  customerName: string;
  selectedCustomer: CustomerOption | null;
  guests: number;
  fromTime: string;
  toTime: string;
  table: string;
}

interface NewReservationModalProps {
  onClose: () => void;
  onSubmit?: (payload: NewReservationPayload) => void;
}

// TODO: Replace with real API data
const availableTables = [
  "Table 1",
  "Table 2",
  "Table 3",
  "Table 4",
  "Table 5",
  "Table 6",
  "Table 7",
  "Table 8",
  "Table 9",
  "Table 10",
];

const isCustomerApiItem = (value: unknown): value is CustomerApiItem => {
  if (typeof value !== "object" || value === null) return false;
  const maybe = value as Record<string, unknown>;
  return typeof maybe.user_name === "string" && typeof maybe.email === "string";
};

const dateToIsoString = (date: Nullable<Date>): string => {
  if (!date) return "";
  return date.toISOString();
};

const isoStringToDate = (iso: string): Nullable<Date> => {
  if (!iso) return null;
  return new Date(iso);
};

export default function NewReservationModal({
  onClose,
  onSubmit,
}: NewReservationModalProps) {
  const { accessToken } = useAuth();

  const [form, setForm] = useState<NewReservationFormState>({
    customerType: "visitor",
    customerName: "",
    selectedCustomer: null,
    guests: 1,
    fromTime: "",
    toTime: "",
    table: "",
  });

  const [showTableDropdown, setShowTableDropdown] = useState<boolean>(false);
  const [showSuggestions, setShowSuggestions] = useState<boolean>(false);

  const [customers, setCustomers] = useState<CustomerOption[]>([]);
  const [customersLoading, setCustomersLoading] = useState<boolean>(false);
  const [customersError, setCustomersError] = useState<string | null>(null);
  const [hasFetchedCustomers, setHasFetchedCustomers] =
    useState<boolean>(false);

  const updateForm = <K extends keyof NewReservationFormState>(
    key: K,
    value: NewReservationFormState[K],
  ) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  useEffect(() => {
    if (form.customerType !== "existing" || hasFetchedCustomers) return;

    const controller = new AbortController();

    const fetchCustomers = async () => {
      try {
        setCustomersLoading(true);
        setCustomersError(null);

        const response = await fetch(`${getApiBaseUrl()}/customers`, {
          method: "GET",
          headers: {
            ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
          },
          signal: controller.signal,
        });

        const payload: unknown = await response.json().catch(() => null);

        if (!response.ok) {
          const maybe = payload as Record<string, unknown> | null;
          const message =
            (typeof maybe?.message === "string" && maybe.message) ||
            (typeof maybe?.error === "string" && maybe.error) ||
            `Failed to fetch customers (${response.status})`;
          throw new Error(message);
        }

        if (!Array.isArray(payload)) {
          throw new Error("Invalid customers response format");
        }

        const mapped = payload.filter(isCustomerApiItem).map((item) => ({
          userName: item.user_name,
          email: item.email,
        }));

        setCustomers(mapped);
        setHasFetchedCustomers(true);
      } catch (err) {
        if (err instanceof Error && err.name !== "AbortError") {
          setCustomersError(err.message);
        } else if (!(err instanceof Error)) {
          setCustomersError("Failed to load customers");
        }
      } finally {
        setCustomersLoading(false);
      }
    };

    void fetchCustomers();

    return () => {
      controller.abort();
    };
  }, [form.customerType, hasFetchedCustomers, accessToken]);

  const filteredCustomers = useMemo(() => {
    const query = form.customerName.trim().toLowerCase();
    if (!query) return customers;

    return customers.filter(
      (customer) =>
        customer.userName.toLowerCase().includes(query) ||
        customer.email.toLowerCase().includes(query),
    );
  }, [customers, form.customerName]);

  const handleSubmit = () => {
    const finalCustomerName =
      form.customerType === "existing"
        ? form.selectedCustomer?.userName || form.customerName.trim()
        : "";

    onSubmit?.({
      customerType: form.customerType,
      customerName: finalCustomerName,
      guests: form.guests,
      fromTime: form.fromTime,
      toTime: form.toTime,
      table: form.table,
    });
  };

  return (
    <div className="fixed inset-0 flex items-center justify-center z-50 bg-black/40">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6 relative">
        <button
          className="absolute top-4 right-4 p-1 rounded-full hover:bg-gray-100 cursor-pointer transition"
          onClick={onClose}
          type="button"
          aria-label="Close modal"
        >
          <span className="pi pi-times" />
        </button>

        <h2 className="text-2xl font-semibold mb-6">New Reservation</h2>

        <div className="flex items-center gap-2 mb-6">
          <span className="pi pi-map-marker" />
          <span className="text-gray-800 font-medium">48 Rustaveli Avenue</span>
        </div>

        <div className="flex flex-col gap-3 mb-6">
          <button
            className={`flex items-center gap-2 border rounded-xl px-4 py-3 font-medium transition ${
              form.customerType === "visitor"
                ? "border-green-500 bg-green-50"
                : "border-gray-200 bg-white"
            }`}
            onClick={() => updateForm("customerType", "visitor")}
            type="button"
          >
            <span
              className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                form.customerType === "visitor"
                  ? "border-green-500"
                  : "border-gray-300"
              }`}
            >
              {form.customerType === "visitor" && (
                <span className="w-3 h-3 bg-green-500 rounded-full block" />
              )}
            </span>
            Visitor
          </button>

          <button
            className={`flex items-center gap-2 border rounded-xl px-4 py-3 font-medium transition ${
              form.customerType === "existing"
                ? "border-green-500 bg-green-50"
                : "border-gray-200 bg-white"
            }`}
            onClick={() => updateForm("customerType", "existing")}
            type="button"
          >
            <span
              className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                form.customerType === "existing"
                  ? "border-green-500"
                  : "border-gray-300"
              }`}
            >
              {form.customerType === "existing" && (
                <span className="w-3 h-3 bg-green-500 rounded-full block" />
              )}
            </span>
            Existing Customer
          </button>
        </div>

        {form.customerType === "existing" && (
          <div className="mb-6 border border-green-500 rounded-xl px-4 py-3">
            <label className="block font-medium text-gray-800 mb-2">
              Customer's Name
            </label>

            <input
              className="w-full border-none outline-none bg-transparent text-gray-800 font-medium mb-1"
              type="text"
              value={form.customerName}
              onChange={(e) => {
                setForm((prev) => ({
                  ...prev,
                  customerName: e.target.value,
                  selectedCustomer: null,
                }));
                setShowSuggestions(true);
              }}
              onFocus={() => setShowSuggestions(true)}
              onBlur={() => {
                window.setTimeout(() => setShowSuggestions(false), 120);
              }}
              placeholder="Search by username or email"
              autoComplete="off"
            />

            {customersLoading && (
              <p className="text-sm text-gray-500 mt-1">Loading customers...</p>
            )}

            {customersError && (
              <p className="text-sm text-red-500 mt-1">{customersError}</p>
            )}

            {showSuggestions &&
              form.customerName &&
              !customersLoading &&
              !customersError && (
                <div className="bg-white border border-gray-200 rounded-lg mt-1 shadow-lg max-h-32 overflow-y-auto">
                  {filteredCustomers.length > 0 ? (
                    filteredCustomers.map((customer) => {
                      const isSelected =
                        form.selectedCustomer?.email === customer.email;

                      return (
                        <button
                          key={customer.email}
                          className={
                            "w-full text-left px-4 py-2 " +
                            (isSelected ? "bg-green-100" : "hover:bg-green-50")
                          }
                          onClick={() => {
                            setForm((prev) => ({
                              ...prev,
                              selectedCustomer: customer,
                              customerName: customer.userName,
                            }));
                            setShowSuggestions(false);
                          }}
                          type="button"
                        >
                          <div className="font-medium text-gray-800">
                            {customer.userName}
                          </div>
                          <div className="text-xs text-gray-500">
                            {customer.email}
                          </div>
                        </button>
                      );
                    })
                  ) : (
                    <div className="px-4 py-2 text-gray-500">
                      No matches found
                    </div>
                  )}
                </div>
              )}
          </div>
        )}

        <div className="flex items-center gap-3 border border-gray-200 rounded-xl px-4 py-3 mb-6">
          <span className="pi pi-users" />
          <span className="font-medium text-gray-800 flex-1">Guests</span>
          <button
            className="w-8 h-8 flex items-center justify-center border border-green-500 rounded-lg text-green-500 text-xl"
            onClick={() =>
              setForm((prev) => ({
                ...prev,
                guests: Math.max(1, prev.guests - 1),
              }))
            }
            type="button"
          >
            -
          </button>
          <span className="w-8 text-center font-semibold text-gray-800">
            {form.guests}
          </span>
          <button
            className="w-8 h-8 flex items-center justify-center border border-green-500 rounded-lg text-green-500 text-xl"
            onClick={() =>
              setForm((prev) => ({
                ...prev,
                guests: prev.guests + 1,
              }))
            }
            type="button"
          >
            +
          </button>
        </div>

        <div className="mb-2">
          <div className="font-medium text-gray-800 mb-1">Time</div>
          <div className="text-gray-500 text-sm mb-3">
            Please choose your preferred time from the dropdowns below
          </div>
          <div className="flex gap-2 mb-3">
            <div className="flex-1">
              <div className="text-xs text-gray-500 mb-1">From</div>
              <button
                className="flex items-center gap-2 border border-gray-200 rounded-xl px-3 py-2 w-full bg-white"
                type="button"
              >
                <span className="pi pi-clock" />
                <Calendar
                  onChange={(e) =>
                    updateForm("fromTime", dateToIsoString(e.value))
                  }
                  value={isoStringToDate(form.fromTime)}
                  timeOnly
                  panelClassName="bg-white p-4 text-[20px]"
                  hourFormat="24"
                  placeholder="Pick time"
                />
              </button>
            </div>
            <div className="flex-1">
              <div className="text-xs text-gray-500 mb-1">To</div>
              <button
                className="flex items-center gap-2 border border-gray-200 rounded-xl px-3 py-2 w-full bg-white"
                type="button"
              >
                <span className="pi pi-clock" />
                <Calendar
                  onChange={(e) =>
                    updateForm("toTime", dateToIsoString(e.value))
                  }
                  value={isoStringToDate(form.toTime)}
                  timeOnly
                  panelClassName="bg-white p-4 text-[20px]"
                  hourFormat="24"
                  placeholder="Pick time"
                />
              </button>
            </div>
          </div>

          <div className="relative">
            <button
              className="flex items-center gap-2 border border-gray-200 rounded-xl px-3 py-2 w-full bg-white hover:border-green-500 transition"
              type="button"
              onClick={() => setShowTableDropdown(!showTableDropdown)}
            >
              <span className="text-gray-800 font-medium flex-1 text-left">
                {form.table || "Select table"}
              </span>
              <span
                className={`pi pi-chevron-down transition-transform ${
                  showTableDropdown ? "rotate-180" : ""
                }`}
              />
            </button>

            {showTableDropdown && (
              <div className="absolute top-full left-0 right-0 bg-white border border-gray-200 rounded-lg mt-1 shadow-lg max-h-48 overflow-y-auto z-10">
                {availableTables.map((tableOption) => (
                  <button
                    key={tableOption}
                    className={
                      "w-full text-left px-4 py-2 " +
                      (form.table === tableOption
                        ? "bg-green-100"
                        : "hover:bg-green-50")
                    }
                    onClick={() => {
                      updateForm("table", tableOption);
                      setShowTableDropdown(false);
                    }}
                    type="button"
                  >
                    {tableOption}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        <button
          className="w-full bg-green-600 text-white font-semibold rounded-xl py-3 mt-2 hover:bg-green-700 transition"
          type="button"
          onClick={handleSubmit}
        >
          Make a Reservation
        </button>
      </div>
    </div>
  );
}
