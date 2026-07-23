import { useCallback, useState } from "react";
import type { SupportApiError } from "@/features/customer-support/api";
import { asSupportApiError } from "@/features/customer-support/shared/useSupportRecords";

export function useSupportMutation({
  onChanged,
  onError,
  onSuccessMessage,
}: {
  onChanged: () => void;
  onError: (error: SupportApiError) => void;
  onSuccessMessage: (message: string) => void;
}) {
  const [saving, setSaving] = useState(false);

  const runMutation = useCallback(async <T,>(
    operation: () => Promise<T>,
    onSuccess: (result: T) => void,
    message: string,
  ) => {
    setSaving(true);
    try {
      const result = await operation();
      onSuccess(result);
      onSuccessMessage(message);
      onChanged();
      return true;
    } catch (error) {
      onError(asSupportApiError(error, "The change could not be saved."));
      return false;
    } finally {
      setSaving(false);
    }
  }, [onChanged, onError, onSuccessMessage]);

  return { saving, runMutation };
}
