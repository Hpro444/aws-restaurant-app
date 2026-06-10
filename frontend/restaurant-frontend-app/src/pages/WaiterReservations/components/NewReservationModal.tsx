import { useEffect, useMemo, useState } from "react";
import getApiBaseUrl from "../../../config/GetApiBaseUrl";
import { useAuth } from "../../../context/AuthContext";
import { Calendar } from "primereact/calendar";
import {
  apiDateToDate,
  createWaiterReservation,
  getCustomerIdFromApiItem,
  getLocationTables,
  getValidSlotTimes,
  isCustomerApiItem,
  toApiDate,
  type CustomerOption,
  type NewReservationFormState,
  type NewReservationPayload,
} from "../waiterReservations.services";

interface NewReservationModalProps {
  onClose: () => void;
  onSubmit?: (payload: NewReservationPayload) => void;
}

export default function NewReservationModal({
  onClose,
  onSubmit,
}: NewReservationModalProps) {
  const { accessToken, user } = useAuth();
  const [tableOptions, setTableOptions] = useState<number[]>([]);
  const [tablesLoading, setTablesLoading] = useState<boolean>(false);
  const [tablesError, setTablesError] = useState<string | null>(null);
  const [validStartTimes, setValidStartTimes] = useState<string[]>([]);
  const [validEndTimes, setValidEndTimes] = useState<string[]>([]);
  const [slotTimesLoading, setSlotTimesLoading] = useState<boolean>(false);
  const [slotTimesError, setSlotTimesError] = useState<string | null>(null);

  const locationId = user?.waiterLocation?.location_id ?? "";

  const [form, setForm] = useState<NewReservationFormState>({
    customerType: "visitor",
    customerName: "",
    selectedCustomer: null,
    guests: 1,
    date: "",
    fromTime: "",
    toTime: "",
    table: "",
  });

  const [showTableDropdown, setShowTableDropdown] = useState<boolean>(false);
  const [showSuggestions, setShowSuggestions] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

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
    if (!accessToken || !locationId) return;
    let isMounted = true;

    const fetchTables = async () => {
      try {
        setTablesLoading(true);
        setTablesError(null);

        const tableNumbers = await getLocationTables(accessToken, locationId);

        if (!isMounted) return;
        setTableOptions(tableNumbers);
      } catch (err) {
        if (!isMounted) return;
        setTableOptions([]);
        setTablesError(
          err instanceof Error ? err.message : "Failed to load tables",
        );
      } finally {
        if (isMounted) {
          setTablesLoading(false);
        }
      }
    };

    void fetchTables();

    return () => {
      isMounted = false;
    };
  }, [accessToken, locationId]);

  useEffect(() => {
    if (!accessToken || !locationId) return;
    let isMounted = true;

    const fetchSlotTimes = async () => {
      try {
        setSlotTimesLoading(true);
        setSlotTimesError(null);

        const payload = await getValidSlotTimes(accessToken, locationId);

        if (!isMounted) return;

        setValidStartTimes(payload.start_times);
        setValidEndTimes(payload.end_times);
        setForm((prev) => ({
          ...prev,
          fromTime: payload.start_times.includes(prev.fromTime)
            ? prev.fromTime
            : "",
          toTime: payload.end_times.includes(prev.toTime) ? prev.toTime : "",
        }));
      } catch (err) {
        if (!isMounted) return;
        setValidStartTimes([]);
        setValidEndTimes([]);
        setSlotTimesError(
          err instanceof Error ? err.message : "Failed to load slot times",
        );
      } finally {
        if (isMounted) {
          setSlotTimesLoading(false);
        }
      }
    };

    void fetchSlotTimes();

    return () => {
      isMounted = false;
    };
  }, [accessToken, locationId]);

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

        const mapped = payload
          .filter(isCustomerApiItem)
          .map((item) => ({
            customerId: getCustomerIdFromApiItem(item),
            userName: item.user_name,
            email: item.email,
          }))
          .filter((item) => item.customerId);

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

  const toReservationIsoTime = (date: string, time: string): string => {
    if (!date || !time) return "";

    const normalizedTime = /^\d{2}:\d{2}$/.test(time)
      ? `${time}:00`
      : /^\d{2}:\d{2}:\d{2}$/.test(time)
        ? time
        : "";
    if (!normalizedTime) return "";

    return `${date}T${normalizedTime}Z`;
  };

  const filteredCustomers = useMemo(() => {
    const query = form.customerName.trim().toLowerCase();
    if (!query) return customers;
    return customers.filter(
      (customer) =>
        customer.userName.toLowerCase().includes(query) ||
        customer.email.toLowerCase().includes(query),
    );
  }, [customers, form.customerName]);

  const handleSubmit = async () => {
    if (!accessToken) {
      setSubmitError("Please log in to create reservation.");
      return;
    }
    if (!locationId) {
      setSubmitError("Waiter location is missing.");
      return;
    }

    if (!form.date) {
      setSubmitError("Date is required.");
      return;
    }

    if (!form.fromTime || !form.toTime) {
      setSubmitError("Both from and to time are required.");
      return;
    }

    if (
      !validStartTimes.includes(form.fromTime) ||
      !validEndTimes.includes(form.toTime)
    ) {
      setSubmitError("Please select valid slot times.");
      return;
    }

    const isoFrom = toReservationIsoTime(form.date, form.fromTime);
    const isoTo = toReservationIsoTime(form.date, form.toTime);

    if (!isoFrom || !isoTo) {
      setSubmitError("Invalid time format.");
      return;
    }

    if (!form.table) {
      setSubmitError("Please select a table.");
      return;
    }

    if (form.guests < 1) {
      setSubmitError("Guests number must be at least 1.");
      return;
    }

    const trimmedName = form.customerName.trim();

    if (form.customerType === "visitor" && !trimmedName) {
      setSubmitError("Client name is required for visitor reservation.");
      return;
    }

    if (
      form.customerType === "existing" &&
      !form.selectedCustomer?.customerId
    ) {
      setSubmitError("Please select an existing customer.");
      return;
    }

    try {
      setIsSubmitting(true);
      setSubmitError(null);

      const basePayload = {
        locationId,
        tableNumber: Number(form.table),
        date: form.date,
        guestsNumber: form.guests,
        timeFrom: isoFrom,
        timeTo: isoTo,
      };

      if (form.customerType === "existing") {
        console.log({
          ...basePayload,
          existingCustomer: true,
          customerId: form.selectedCustomer!.customerId,
        });
        await createWaiterReservation(accessToken, {
          ...basePayload,
          existingCustomer: true,
          customerId: form.selectedCustomer!.customerId,
        });
      } else {
        console.log({
          ...basePayload,
          existingCustomer: false,
          clientName: trimmedName,
        });
        await createWaiterReservation(accessToken, {
          ...basePayload,
          existingCustomer: false,
          clientName: trimmedName,
        });
      }

      onSubmit?.({
        customerType: form.customerType,
        customerName:
          form.customerType === "existing"
            ? form.selectedCustomer?.userName || trimmedName
            : trimmedName,
        guests: form.guests,
        date: form.date,
        fromTime: form.fromTime,
        toTime: form.toTime,
        table: form.table,
      });

      onClose();
    } catch (err) {
      setSubmitError(
        err instanceof Error ? err.message : "Failed to create reservation.",
      );
    } finally {
      setIsSubmitting(false);
    }
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
        </button>{" "}
        <h2 className="text-2xl font-semibold mb-6">New Reservation</h2>
        <div className="flex items-center gap-2 mb-6">
          <span className="pi pi-map-marker" />
          <span className="text-gray-800 font-medium">
            {user?.waiterLocation?.location_address}
          </span>
        </div>
        <div className="flex flex-col gap-3 mb-6">
          <button
            className={`flex items-center gap-2 border rounded-xl px-4 py-3 font-medium transition ${
              form.customerType === "visitor"
                ? "border-green-500 bg-green-50"
                : "border-gray-200 bg-white"
            }`}
            onClick={() => {
              updateForm("customerType", "visitor");
              updateForm("selectedCustomer", null);
            }}
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
        {form.customerType === "visitor" && (
          <div className="mb-6 border border-green-500 rounded-xl px-4 py-3">
            <label className="block font-medium text-gray-800 mb-2">
              Client Name
            </label>
            <input
              className="w-full border-none outline-none bg-transparent text-gray-800 font-medium"
              type="text"
              value={form.customerName}
              onChange={(e) => updateForm("customerName", e.target.value)}
              placeholder="Enter visitor full name"
              autoComplete="off"
            />
          </div>
        )}
        {form.customerType === "existing" && (
          <div className="mb-6 border border-green-500 rounded-xl px-4 py-3">
            <label className="block font-medium text-gray-800 mb-2">
              Customer Name
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
                        form.selectedCustomer?.customerId ===
                        customer.customerId;

                      return (
                        <button
                          key={customer.customerId}
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
        <div className="mb-3">
          <div className="text-xs text-gray-500 mb-1">Date</div>
          <div className="flex items-center gap-2 border border-gray-200 rounded-xl px-3 py-2 w-full bg-white">
            <span className="pi pi-calendar" />
            <Calendar
              onChange={(e) => {
                const value = e.value;
                if (value instanceof Date) {
                  updateForm("date", toApiDate(value));
                }
              }}
              value={apiDateToDate(form.date)}
              dateFormat="M d, yy"
              placeholder="Pick date"
              showIcon={false}
              panelClassName="bg-white"
            />
          </div>
        </div>
        <div className="mb-2">
          <div className="font-medium text-gray-800 mb-1">Time</div>
          <div className="text-gray-500 text-sm mb-3">
            Please choose your preferred time from the dropdowns below
          </div>

          <div className="flex gap-2 mb-3">
            <div className="flex-1">
              <div className="text-xs text-gray-500 mb-1">From</div>
              <div className="flex items-center gap-2 border border-gray-200 rounded-xl px-3 py-2 w-full bg-white">
                <span className="pi pi-clock" />
                <select
                  className="w-full bg-transparent outline-none text-gray-800 font-medium disabled:text-gray-400"
                  value={form.fromTime}
                  onChange={(e) => updateForm("fromTime", e.target.value)}
                  disabled={slotTimesLoading || validStartTimes.length === 0}
                >
                  <option value="">
                    {slotTimesLoading ? "Loading..." : "Select start time"}
                  </option>
                  {validStartTimes.map((time) => (
                    <option key={time} value={time}>
                      {time}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex-1">
              <div className="text-xs text-gray-500 mb-1">To</div>
              <div className="flex items-center gap-2 border border-gray-200 rounded-xl px-3 py-2 w-full bg-white">
                <span className="pi pi-clock" />
                <select
                  className="w-full bg-transparent outline-none text-gray-800 font-medium disabled:text-gray-400"
                  value={form.toTime}
                  onChange={(e) => updateForm("toTime", e.target.value)}
                  disabled={slotTimesLoading || validEndTimes.length === 0}
                >
                  <option value="">
                    {slotTimesLoading ? "Loading..." : "Select end time"}
                  </option>
                  {validEndTimes.map((time) => (
                    <option key={time} value={time}>
                      {time}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {slotTimesError ? (
            <p className="text-sm text-red-500 mb-2">{slotTimesError}</p>
          ) : null}

          <div className="relative">
            <button
              className="flex items-center gap-2 border border-gray-200 rounded-xl px-3 py-2 w-full bg-white hover:border-green-500 transition disabled:cursor-not-allowed disabled:opacity-70"
              type="button"
              onClick={() => {
                if (!tablesLoading && tableOptions.length > 0) {
                  setShowTableDropdown((prev) => !prev);
                }
              }}
              disabled={tablesLoading || tableOptions.length === 0}
            >
              <span className="text-gray-800 font-medium flex-1 text-left">
                {tablesLoading
                  ? "Loading tables..."
                  : form.table
                    ? `Table ${form.table}`
                    : "Select table"}
              </span>
              <span
                className={`pi pi-chevron-down transition-transform ${
                  showTableDropdown ? "rotate-180" : ""
                }`}
              />
            </button>

            {tablesError ? (
              <p className="text-sm text-red-500 mt-2">{tablesError}</p>
            ) : null}

            {showTableDropdown && !tablesLoading && tableOptions.length > 0 && (
              <div className="absolute top-full left-0 right-0 bg-white border border-gray-200 rounded-lg mt-1 shadow-lg max-h-48 overflow-y-auto z-10">
                {tableOptions.map((tableNumber) => (
                  <button
                    key={tableNumber}
                    className={
                      "w-full text-left px-4 py-2 " +
                      (form.table === String(tableNumber)
                        ? "bg-green-100"
                        : "hover:bg-green-50")
                    }
                    onClick={() => {
                      updateForm("table", String(tableNumber));
                      setShowTableDropdown(false);
                    }}
                    type="button"
                  >
                    {`Table ${tableNumber}`}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
        {submitError ? (
          <p className="text-sm text-red-500 mb-2">{submitError}</p>
        ) : null}
        <button
          className="w-full bg-green-600 text-white font-semibold rounded-xl py-3 mt-2 hover:bg-green-700 transition disabled:opacity-70 disabled:cursor-not-allowed"
          type="button"
          onClick={() => void handleSubmit()}
          disabled={isSubmitting}
        >
          {isSubmitting ? "Creating reservation..." : "Make a Reservation"}
        </button>
      </div>
    </div>
  );
}
