// utils/reservationHelpers.ts
export const getStatusColor = (status: string): string => {
  switch (status.toLowerCase()) {
    case "reserved":
      return "text-blue-600 bg-blue-50 border-blue-200";
    case "in progress":
      return "text-orange-600 bg-orange-50 border-orange-200";
    case "finished":
      return "text-green-600 bg-green-50 border-green-200";
    case "canceled":
    case "cancelled":
      return "text-red-600 bg-red-50 border-red-200";
    default:
      return "text-gray-600 bg-gray-50 border-gray-200";
  }
};

export const formatDate = (dateString: string): string => {
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return dateString;
  }
};

export const formatTimeSlot = (timeSlot: string): string => {
  // Handle different time formats
  if (timeSlot.includes(" - ")) {
    return timeSlot;
  }
  // Add formatting logic based on your backend format
  return timeSlot;
};

export const canEditReservation = (status: string): boolean => {
  return status.toLowerCase() === "reserved";
};

export const canCancelReservation = (status: string): boolean => {
  return ["reserved", "in progress"].includes(status.toLowerCase());
};

export const canLeaveFeedback = (
  status: string,
  feedbackId: string,
): boolean => {
  return status.toLowerCase() === "finished" && !feedbackId;
};
