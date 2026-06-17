export const getStatusColor = (status: string): string => {
  switch (status.toLowerCase()) {
    case "reserved":
      return "text-blue-600 bg-blue-50 border-blue-200";
    case "in_progress":
      return "text-orange-600 bg-orange-50 border-orange-200";
    case "finished":
      return "text-green-600 bg-green-50 border-green-200";
    case "cancelled":
      return "text-red-600 bg-red-50 border-red-200";
    default:
      return "text-gray-600 bg-gray-50 border-gray-200";
  }
};

export const formatSlotTime = (value: string): string => {
  const trimmed = value.trim();
  if (!trimmed) return value;

  const hasZone = /(?:Z|[+-]\d{2}:\d{2})$/i.test(trimmed);
  const dateTimeNoZone = /^\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}(?::\d{2})?$/i.test(
    trimmed,
  );
  const timeOnly = /^(\d{2}):(\d{2})(?::\d{2})?$/i.exec(trimmed);

  let date: Date | null = null;

  if (dateTimeNoZone && !hasZone) {
    date = new Date(`${trimmed.replace(" ", "T")}Z`);
  } else if (hasZone || trimmed.includes("T") || trimmed.includes(" ")) {
    date = new Date(trimmed);
  } else if (timeOnly) {
    const hour = Number(timeOnly[1]);
    const minute = Number(timeOnly[2]);
    date = new Date(Date.UTC(1970, 0, 1, hour, minute, 0));
  }

  if (!date || Number.isNaN(date.getTime())) return value;

  const formatted = new Intl.DateTimeFormat("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  }).format(date);

  return formatted.replace(" AM", " a.m").replace(" PM", " p.m");
};

export const formatDate = (dateString: string): string => {
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return dateString;
  }
};

export const formatTime = (value: string): string => {
  const trimmed = value?.trim();
  if (!trimmed) return value;

  const timeOnly = /^([01]\d|2[0-3]):([0-5]\d)(?::([0-5]\d))?$/.exec(trimmed);
  if (timeOnly) {
    return `${timeOnly[1]}:${timeOnly[2]}`;
  }

  const normalized = trimmed.includes("T")
    ? trimmed
    : trimmed.replace(" ", "T");

  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "UTC",
  }).format(date);
};
