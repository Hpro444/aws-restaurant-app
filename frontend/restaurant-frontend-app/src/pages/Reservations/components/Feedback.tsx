import { useState, type FC } from "react";
import { Dialog } from "primereact/dialog";
import { Button } from "primereact/button";
import { InputTextarea } from "primereact/inputtextarea";
import { Rating } from "primereact/rating";

type FeedbackTab = "Service" | "Culinary Experience";

interface FeedbackModalProps {
  visible: boolean;
  onHide: () => void;
}

interface WaiterData {
  name: string;
  role: string;
  rating: number;
  avatar: string;
}

interface FeedbackFormState {
  selectedTab: FeedbackTab;
  rating: number;
  comments: string;
}

const FeedbackModal: FC<FeedbackModalProps> = ({ visible, onHide }) => {
  const [form, setForm] = useState<FeedbackFormState>({
    selectedTab: "Service",
    rating: 0,
    comments: "",
  });

  // TODO: Replace with fetched data for that reservation
  const waiterData: WaiterData = {
    name: "Mario Jast",
    role: "Waiter",
    rating: 4.96,
    avatar: "/api/placeholder/60/60",
  };

  const tabs: FeedbackTab[] = ["Service", "Culinary Experience"];

  const updateForm = <K extends keyof FeedbackFormState>(
    key: K,
    value: FeedbackFormState[K],
  ): void => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = (): void => {
    // TODO: Implement logic
    onHide();
  };

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
      <div className="flex flex-col gap-10">
        <p className="text-sm text-[#232323] ">
          Please rate your experience below
        </p>

        <div className="flex">
          {tabs.map((tab) => (
            <button
              key={tab}
              onClick={() => updateForm("selectedTab", tab)}
              className={`flex-1 pb-3 text-lg font-medium border-b-1 transition-colors text-left ${
                form.selectedTab === tab
                  ? "text-[var(--color-brand)] border-[#00ad0c]"
                  : "text-gray-400 border-transparent hover:text-gray-600"
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-4">
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
                {waiterData.rating}
              </span>
              <i className="pi pi-star-fill text-yellow-400 text-xs"></i>
            </div>
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between">
            <Rating
              value={form.rating}
              onChange={(e) => updateForm("rating", e.value || 0)}
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
        </div>

        <Button
          label="Submit Feedback"
          onClick={handleSubmit}
          className="w-full bg-[#898989] hover:bg-[#757575] text-white py-3 px-4 rounded-lg font-medium transition-colors"
        />
      </div>
    </Dialog>
  );
};

export default FeedbackModal;
