import { useEffect, useState, type FC } from "react";
import { Dialog } from "primereact/dialog";
import { Button } from "primereact/button";
import { InputTextarea } from "primereact/inputtextarea";
import { Rating } from "primereact/rating";
import { Skeleton } from "primereact/skeleton";
import {
  fetchFeedbackByType,
  fetchWaiterContext,
  submitFeedback,
  updateFeedback,
  type FeedbackDetailsResponse,
  type FeedbackFormState,
  type FeedbackTab,
  type WaiterData,
} from "../reservations.services";

interface FeedbackModalProps {
  visible: boolean;
  onHide: () => void;
  reservationId: string | null;
  accessToken: string | null;
  mode: "create" | "update";
  onSubmitted?: () => void;
}

const FeedbackModal: FC<FeedbackModalProps> = ({
  visible,
  onHide,
  reservationId,
  accessToken,
  mode,
  onSubmitted,
}) => {
  const [form, setForm] = useState<FeedbackFormState>({
    selectedTab: "Service",
    rating: 0,
    comments: "",
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const [waiterData, setWaiterData] = useState<WaiterData | null>(null);
  const [isWaiterLoading, setIsWaiterLoading] = useState(false);
  const [waiterError, setWaiterError] = useState<string | null>(null);

  const [cachedFeedback, setCachedFeedback] = useState<{
    service: FeedbackDetailsResponse | null;
    cuisine: FeedbackDetailsResponse | null;
  }>({ service: null, cuisine: null });
  const [isFeedbackLoading, setIsFeedbackLoading] = useState(false);

  const tabs: FeedbackTab[] = ["Service", "Culinary Experience"];

  const updateForm = <K extends keyof FeedbackFormState>(
    key: K,
    value: FeedbackFormState[K],
  ): void => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  // Load both feedback types once when modal opens
  useEffect(() => {
    if (!visible || !reservationId || !accessToken) {
      return;
    }

    const controller = new AbortController();

    const loadAllFeedback = async () => {
      try {
        setIsFeedbackLoading(true);
        setSubmitError(null);

        const [serviceFb, cuisineFb] = await Promise.all([
          fetchFeedbackByType(
            reservationId,
            "service",
            accessToken,
            controller.signal,
          ),
          fetchFeedbackByType(
            reservationId,
            "cuisine",
            accessToken,
            controller.signal,
          ),
        ]);

        setCachedFeedback({ service: serviceFb, cuisine: cuisineFb });

        // Pre-populate form with Service feedback (default tab), or Cuisine if Service not available
        const initialFeedback = serviceFb || cuisineFb;
        if (initialFeedback) {
          setForm((prev) => ({
            ...prev,
            selectedTab: "Service",
            rating: Number(initialFeedback.rate) || 0,
            comments: initialFeedback.feedback || "",
          }));
        } else {
          setForm((prev) => ({
            ...prev,
            selectedTab: "Service",
            rating: 0,
            comments: "",
          }));
        }
      } catch (err) {
        if ((err as Error).name === "AbortError") return;
        setSubmitError(
          err instanceof Error ? err.message : "Failed to load feedback.",
        );
      } finally {
        setIsFeedbackLoading(false);
      }
    };

    void loadAllFeedback();

    return () => controller.abort();
  }, [visible, reservationId, accessToken]);

  useEffect(() => {
    if (!visible || !reservationId || !accessToken) {
      return;
    }

    const controller = new AbortController();

    void fetchWaiterContext(
      setIsWaiterLoading,
      setWaiterError,
      setWaiterData,
      reservationId,
      accessToken,
      controller,
    );

    return () => controller.abort();
  }, [visible, reservationId, accessToken]);

  const headerContent = (
    <div className="flex items-center justify-between w-full">
      <h2 className="text-[24px] font-semibold text-gray-800 m-0">
        Give Feedback
      </h2>
      <Button
        icon="pi pi-times"
        className="cursor-pointer p-button-text p-button-plain hover:text-gray-700"
        onClick={onHide}
      />
    </div>
  );

  const isServiceTab = form.selectedTab === "Service";
  const waiterRatingDisplay = waiterData
    ? (Math.ceil(waiterData.rating * 100) / 100).toFixed(2)
    : "0.00";

  const shouldShowWaiterSection =
    isServiceTab &&
    (isWaiterLoading || Boolean(waiterError) || Boolean(waiterData));

  return (
    <Dialog
      visible={visible}
      onHide={onHide}
      header={headerContent}
      className="w-full max-w-[496px] bg-[#f7f7f7] rounded-[24px] shadow-[0px_0px_10px_4px_#DADADAB2] p-6"
      draggable={false}
      resizable={false}
      modal
      closable={false}
      maskStyle={{ backgroundColor: "#00000073" }}
    >
      <div
        className={
          shouldShowWaiterSection
            ? "flex flex-col gap-10"
            : "flex flex-col gap-6"
        }
      >
        <p className="text-sm text-[#232323] ">
          Please rate your experience below
        </p>

        <div className="flex">
          {tabs.map((tab) => (
            <button
              key={tab}
              onClick={() => {
                const tabType = tab === "Service" ? "service" : "cuisine";
                const feedback = cachedFeedback[tabType];
                console.log(tabType, feedback);

                setForm((prev) => ({
                  ...prev,
                  selectedTab: tab,
                  rating: feedback ? Number(feedback.rate) || 0 : 0,
                  comments: feedback ? feedback.feedback || "" : "",
                }));
              }}
              className={`flex-1 pb-3 text-lg font-medium border-b-1 transition-colors text-left ${form.selectedTab === tab ? "text-[var(--color-brand)] border-[#00ad0c]" : "text-gray-400 border-transparent hover:text-gray-600"}`}
            >
              {tab}
            </button>
          ))}
        </div>

        {shouldShowWaiterSection ? (
          <div className="min-h-[88px]">
            {isWaiterLoading ? (
              <div className="flex items-center gap-4">
                <Skeleton
                  shape="circle"
                  size="88px"
                  className="feedback-skeleton"
                />
                <Skeleton
                  width="10rem"
                  height="0.9rem"
                  className="feedback-skeleton"
                />
                <Skeleton
                  width="5rem"
                  height="0.75rem"
                  className="feedback-skeleton"
                />
                <Skeleton
                  width="2.2rem"
                  height="0.9rem"
                  className="feedback-skeleton"
                />
                <Skeleton
                  width="1rem"
                  height="1rem"
                  shape="circle"
                  className="feedback-skeleton"
                />
              </div>
            ) : waiterError ? (
              <div className="min-h-[88px] flex items-center text-sm text-red-500">
                {waiterError}
              </div>
            ) : waiterData ? (
              <div className="flex items-center gap-4 min-h-[88px]">
                <img
                  src={waiterData.avatar}
                  alt={waiterData.name}
                  className="w-[88px] h-[88px] rounded-full object-cover outline"
                />
                <div className="flex-1 flex flex-col gap-1">
                  <h3 className="font-medium text-[#232323] text-sm">
                    {waiterData.name}
                  </h3>
                  <p className="text-xs text-gray-500">{waiterData.role}</p>
                  <div className="flex items-center gap-1">
                    <span className="text-[14px] text-[#232323]">
                      {waiterRatingDisplay}
                    </span>
                    <i className="pi pi-star-fill text-yellow-400 text-lg"></i>
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        ) : null}

        <div>
          <div className="flex items-center justify-between">
            <Rating
              value={form.rating}
              onChange={(e) => updateForm("rating", Number(e.value) || 0)}
              stars={5}
              cancel={false}
              className="gap-4"
              pt={{
                item: {
                  className:
                    "w-[30px] h-[30px] flex items-center justify-center",
                },
                onIcon: {
                  style: {
                    fontSize: "30px",
                    width: "30px",
                    height: "30px",
                    lineHeight: "30px",
                  },
                  className: "text-yellow-400",
                },
                offIcon: {
                  style: {
                    fontSize: "30px",
                    width: "30px",
                    height: "30px",
                    lineHeight: "30px",
                  },
                  className: "text-gray-300",
                },
              }}
            />
            <span className="text-sm text-gray-500">{form.rating}/5 stars</span>
          </div>
        </div>

        <div>
          <InputTextarea
            value={form.comments}
            onChange={(e) => updateForm("comments", e.target.value)}
            placeholder="Add your comments"
            rows={4}
            className="w-full p-4 border border-[#dadada] rounded-lg resize-none text-sm placeholder-gray-400 focus:border-green-500 focus:ring-1 focus:ring-green-500"
          />
          {submitError ? (
            <p className="mt-2 text-sm text-red-500">{submitError}</p>
          ) : null}
        </div>

        <Button
          label={
            isSubmitting
              ? "Submitting..."
              : mode === "update"
                ? "Update Feedback"
                : "Submit Feedback"
          }
          onClick={() => {
            if (isSubmitting) return;

            const action = mode === "update" ? updateFeedback : submitFeedback;

            void action(
              setSubmitError,
              reservationId,
              accessToken,
              form,
              setIsSubmitting,
              () => {
                onHide();
                onSubmitted?.();
              },
            );
          }}
          disabled={isSubmitting || isFeedbackLoading || form.rating < 1}
          className={
            "w-full text-white py-3 px-4 rounded-lg font-medium transition-colors " +
            (form.comments.trim()
              ? "bg-[var(--color-brand)] hover:bg-[#009a0b]"
              : "bg-[#898989] hover:bg-[#757575]") +
            (isSubmitting || isFeedbackLoading || form.rating < 1
              ? " opacity-60 cursor-not-allowed"
              : " cursor-pointer")
          }
        />
      </div>
    </Dialog>
  );
};

export default FeedbackModal;
