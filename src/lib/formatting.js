export function formatDateTime(isoString) {
  try {
    const date = new Date(isoString);
    return new Intl.DateTimeFormat("en-US", {
      month: "long",
      day: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(date);
  } catch {
    return isoString;
  }
}

export function truncate(text, max = 32) {
  if (!text) {
    return "N/A";
  }
  const value = String(text);
  return value.length > max ? `${value.slice(0, max)}...` : value;
}
